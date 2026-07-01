"""#176 leg 3: the directional pass-rate-delta report -- R1-framed, quarantine-aware.

The report is the slice's one output artifact, so the R1 framing is HARD-CODED into it: the number
is pre-T0 directional, LocalStack-graded, and never the E13 proof -- it cannot be innocently
copy-pasted without that context. Quarantined rollouts (the unscored NaN sentinel) are excluded
from the rate, never counted as failures (7A: a quarantine is not a wrong answer).
"""

from __future__ import annotations

import math

import pytest
from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSample, EvalSpec
from inspect_ai.scorer import CORRECT, INCORRECT, Score

from assayops_evals.report import DEPLOY_VERIFIER_SCORER_NAME, directional_delta, render_report

NAN = float("nan")


def _log(model: str, values: list[str | float], scorer: str | None = None) -> EvalLog:
    samples = [
        EvalSample(
            id=f"task-{index}",
            epoch=1,
            input="fix the drift",
            target="",
            scores={scorer or DEPLOY_VERIFIER_SCORER_NAME: Score(value=value)},
        )
        for index, value in enumerate(values)
    ]
    return EvalLog(
        eval=EvalSpec(
            created="2026-07-01T00:00:00+00:00",
            task="drift_slice",
            dataset=EvalDataset(),
            model=model,
            config=EvalConfig(),
        ),
        samples=samples,
    )


def test_directional_delta_computes_pass_rates_and_the_delta() -> None:
    base = _log("hf/base", [CORRECT, INCORRECT, INCORRECT, INCORRECT])
    sft = _log("hf/sft", [CORRECT, CORRECT, CORRECT, INCORRECT])

    delta = directional_delta(base, sft)

    assert delta.base.model == "hf/base"
    assert delta.base.scored == 4
    assert delta.base.passed == 1
    assert delta.base.pass_rate == 0.25
    assert delta.sft.pass_rate == 0.75
    assert delta.delta == 0.5


def test_quarantined_rollouts_are_excluded_from_the_rate() -> None:
    base = _log("hf/base", [CORRECT, INCORRECT, NAN])
    sft = _log("hf/sft", [CORRECT, CORRECT, INCORRECT])

    delta = directional_delta(base, sft)

    assert delta.base.scored == 2
    assert delta.base.quarantined == 1
    assert delta.base.pass_rate == 0.5


def test_the_report_carries_the_hard_coded_r1_framing() -> None:
    base = _log("hf/base", [CORRECT, INCORRECT])
    sft = _log("hf/sft", [CORRECT, CORRECT])

    report = render_report(directional_delta(base, sft))

    assert "PRE-T0 DIRECTIONAL" in report
    assert "NOT the E13 proof" in report
    assert "Never publish" in report
    assert "hf/base" in report and "hf/sft" in report


def test_an_all_quarantined_log_fails_closed() -> None:
    base = _log("hf/base", [NAN, NAN])
    sft = _log("hf/sft", [CORRECT])

    with pytest.raises(ValueError, match="no scored"):
        directional_delta(base, sft)


def test_a_log_without_the_verifier_score_fails_closed() -> None:
    base = _log("hf/base", [CORRECT], scorer="some_other_scorer")
    sft = _log("hf/sft", [CORRECT])

    with pytest.raises(ValueError, match=DEPLOY_VERIFIER_SCORER_NAME):
        directional_delta(base, sft)


def test_an_unexpected_score_value_fails_closed() -> None:
    # The deploy-verifier scorer emits only CORRECT / INCORRECT / the unscored NaN; anything else
    # in the log means it was not produced by this harness -- never silently coerced into a rate.
    base = _log("hf/base", ["P"])
    sft = _log("hf/sft", [CORRECT])

    with pytest.raises(ValueError, match="unexpected score value"):
        directional_delta(base, sft)


def test_a_log_without_samples_fails_closed() -> None:
    base = _log("hf/base", [])
    sft = _log("hf/sft", [CORRECT])

    with pytest.raises(ValueError, match="no samples"):
        directional_delta(base, sft)


def test_the_scorer_name_constant_matches_the_registered_scorer() -> None:
    # The report extracts scores by the name the @scorer decorator registers; a scorer rename
    # would silently break extraction, so the coupling is locked here. (registry_info is
    # inspect-internal, but the registered name IS the public log key -- worth the private import.)
    from inspect_ai._util.registry import registry_info

    from assayops_evals.scorer import deploy_verifier_scorer

    assert registry_info(deploy_verifier_scorer).name == DEPLOY_VERIFIER_SCORER_NAME


def test_nan_never_leaks_into_the_delta() -> None:
    base = _log("hf/base", [CORRECT, NAN])
    sft = _log("hf/sft", [CORRECT, CORRECT])

    delta = directional_delta(base, sft)

    assert not math.isnan(delta.delta)
