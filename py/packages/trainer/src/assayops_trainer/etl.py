"""The trajectory->SFT ETL -- rejection sampling on the account-B graded reward.

``build_sft_dataset`` turns leg-3's graded ``EvalLog``s into a rejection-sampled SFT set: an example
enters ONLY when the deploy-verifier ``Score`` is CORRECT (reward 1 = the account-B ``verify()``
grade -- §8 reward-boundary; NEVER the env ``step()``). Pre-T0 there is no ledger, so the graded
reward is read from the log's scorer key (the pre-T0 stand-in for the ``trajectory_id`` ⨝ KMS-signed
WORM join #78 adds later) -- but a CORRECT is not merely trusted by key: the metadata must show
a settled, reproduced grade (``verdict == "reproducible"``) of THAT sample's task, and only a
``status == "success"`` log is admitted, so a foreign / partial log fails closed rather than
minting ungrounded positives. Everything else is excluded and COUNTED (never silently dropped):
INCORRECT (reward 0), quarantined (the unscored NaN sentinel -- an unsettled grade, not a negative),
and incomplete rollouts (an infra error or a hit limit). A held-out task id in the training logs
FAILS CLOSED **on any appearance** -- regardless of grade -- because a held-out task in a training
log is a corpus-split bug (contamination -- eval-rigor/I11). Duplicate rollouts are dropped, and
output is deterministically sorted so the same logs yield the same manifest.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from inspect_ai.log import EvalLog, EvalSample, read_eval_log_async
from inspect_ai.scorer import CORRECT, INCORRECT, Score

from assayops_trainer.messages import sample_to_openai_messages, sample_tools
from assayops_trainer.records import Provenance, SFTExample

# The log key leg-3's @scorer registers its Score under. MUST equal
# assayops_evals.scorer.DEPLOY_VERIFIER_SCORER_NAME -- kept as a literal (not an import) so the
# trainer's runtime dep graph stays free of the verifier stack; the contract is locked by
# test_etl.test_default_scorer_name_matches_the_evals_log_key_contract.
DEFAULT_SCORER_NAME = "deploy_verifier_scorer"

_SFT_JSONL_NAME = "sft.jsonl"
_MANIFEST_NAME = "manifest.json"

# Baked into the manifest so a pre-T0 directional SFT set can't be mistaken for the E13 proof corpus
# (mirrors leg-3's report framing; eval-rigor / R1).
_R1_FRAMING = (
    "PRE-T0 DIRECTIONAL SFT SET -- rejection-sampled from LocalStack-graded rollouts, NOT the E13 "
    "proof corpus. A model trained on this is a directional signal only; never publish or pitch it "
    "(R1; docs/priorities.md P1)."
)


@dataclass(frozen=True)
class SftDataset:
    """A built SFT set + the accounting that makes its curation auditable."""

    examples: tuple[SFTExample, ...]
    excluded_incorrect: int
    excluded_quarantined: int
    # Incomplete rollouts: an infra error OR a hit limit -- not a settled grade.
    excluded_errored: int
    dropped_duplicates: int
    source_run_ids: tuple[str, ...]


async def build_sft_dataset(
    logs: Iterable[EvalLog],
    *,
    held_out_ids: frozenset[str] = frozenset(),
    harness_git_sha: str | None = None,
    scorer_name: str = DEFAULT_SCORER_NAME,
) -> SftDataset:
    """Build the rejection-sampled SFT set from graded eval logs (see the module docstring)."""
    examples: list[SFTExample] = []
    seen: set[tuple[str, str, str, int, str]] = set()
    incorrect = quarantined = errored = duplicates = 0
    run_ids: list[str] = []
    seen_run_ids: set[str] = set()
    for log in logs:
        if log.status != "success":
            raise ValueError(
                f"eval log for {log.eval.model!r} has status {log.status!r}, not 'success' -- "
                "refusing to build training data from an incomplete/failed run (fail closed)"
            )
        run_id = log.eval.run_id
        if run_id not in seen_run_ids:
            seen_run_ids.add(run_id)
            run_ids.append(run_id)
        for sample in log.samples or []:
            task_id = str(sample.id)
            # Contamination tripwire FIRST: a held-out task id in a training-rollout log is a
            # corpus-split bug -- fail closed on ANY appearance, before grade/error triage, never
            # only when it happened to pass (eval-rigor / DECISIONS.md I11).
            if task_id in held_out_ids:
                raise ValueError(
                    f"held-out task {task_id!r} appears in a training-rollout log -- refusing to "
                    "train on / silently accept eval data (contamination; eval-rigor / I11)"
                )
            if sample.error is not None or sample.limit is not None:
                # An infra error or a hit limit -> an incomplete rollout, not a settled grade.
                errored += 1
                continue
            score = _verifier_score(sample, scorer_name)
            value = score.value
            if isinstance(value, float) and math.isnan(value):
                quarantined += 1
                continue
            if value == INCORRECT:
                incorrect += 1
                continue
            if value != CORRECT:
                raise ValueError(
                    f"unexpected score value {value!r} for sample {sample.id!r} -- the "
                    "deploy-verifier scorer emits only CORRECT / INCORRECT / the unscored NaN"
                )
            _require_reproduced_grade(score, task_id)
            key = (log.eval.model, log.eval.task_id, task_id, sample.epoch, run_id)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            examples.append(
                SFTExample(
                    messages=await sample_to_openai_messages(sample),
                    tools=sample_tools(sample),
                    provenance=Provenance(
                        task_id=task_id,
                        eval_task_id=log.eval.task_id,
                        epoch=sample.epoch,
                        model=log.eval.model,
                        run_id=run_id,
                        harness_git_sha=harness_git_sha,
                        reward=1,
                        verifier_runs=_verifier_runs(score),
                    ),
                )
            )
    examples.sort(key=_sort_key)
    return SftDataset(
        examples=tuple(examples),
        excluded_incorrect=incorrect,
        excluded_quarantined=quarantined,
        excluded_errored=errored,
        dropped_duplicates=duplicates,
        source_run_ids=tuple(run_ids),
    )


def _sort_key(example: SFTExample) -> tuple[str, str, str, int, str]:
    prov = example.provenance
    return (prov.model, prov.eval_task_id, prov.task_id, prov.epoch, prov.run_id or "")


def _verifier_score(sample: EvalSample, scorer_name: str) -> Score:
    score = (sample.scores or {}).get(scorer_name)
    if score is None:
        raise ValueError(
            f"sample {sample.id!r} carries no {scorer_name!r} score -- the log was not produced by "
            "the drift-slice task (and the sample neither errored nor hit a limit)"
        )
    return score


def _require_reproduced_grade(score: Score, task_id: str) -> None:
    """A CORRECT must be a settled, reproduced account-B grade of THIS task, not a trusted key.

    Leg-3's scorer emits CORRECT only for a ``Reproducible`` verdict and records
    ``metadata={"verdict": "reproducible", ..., "task_id": <graded task>}``. Requiring that here
    means a foreign / partial / edited log whose sample merely carries the scorer key with a CORRECT
    value -- but no reproduced-grade metadata, or a mismatched task id -- fails closed instead of
    minting an ungrounded positive (§8 reward-boundary; the pre-T0 stand-in for #78's signature).
    """
    metadata = score.metadata or {}
    if metadata.get("verdict") != "reproducible" or metadata.get("task_id") != task_id:
        raise ValueError(
            f"sample {task_id!r} scored CORRECT but its score metadata is not a reproduced "
            f"account-B grade of this task (verdict={metadata.get('verdict')!r}, "
            f"metadata task_id={metadata.get('task_id')!r}) -- refusing an ungrounded positive"
        )


def _verifier_runs(score: Score) -> int | None:
    # The K-reproduction count behind the grade (leg-3 replay). None (not 0) when the source log
    # did not record it -- "unknown", never conflated with "zero reproductions".
    runs = (score.metadata or {}).get("runs")
    return runs if isinstance(runs, int) else None


def write_sft_jsonl(dataset: SftDataset, path: Path) -> None:
    """Write the trained columns -- one ``{messages, tools}`` JSON line per example (TRL-ready)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for example in dataset.examples:
            handle.write(json.dumps(example.training_record()) + "\n")


def write_manifest(dataset: SftDataset, path: Path) -> None:
    """Write the provenance manifest -- curation counts + per-example provenance, R1-framed.

    The ``examples`` list is aligned line-for-line with the JSONL (same order), so the manifest is a
    faithful, reproducible record of what was trained on and why (#78).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "framing": _R1_FRAMING,
        "source_run_ids": list(dataset.source_run_ids),
        "counts": {
            "examples": len(dataset.examples),
            "excluded_incorrect": dataset.excluded_incorrect,
            "excluded_quarantined": dataset.excluded_quarantined,
            "excluded_errored": dataset.excluded_errored,
            "dropped_duplicates": dataset.dropped_duplicates,
        },
        "examples": [example.provenance.model_dump(mode="json") for example in dataset.examples],
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


async def build_and_write(
    log_paths: Sequence[Path],
    out_dir: Path,
    *,
    held_out_ids: frozenset[str] = frozenset(),
    harness_git_sha: str | None = None,
    scorer_name: str = DEFAULT_SCORER_NAME,
) -> SftDataset:
    """Read graded eval logs -> build the SFT set -> write ``sft.jsonl`` + ``manifest.json``."""
    logs = [await read_eval_log_async(str(path)) for path in log_paths]
    dataset = await build_sft_dataset(
        logs,
        held_out_ids=held_out_ids,
        harness_git_sha=harness_git_sha,
        scorer_name=scorer_name,
    )
    write_sft_jsonl(dataset, out_dir / _SFT_JSONL_NAME)
    write_manifest(dataset, out_dir / _MANIFEST_NAME)
    return dataset
