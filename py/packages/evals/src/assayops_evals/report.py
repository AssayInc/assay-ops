"""The directional pass-rate-delta report -- the slice's one output artifact, R1-framed.

Computes base-vs-SFT pass rates from two Inspect eval logs of the drift-slice task and renders
them with the R1 framing HARD-CODED in (eval-rigor): this number is pre-T0 directional,
LocalStack-graded, and NOT the E13 proof -- it must never be published or pitched, and the
artifact says so on its face so it cannot be innocently reused. Quarantined rollouts (the unscored
NaN sentinel) are excluded from the headline rate, never counted as failures (7A: a quarantine is
not a wrong answer -- counting it as 0 would poison the delta with a false negative).

Two honesty guards for a directional (non-adversarial-SFT, never-published) number:
- A CONSERVATIVE lower-bound rate that DOES count quarantines as failures is reported alongside the
  headline. Pre-T0 the substrate is agent-reachable (the R1 caveat), so a policy could in principle
  farm quarantines to dodge failures; the bracket [lower-bound, headline] makes that visible instead
  of silently trusting the excluded-quarantine rate.
- A DIVERGENCE warning when the two models quarantine at materially different rates (the signature
  of such farming, or just an uneven run) -- the delta is then low-confidence.
Neither changes a score (7A holds); they frame the number for the reader.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.scorer import CORRECT, INCORRECT

from assayops_evals.scorer import DEPLOY_VERIFIER_SCORER_NAME

_R1_FRAMING = (
    "PRE-T0 DIRECTIONAL SIGNAL -- LocalStack-graded, NOT the E13 proof.\n"
    "Never publish or pitch this number (R1: no external claim on a reward without the full\n"
    "trust stack; DECISIONS.md section 5/section 6, docs/priorities.md P1)."
)

# A per-model quarantine fraction differing by more than this is flagged: a divergent quarantine
# rate is the signature of a substrate-induced dodge (a flaky/throttled rollout is pulled from the
# denominator, so one model quarantining far more can inflate its headline rate) or simply an
# uneven run. It does not change a score (7A: a quarantine is never a false 0), only the confidence.
_QUARANTINE_DIVERGENCE_WARN = 0.15


@dataclass(frozen=True)
class ModelSlice:
    """One model's slice outcome over its rollouts (scored + quarantined + errored)."""

    model: str
    task_ids: frozenset[str]
    passed: int
    failed: int
    quarantined: int
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
        """Conservative rate: quarantines counted as failures (errored still excluded -- infra,

        not the agent's deploy). The anti-farming floor: what the rate is if every quarantined
        rollout was really a failure the substrate hid.
        """
        denominator = self.scored + self.quarantined
        return self.passed / denominator if denominator else 0.0

    @property
    def quarantine_fraction(self) -> float:
        return self.quarantined / self.rollouts if self.rollouts else 0.0


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
            > _QUARANTINE_DIVERGENCE_WARN
        )


def directional_delta(base: EvalLog, sft: EvalLog) -> DirectionalDelta:
    """Both logs' verifier scores -> the directional read, fail-closed on non-comparable logs.

    Refuses two logs that are not a base-vs-SFT pair over the SAME slice: they must run the same
    task and cover the same set of task ids (else the "delta" compares different work and is
    meaningless -- an honest-mistake guard for a directional number, eval-rigor).
    """
    base_slice = _slice_of(base)
    sft_slice = _slice_of(sft)
    _require_comparable(base, sft, base_slice, sft_slice)
    return DirectionalDelta(base=base_slice, sft=sft_slice)


def _require_comparable(
    base: EvalLog, sft: EvalLog, base_slice: ModelSlice, sft_slice: ModelSlice
) -> None:
    if base.eval.task != sft.eval.task:
        raise ValueError(
            f"logs are not comparable: base ran task {base.eval.task!r}, sft ran "
            f"{sft.eval.task!r} -- the directional delta compares one slice across two models"
        )
    if base_slice.task_ids != sft_slice.task_ids:
        only_base = sorted(base_slice.task_ids - sft_slice.task_ids)
        only_sft = sorted(sft_slice.task_ids - base_slice.task_ids)
        raise ValueError(
            "logs cover different task sets -- not a base-vs-SFT pair over the same slice "
            f"(only in base: {only_base}; only in sft: {only_sft})"
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
    return "\n".join(lines)


def _slice_line(label: str, model_slice: ModelSlice) -> str:
    line = (
        f"{label} {model_slice.model}: pass {model_slice.passed}/{model_slice.scored} "
        f"({model_slice.pass_rate * 100:.1f}%) "
        f"[{model_slice.tasks} tasks; {model_slice.quarantined} quarantined; "
        f"{model_slice.errored} errored]"
    )
    if model_slice.quarantined:
        lower = model_slice.pass_rate_lower_bound * 100
        line += f" (>= {lower:.1f}% counting quarantines as fails)"
    return line


def _slice_of(log: EvalLog) -> ModelSlice:
    if not log.samples:
        raise ValueError(f"eval log for {log.eval.model!r} has no samples (need a full log)")
    passed = failed = quarantined = errored = 0
    for sample in log.samples:
        if sample.error is not None:
            # An infra failure (sandbox/scoring error), not a graded deploy -- excluded from the
            # rate like a quarantine, never crashes the whole report on one flaky rollout.
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


def _verifier_value(sample: EvalSample) -> object:
    score = (sample.scores or {}).get(DEPLOY_VERIFIER_SCORER_NAME)
    if score is None:
        raise ValueError(
            f"sample {sample.id!r} carries no {DEPLOY_VERIFIER_SCORER_NAME!r} score -- the log "
            "was not produced by the drift-slice task (and the sample did not error)"
        )
    return score.value
