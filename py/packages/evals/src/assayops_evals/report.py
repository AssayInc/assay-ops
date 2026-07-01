"""The directional pass-rate-delta report -- the slice's one output artifact, R1-framed.

Computes base-vs-SFT pass rates from two Inspect eval logs of the drift-slice task and renders
them with the R1 framing HARD-CODED in (eval-rigor): this number is pre-T0 directional,
LocalStack-graded, and NOT the E13 proof -- it must never be published or pitched, and the
artifact says so on its face so it cannot be innocently reused. Quarantined rollouts (the unscored
NaN sentinel) are excluded from the rate, never counted as failures (7A: a quarantine is not a
wrong answer -- counting it as 0 would poison the delta with a false negative).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.scorer import CORRECT, INCORRECT

# The registry name the @scorer decorator derives from the factory function.
DEPLOY_VERIFIER_SCORER_NAME = "deploy_verifier_scorer"

_R1_FRAMING = (
    "PRE-T0 DIRECTIONAL SIGNAL -- LocalStack-graded, NOT the E13 proof.\n"
    "Never publish or pitch this number (R1: no external claim on a reward without the full\n"
    "trust stack; DECISIONS.md section 5/section 6, docs/priorities.md P1)."
)


@dataclass(frozen=True)
class ModelSlice:
    """One model's slice outcome: scored/passed/quarantined rollout counts."""

    model: str
    tasks: int
    scored: int
    passed: int
    quarantined: int

    @property
    def pass_rate(self) -> float:
        return self.passed / self.scored


@dataclass(frozen=True)
class DirectionalDelta:
    """The base-vs-SFT directional read; ``delta`` is sft minus base, in pass-rate points."""

    base: ModelSlice
    sft: ModelSlice

    @property
    def delta(self) -> float:
        return self.sft.pass_rate - self.base.pass_rate


def directional_delta(base: EvalLog, sft: EvalLog) -> DirectionalDelta:
    """Extract both logs' verifier scores (fail closed on anything this harness never emits)."""
    return DirectionalDelta(base=_slice_of(base), sft=_slice_of(sft))


def render_report(delta: DirectionalDelta) -> str:
    lines = [
        "== AssayOps #176 directional slice: base vs SFT ==",
        _R1_FRAMING,
        "",
        _slice_line("base", delta.base),
        _slice_line("sft ", delta.sft),
        f"delta (sft - base): {delta.delta * 100:+.1f} points",
    ]
    return "\n".join(lines)


def _slice_line(label: str, model_slice: ModelSlice) -> str:
    return (
        f"{label} {model_slice.model}: pass {model_slice.passed}/{model_slice.scored} "
        f"({model_slice.pass_rate * 100:.1f}%) "
        f"[{model_slice.tasks} tasks; {model_slice.quarantined} quarantined]"
    )


def _slice_of(log: EvalLog) -> ModelSlice:
    if not log.samples:
        raise ValueError(f"eval log for {log.eval.model!r} has no samples (need a full log)")
    passed = failed = quarantined = 0
    for sample in log.samples:
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
    scored = passed + failed
    if scored == 0:
        raise ValueError(
            f"eval log for {log.eval.model!r} has no scored rollouts "
            f"({quarantined} quarantined) -- no rate to report"
        )
    return ModelSlice(
        model=log.eval.model,
        tasks=len({sample.id for sample in log.samples}),
        scored=scored,
        passed=passed,
        quarantined=quarantined,
    )


def _verifier_value(sample: EvalSample) -> object:
    score = (sample.scores or {}).get(DEPLOY_VERIFIER_SCORER_NAME)
    if score is None:
        raise ValueError(
            f"sample {sample.id!r} carries no {DEPLOY_VERIFIER_SCORER_NAME!r} score -- the log "
            "was not produced by the drift-slice task"
        )
    return score.value
