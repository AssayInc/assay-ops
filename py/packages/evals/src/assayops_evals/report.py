"""The directional pass-rate-delta report -- the slice's one output artifact, R1-framed.

Computes base-vs-SFT pass rates from two Inspect eval logs of the drift-slice task and renders
them with the R1 framing HARD-CODED in (eval-rigor): this number is pre-T0 directional,
LocalStack-graded, and NOT the E13 proof -- it must never be published or pitched, and the
artifact says so on its face so it cannot be innocently reused. Quarantined rollouts (the unscored
NaN sentinel) are excluded from the headline rate, never counted as failures (7A: a quarantine is
not a wrong answer -- counting it as 0 would poison the delta with a false negative).

Honesty guards for a directional (non-adversarial-SFT, never-published) number:
- Only a ``status == "success"`` log reports (an interrupted run must not yield a delta).
- A CONSERVATIVE lower-bound rate that counts quarantines AND errored/limit-cut rollouts as
  failures is reported alongside the headline. Pre-T0 the substrate is agent-reachable (the R1
  caveat), so a policy could in principle dodge a settled 0 two ways: farm quarantines (transient
  budget) or wedge the substrate hard enough to error/cancel the scoring. The bracket
  [lower-bound, headline] covers both dodge shapes instead of silently trusting the excluded rate.
- DIVERGENCE warnings when the two models quarantine OR error at materially different rates (the
  signature of such farming, or just an uneven run) -- the delta is then low-confidence.
None of these changes a score (7A holds); they frame the number for the reader.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.scorer import CORRECT, INCORRECT, Score

from assayops_evals.scorer import DEPLOY_VERIFIER_SCORER_NAME

_R1_FRAMING = (
    "PRE-T0 DIRECTIONAL SIGNAL -- LocalStack-graded, NOT the E13 proof.\n"
    "Never publish or pitch this number (R1: no external claim on a reward without the full\n"
    "trust stack; DECISIONS.md section 5/section 6, docs/priorities.md P1)."
)

# A per-model quarantine OR error fraction differing by more than this is flagged: a divergent
# rate is the signature of a substrate-induced dodge (a flaky/throttled/wedged rollout is pulled
# from the denominator, so one model quarantining or erroring far more can inflate its headline
# rate) or simply an uneven run. It does not change a score (7A: a quarantine is never a false 0),
# only the confidence.
_RATE_DIVERGENCE_WARN = 0.15


@dataclass(frozen=True)
class ModelSlice:
    """One model's slice outcome over its rollouts (scored + quarantined + errored)."""

    model: str
    task_ids: frozenset[str]
    passed: int
    failed: int
    quarantined: int
    # Incomplete rollouts: an infra/scoring error OR a limit hit that left no settled grade.
    errored: int

    @property
    def tasks(self) -> int:
        return len(self.task_ids)

    @property
    def scored(self) -> int:
        """Rollouts with a settled grade (CORRECT or INCORRECT) -- the headline denominator."""
        return self.passed + self.failed

    @property
    def rollouts(self) -> int:
        return self.scored + self.quarantined + self.errored

    @property
    def pass_rate(self) -> float:
        """Headline rate: passes over settled rollouts (quarantined + errored excluded)."""
        return self.passed / self.scored

    @property
    def pass_rate_lower_bound(self) -> float:
        """Conservative rate: quarantined AND errored rollouts counted as failures.

        The anti-farming floor: what the rate is if every rollout that dodged a settled grade --
        a farmed quarantine (transient budget) or a substrate wedged hard enough to error/cancel
        the scoring -- was really a failure the substrate hid.
        """
        denominator = self.scored + self.quarantined + self.errored
        return self.passed / denominator if denominator else 0.0

    @property
    def quarantine_fraction(self) -> float:
        return self.quarantined / self.rollouts if self.rollouts else 0.0

    @property
    def error_fraction(self) -> float:
        return self.errored / self.rollouts if self.rollouts else 0.0


@dataclass(frozen=True)
class DirectionalDelta:
    """The base-vs-SFT directional read; ``delta`` is sft minus base, in pass-rate points."""

    base: ModelSlice
    sft: ModelSlice

    @property
    def delta(self) -> float:
        return self.sft.pass_rate - self.base.pass_rate

    @property
    def quarantine_rates_diverge(self) -> bool:
        return (
            abs(self.sft.quarantine_fraction - self.base.quarantine_fraction)
            > _RATE_DIVERGENCE_WARN
        )

    @property
    def error_rates_diverge(self) -> bool:
        return abs(self.sft.error_fraction - self.base.error_fraction) > _RATE_DIVERGENCE_WARN


def directional_delta(base: EvalLog, sft: EvalLog) -> DirectionalDelta:
    """Both logs' verifier scores -> the directional read, fail-closed on non-comparable logs.

    Refuses two logs that are not a base-vs-SFT pair over the SAME slice: they must run the same
    task and the same ROLLOUT GRID -- the identical ``(task_id, epoch)`` multiset (same tasks AND
    same epoch count per task, including any errored/quarantined rollouts, which still appear as
    samples). Otherwise the "delta" compares different work / a different n and is meaningless -- an
    honest-mistake guard for a directional number (eval-rigor). Comparing task-id SETS alone would
    miss a base run at epochs=3 vs an sft run at epochs=1.
    """
    base_slice = _slice_of(base)
    sft_slice = _slice_of(sft)
    _require_comparable(base, sft)
    return DirectionalDelta(base=base_slice, sft=sft_slice)


def _rollout_grid(log: EvalLog) -> Counter[tuple[str, int]]:
    # Reached only after _slice_of has confirmed samples are present; `or ()` keeps mypy happy.
    return Counter((str(sample.id), sample.epoch) for sample in log.samples or ())


def _require_comparable(base: EvalLog, sft: EvalLog) -> None:
    if base.eval.task != sft.eval.task:
        raise ValueError(
            f"logs are not comparable: base ran task {base.eval.task!r}, sft ran "
            f"{sft.eval.task!r} -- the directional delta compares one slice across two models"
        )
    base_grid = _rollout_grid(base)
    sft_grid = _rollout_grid(sft)
    if base_grid != sft_grid:
        only_base = sorted(base_grid - sft_grid)
        only_sft = sorted(sft_grid - base_grid)
        raise ValueError(
            "logs cover a different rollout grid -- not a base-vs-SFT pair over the same slice "
            f"(same task/epoch (id, epoch) rollouts required; only in base: {only_base}; only in "
            f"sft: {only_sft})"
        )


def render_report(delta: DirectionalDelta) -> str:
    lines = [
        "== AssayOps #176 directional slice: base vs SFT ==",
        _R1_FRAMING,
        "",
        _slice_line("base", delta.base),
        _slice_line("sft ", delta.sft),
        f"delta (sft - base): {delta.delta * 100:+.1f} points (headline; quarantined excluded)",
    ]
    if delta.quarantine_rates_diverge:
        lines.append(
            "WARNING: base and sft quarantine at materially different rates -- the delta is "
            "low-confidence (compare the lower-bound rates and inspect the quarantined rollouts)."
        )
    if delta.error_rates_diverge:
        lines.append(
            "WARNING: base and sft error/limit out at materially different rates -- the delta is "
            "low-confidence (compare the lower-bound rates and inspect the errored rollouts)."
        )
    return "\n".join(lines)


def _slice_line(label: str, model_slice: ModelSlice) -> str:
    line = (
        f"{label} {model_slice.model}: pass {model_slice.passed}/{model_slice.scored} "
        f"({model_slice.pass_rate * 100:.1f}%) "
        f"[{model_slice.tasks} tasks; {model_slice.quarantined} quarantined; "
        f"{model_slice.errored} errored]"
    )
    if model_slice.quarantined or model_slice.errored:
        lower = model_slice.pass_rate_lower_bound * 100
        line += f" (>= {lower:.1f}% counting quarantined/errored as fails)"
    return line


def _slice_of(log: EvalLog) -> ModelSlice:
    if log.status != "success":
        raise ValueError(
            f"eval log for {log.eval.model!r} has status {log.status!r}, not 'success' -- "
            "refusing to report a rate from an incomplete/failed run (fail closed)"
        )
    if not log.samples:
        raise ValueError(f"eval log for {log.eval.model!r} has no samples (need a full log)")
    passed = failed = quarantined = errored = 0
    for sample in log.samples:
        if sample.error is not None:
            # An infra failure (sandbox/scoring error), not a graded deploy -- excluded from the
            # headline, bracketed by the lower bound, never crashes the report on one rollout.
            errored += 1
            continue
        if sample.limit is not None and _verifier_score_of(sample) is None:
            # Cut by a message/time limit before/during scoring -> an incomplete rollout, excluded
            # like an error. A limit-hit rollout that WAS scored falls through: the deployed state
            # was graded, and an unfinished fix deserves its settled 0.
            errored += 1
            continue
        value = _verifier_value(sample)
        if isinstance(value, float) and math.isnan(value):
            quarantined += 1
        elif value == CORRECT:
            passed += 1
        elif value == INCORRECT:
            failed += 1
        else:
            raise ValueError(
                f"unexpected score value {value!r} for sample {sample.id!r} -- the "
                "deploy-verifier scorer emits only CORRECT / INCORRECT / unscored"
            )
    if passed + failed == 0:
        raise ValueError(
            f"eval log for {log.eval.model!r} has no scored rollouts "
            f"({quarantined} quarantined, {errored} errored) -- no rate to report"
        )
    return ModelSlice(
        model=log.eval.model,
        # EvalSample.id is int | str; our task ids are strings, but coerce so the set is uniform.
        task_ids=frozenset(str(sample.id) for sample in log.samples if sample.id is not None),
        passed=passed,
        failed=failed,
        quarantined=quarantined,
        errored=errored,
    )


def _verifier_score_of(sample: EvalSample) -> Score | None:
    return (sample.scores or {}).get(DEPLOY_VERIFIER_SCORER_NAME)


def _verifier_value(sample: EvalSample) -> object:
    score = _verifier_score_of(sample)
    if score is None:
        raise ValueError(
            f"sample {sample.id!r} carries no {DEPLOY_VERIFIER_SCORER_NAME!r} score -- the log "
            "was not produced by the drift-slice task (and the sample neither errored nor was "
            "cut by a limit)"
        )
    return score.value
