"""#176 leg 3: the directional pass-rate-delta report -- R1-framed, quarantine-aware.

The report is the slice's one output artifact, so the R1 framing is HARD-CODED into it: the number
is pre-T0 directional, LocalStack-graded, and never the E13 proof -- it cannot be innocently
copy-pasted without that context. Quarantined rollouts (the unscored NaN sentinel) are excluded
from the rate, never counted as failures (7A: a quarantine is not a wrong answer).
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from inspect_ai._util.error import EvalError
from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSample, EvalSpec
from inspect_ai.scorer import CORRECT, INCORRECT, Score

from assayops_evals.report import directional_delta, render_report
from assayops_evals.scorer import DEPLOY_VERIFIER_SCORER_NAME

NAN = float("nan")


def _sample(
    sample_id: str, value: str | float, epoch: int = 1, scorer: str | None = None
) -> EvalSample:
    return EvalSample(
        id=sample_id,
        epoch=epoch,
        input="fix the drift",
        target="",
        scores={scorer or DEPLOY_VERIFIER_SCORER_NAME: Score(value=value)},
    )


def _errored_sample(sample_id: str) -> EvalSample:
    return EvalSample(
        id=sample_id,
        epoch=1,
        input="fix the drift",
        target="",
        error=EvalError(message="sandbox died", traceback="", traceback_ansi=""),
    )


def _make_log(model: str, samples: list[EvalSample], task: str = "drift_slice") -> EvalLog:
    return EvalLog(
        eval=EvalSpec(
            created="2026-07-01T00:00:00+00:00",
            task=task,
            dataset=EvalDataset(),
            model=model,
            config=EvalConfig(),
        ),
        samples=samples,
    )


def _log(model: str, values: list[str | float], scorer: str | None = None) -> EvalLog:
    samples = [_sample(f"task-{index}", value, scorer=scorer) for index, value in enumerate(values)]
    return _make_log(model, samples)


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
    # The report extracts scores by the name the @scorer decorator registers -- which it derives
    # from the factory's __name__ (preserved through the decorator). A rename changes __name__ and
    # the registered log key together while the constant stays, so this public-surface check
    # catches the drift without reaching into inspect_ai's private registry internals.
    from assayops_evals.scorer import deploy_verifier_scorer

    assert deploy_verifier_scorer.__name__ == DEPLOY_VERIFIER_SCORER_NAME


def test_nan_never_leaks_into_the_delta() -> None:
    base = _log("hf/base", [CORRECT, NAN])
    sft = _log("hf/sft", [CORRECT, CORRECT])

    delta = directional_delta(base, sft)

    assert not math.isnan(delta.delta)


def test_multi_epoch_rollouts_count_tasks_by_distinct_id() -> None:
    # Production runs epochs>1: many EvalSamples share one task id. `tasks` must dedup by id while
    # the rate counts every rollout. (The test-only single-epoch logs above never exercise this.)
    samples = [
        _sample(f"task-{t}", CORRECT if epoch == 1 else INCORRECT, epoch=epoch)
        for t in range(2)
        for epoch in range(1, 4)
    ]
    log = _make_log("hf/base", samples)

    model_slice = directional_delta(log, log).base

    assert model_slice.tasks == 2
    assert model_slice.scored == 6
    assert model_slice.pass_rate == pytest.approx(2 / 6)


def test_errored_samples_are_excluded_not_crashing() -> None:
    # An infra-errored rollout (sandbox/scoring failure) must not crash the whole report on one
    # flaky sample; it is excluded from the rate like a quarantine and surfaced as `errored`.
    base = _make_log("hf/base", [_sample("task-0", CORRECT), _errored_sample("task-1")])
    sft = _make_log("hf/sft", [_sample("task-0", CORRECT), _sample("task-1", INCORRECT)])

    delta = directional_delta(base, sft)

    assert delta.base.errored == 1
    assert delta.base.scored == 1
    assert delta.base.pass_rate == 1.0
    assert "errored" in render_report(delta)


def test_a_lower_bound_rate_counts_quarantines_as_failures() -> None:
    base = _log("hf/base", [CORRECT, CORRECT, NAN, NAN])
    sft = _log("hf/sft", [CORRECT, CORRECT, INCORRECT, INCORRECT])

    delta = directional_delta(base, sft)

    # headline: 2/2 scored = 100%; lower bound counts the 2 quarantines as fails: 2/4 = 50%.
    assert delta.base.pass_rate == 1.0
    assert delta.base.pass_rate_lower_bound == 0.5
    report = render_report(delta)
    assert "counting quarantines as fails" in report


def test_divergent_quarantine_rates_warn() -> None:
    # base quarantines heavily, sft not at all -> the delta is low-confidence; the report warns.
    base = _log("hf/base", [CORRECT, NAN, NAN, NAN])
    sft = _log("hf/sft", [CORRECT, CORRECT, INCORRECT, INCORRECT])

    delta = directional_delta(base, sft)

    assert delta.quarantine_rates_diverge
    assert "WARNING" in render_report(delta)


def test_even_quarantine_rates_do_not_warn() -> None:
    base = _log("hf/base", [CORRECT, INCORRECT])
    sft = _log("hf/sft", [CORRECT, CORRECT])

    assert not directional_delta(base, sft).quarantine_rates_diverge
    assert "WARNING" not in render_report(directional_delta(base, sft))


def test_mismatched_task_sets_fail_closed() -> None:
    base = _make_log("hf/base", [_sample("task-a", CORRECT), _sample("task-b", INCORRECT)])
    sft = _make_log("hf/sft", [_sample("task-a", CORRECT), _sample("task-c", CORRECT)])

    with pytest.raises(ValueError, match="different rollout grid"):
        directional_delta(base, sft)


def test_mismatched_epoch_multiplicity_fails_closed() -> None:
    # Same task ids, different epoch counts (base ran epochs=3, sft epochs=1) is NOT a comparable
    # pair -- the delta would span different n. The rollout-grid multiset catches it (a task-id-set
    # check would not).
    base = _make_log("hf/base", [_sample("task-a", CORRECT, epoch=e) for e in (1, 2, 3)])
    sft = _make_log("hf/sft", [_sample("task-a", CORRECT)])

    with pytest.raises(ValueError, match="different rollout grid"):
        directional_delta(base, sft)


def test_mismatched_task_names_fail_closed() -> None:
    base = _make_log("hf/base", [_sample("task-0", CORRECT)], task="drift_slice")
    sft = _make_log("hf/sft", [_sample("task-0", CORRECT)], task="some_other_task")

    with pytest.raises(ValueError, match="not comparable"):
        directional_delta(base, sft)


def test_quarantine_sentinel_survives_a_real_inspect_log_round_trip(tmp_path: Path) -> None:
    # The report's one integration seam with inspect's log format: a Score.unscored() NaN must
    # survive write_eval_log -> read_eval_log (raw pydantic json would corrupt it to null).
    from inspect_ai.log import read_eval_log, write_eval_log
    from inspect_ai.scorer import Score

    quarantined = EvalSample(
        id="task-0",
        epoch=1,
        input="fix the drift",
        target="",
        scores={DEPLOY_VERIFIER_SCORER_NAME: Score.unscored()},
    )
    log = _make_log("hf/base", [_sample("task-1", CORRECT), quarantined])
    path = str(tmp_path / "base.eval")
    write_eval_log(log, path)
    reloaded = read_eval_log(path)

    model_slice = directional_delta(reloaded, reloaded).base
    assert model_slice.quarantined == 1
    assert model_slice.scored == 1
