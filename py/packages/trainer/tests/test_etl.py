"""#176 leg 2: the trajectory->SFT ETL -- rejection sampling on the account-B graded reward.

The trust-load-bearing behavior: an example enters the SFT set ONLY when leg-3's deploy-verifier
Score is CORRECT (reward 1 = the account-B ``verify()`` grade -- §8 reward-boundary; never the env
``step()``). INCORRECT / quarantined (unscored NaN) / errored rollouts are excluded (and counted), a
held-out task id in the training logs FAILS CLOSED (contamination -- eval-rigor/I11), duplicates are
dropped, and the output order is deterministic (a reproducible manifest).
"""

from __future__ import annotations

import asyncio

import pytest
from conftest import as_dict
from inspect_ai._util.error import EvalError
from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSample, EvalSampleLimit, EvalSpec
from inspect_ai.model import (
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
)
from inspect_ai.scorer import CORRECT, INCORRECT, Score
from inspect_ai.tool import ToolInfo, ToolParams

from assayops_trainer.etl import DEFAULT_SCORER_NAME, SftDataset, build_sft_dataset

NAN = float("nan")


def _model_event() -> ModelEvent:
    bash = ToolInfo(name="bash", description="shell", parameters=ToolParams())
    return ModelEvent(
        model="hf/base",
        input=[],
        tools=[bash],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(),
    )


def _sample(
    task_id: str,
    value: str | float,
    *,
    epoch: int = 1,
    runs: int = 3,
    metadata: dict[str, object] | None = None,
) -> EvalSample:
    # Default metadata mirrors leg-3's Reproducible grade (verdict + task_id + runs); a CORRECT is
    # admitted only against this shape. Tests override `metadata` to exercise the fail-closed path.
    meta = metadata or {"verdict": "reproducible", "reward": 1, "runs": runs, "task_id": task_id}
    return EvalSample(
        id=task_id,
        epoch=epoch,
        input="fix the drift",
        target="",
        messages=[ChatMessageUser(content=f"fix {task_id}")],
        events=[_model_event()],
        scores={DEFAULT_SCORER_NAME: Score(value=value, metadata=meta)},
    )


def _errored(task_id: str) -> EvalSample:
    return EvalSample(
        id=task_id,
        epoch=1,
        input="fix the drift",
        target="",
        error=EvalError(message="sandbox died", traceback="", traceback_ansi=""),
    )


def _log(
    model: str, samples: list[EvalSample], *, run_id: str = "run-1", status: str = "success"
) -> EvalLog:
    return EvalLog(
        eval=EvalSpec(
            run_id=run_id,
            created="2026-07-02T00:00:00+00:00",
            task="drift_slice",
            dataset=EvalDataset(),
            model=model,
            config=EvalConfig(),
        ),
        status=status,  # type: ignore[arg-type]
        samples=samples,
    )


def _build(
    *logs: EvalLog,
    held_out_ids: frozenset[str] = frozenset(),
    harness_git_sha: str | None = None,
) -> SftDataset:
    return asyncio.run(
        build_sft_dataset(list(logs), held_out_ids=held_out_ids, harness_git_sha=harness_git_sha)
    )


def test_only_reward_1_rollouts_become_examples() -> None:
    log = _log(
        "hf/base",
        [
            _sample("task-pass", CORRECT),
            _sample("task-fail", INCORRECT),
            _sample("task-flaky", NAN),
            _errored("task-broke"),
        ],
    )

    ds = _build(log, harness_git_sha="cafe")

    assert len(ds.examples) == 1
    example = ds.examples[0]
    assert example.provenance.task_id == "task-pass"
    assert example.provenance.model == "hf/base"
    assert example.provenance.run_id == "run-1"
    assert example.provenance.harness_git_sha == "cafe"
    assert example.provenance.verifier_runs == 3
    assert ds.excluded_incorrect == 1
    assert ds.excluded_quarantined == 1
    assert ds.excluded_errored == 1
    # the positive trajectory carries its messages + the tools the model saw
    assert example.messages[0]["content"] == "fix task-pass"
    assert [as_dict(tool)["function"]["name"] for tool in example.tools] == ["bash"]


def test_a_held_out_task_in_the_training_logs_fails_closed() -> None:
    # A held-out eval task appearing in a training-rollout log is contamination -- refuse it loudly
    # rather than silently training on eval data (eval-rigor / I11). Never a silent drop.
    log = _log("hf/base", [_sample("task-heldout", CORRECT)])

    with pytest.raises(ValueError, match="held-out"):
        _build(log, held_out_ids=frozenset({"task-heldout"}))


def test_duplicate_rollouts_are_dropped() -> None:
    # The same (model, task_id, epoch, run_id) rollout seen twice (e.g. overlapping log inputs) is
    # one trajectory, counted once; distinct epochs are NOT duplicates.
    log = _log("hf/base", [_sample("task-a", CORRECT, epoch=1)])

    ds = _build(log, log)  # same log passed twice

    assert len(ds.examples) == 1
    assert ds.dropped_duplicates == 1


def test_distinct_epochs_are_kept_and_output_is_deterministically_sorted() -> None:
    log = _log(
        "hf/base",
        [
            _sample("task-b", CORRECT, epoch=2),
            _sample("task-a", CORRECT, epoch=1),
            _sample("task-b", CORRECT, epoch=1),
        ],
    )

    ds = _build(log)

    keys = [(e.provenance.task_id, e.provenance.epoch) for e in ds.examples]
    assert keys == [("task-a", 1), ("task-b", 1), ("task-b", 2)]


def test_a_log_missing_the_verifier_score_fails_closed() -> None:
    bad = EvalSample(id="task-x", epoch=1, input="x", target="", scores={"other": Score(value="C")})
    with pytest.raises(ValueError, match=DEFAULT_SCORER_NAME):
        _build(_log("hf/base", [bad]))


def test_an_unexpected_score_value_fails_closed() -> None:
    with pytest.raises(ValueError, match="unexpected score value"):
        _build(_log("hf/base", [_sample("task-x", "P")]))


def test_held_out_fails_closed_even_when_the_rollout_did_not_pass() -> None:
    # The tripwire fires on ANY appearance of a held-out id in a training log -- a task that merely
    # FAILED (INCORRECT) is still the corpus-split bug the guard catches, not a silent exclusion.
    log = _log("hf/base", [_sample("task-heldout", INCORRECT)])

    with pytest.raises(ValueError, match="held-out"):
        _build(log, held_out_ids=frozenset({"task-heldout"}))


def test_a_non_success_log_fails_closed() -> None:
    # An incomplete/failed run must not become training data -- fail closed on its status, not
    # silently build from whatever partial samples it happens to carry.
    log = _log("hf/base", [_sample("task-a", CORRECT)], status="error")

    with pytest.raises(ValueError, match="not 'success'"):
        _build(log)


def test_a_correct_without_a_reproduced_grade_fails_closed() -> None:
    # A CORRECT is admitted only against reproduced-grade metadata (verdict + graded task_id). A
    # foreign/edited log with a CORRECT value but no reproduced-grade metadata is refused.
    log = _log("hf/base", [_sample("task-a", CORRECT, metadata={"runs": 3})])

    with pytest.raises(ValueError, match="ungrounded positive"):
        _build(log)


def test_a_correct_with_contradictory_reward_metadata_fails_closed() -> None:
    # A CORRECT whose own metadata claims reward 0 is not a reproduced account-B grade -- a
    # corrupted/foreign log must not mint an SFT positive (one more shape check on the pre-T0
    # stand-in; #78's signature replaces this).
    contradictory = {"verdict": "reproducible", "reward": 0, "runs": 3, "task_id": "task-a"}
    log = _log("hf/base", [_sample("task-a", CORRECT, metadata=contradictory)])

    with pytest.raises(ValueError, match="reproduced"):
        _build(log)


def test_a_boolean_runs_in_metadata_maps_to_unknown() -> None:
    # bool subclasses int: a foreign log's `"runs": true` must not fabricate a K-reproduction
    # count of 1 in the manifest -- unknown stays None.
    meta = {"verdict": "reproducible", "reward": 1, "runs": True, "task_id": "task-a"}
    log = _log("hf/base", [_sample("task-a", CORRECT, metadata=meta)])

    dataset = _build(log)

    assert dataset.examples[0].provenance.verifier_runs is None


def test_held_out_ids_has_no_default_the_split_is_an_explicit_choice() -> None:
    # The docstring's "FAILS CLOSED on any appearance" is inert under a silent empty default: the
    # split must be an explicit call-site decision (an explicit empty set = a documented operator
    # choice for the pre-T0 slice, not an accident).
    import inspect as stdlib_inspect

    from assayops_trainer.etl import build_and_write

    for entrypoint in (build_sft_dataset, build_and_write):
        parameter = stdlib_inspect.signature(entrypoint).parameters["held_out_ids"]
        assert parameter.default is stdlib_inspect.Parameter.empty, entrypoint.__name__


def test_a_correct_with_a_mismatched_metadata_task_id_fails_closed() -> None:
    bad = _sample(
        "task-a", CORRECT, metadata={"verdict": "reproducible", "task_id": "some-other-task"}
    )
    with pytest.raises(ValueError, match="ungrounded positive"):
        _build(_log("hf/base", [bad]))


def test_a_limit_hit_sample_is_excluded_not_crashing() -> None:
    # A non-errored sample that hit a limit is unscored -> an incomplete rollout, excluded like an
    # error, NOT a whole-build crash (and NOT a foreign-log fail-closed).
    limited = EvalSample(
        id="task-lim",
        epoch=1,
        input="x",
        target="",
        limit=EvalSampleLimit(type="message", limit=50),
    )
    ds = _build(_log("hf/base", [limited, _sample("task-a", CORRECT)]))

    assert len(ds.examples) == 1
    assert ds.excluded_errored == 1


def test_verifier_runs_is_none_when_the_log_omits_it() -> None:
    # A reproduced grade (verdict + task_id + reward) whose K count is missing -> unknown, not 0.
    meta = {"verdict": "reproducible", "reward": 1, "task_id": "task-a"}
    log = _log("hf/base", [_sample("task-a", CORRECT, metadata=meta)])

    assert _build(log).examples[0].provenance.verifier_runs is None


def test_source_run_ids_are_deduped() -> None:
    log = _log("hf/base", [_sample("task-a", CORRECT)])

    assert _build(log, log).source_run_ids == ("run-1",)


def test_default_scorer_name_matches_the_evals_log_key_contract() -> None:
    # The ETL reads the graded reward by the log key leg-3's scorer registers. DRY-by-verification:
    # keep the trainer's runtime dep graph free of the verifier stack (a literal here), but lock the
    # contract so an evals-side rename can't silently orphan this reader.
    from assayops_evals.scorer import DEPLOY_VERIFIER_SCORER_NAME

    assert DEFAULT_SCORER_NAME == DEPLOY_VERIFIER_SCORER_NAME
