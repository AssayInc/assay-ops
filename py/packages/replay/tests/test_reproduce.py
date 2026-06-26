"""K-run reproduce + quarantine (DECISIONS.md 7A / T8): drive a grade callable K times, absorb
transient failures within a bounded budget, and **quarantine** a non-reproducing (flaky) task so its
reward is never silently shipped (vector #15). Decoupled from the live read — the grade callable is
injected, which is exactly how the acceptance criterion injects a nondeterministic task.
"""

from __future__ import annotations

import pytest
from assayops_contracts import Reward
from assayops_contracts.jcs import canonicalize
from assayops_diff_ir import GradeOutcome
from fixtures import FakeClientError, reward_0, reward_0_other, reward_1

from assayops_replay import (
    Quarantined,
    Reproducible,
    TransientBudgetExhausted,
    TransientGradeError,
    TransientKind,
    reproduce,
)


def test_deterministic_reward_1_is_reproducible() -> None:
    verdict = reproduce(reward_1, runs=5)
    assert isinstance(verdict, Reproducible)
    assert verdict.reward is Reward.number_1
    assert verdict.runs == 5


def test_deterministic_reward_0_is_reproducible() -> None:
    verdict = reproduce(reward_0, runs=5)
    assert isinstance(verdict, Reproducible)
    assert verdict.reward is Reward.number_0


def test_default_runs_applied() -> None:
    # K defaults to a small >= 3 run count (DECISIONS.md leaves K a parameter, not a locked number).
    verdict = reproduce(reward_1)
    assert isinstance(verdict, Reproducible)
    assert verdict.runs >= 3


def test_injected_nondeterministic_task_is_quarantined() -> None:
    # THE acceptance criterion: a task whose grade flips across runs is flaky — quarantined, never
    # silently rewarded; tested with an injected nondeterministic task.
    outcomes = [reward_1(), reward_0()]
    calls = {"n": 0}

    def flaky() -> GradeOutcome:
        outcome = outcomes[calls["n"] % len(outcomes)]
        calls["n"] += 1
        return outcome

    verdict = reproduce(flaky, runs=4)

    assert isinstance(verdict, Quarantined)
    assert not hasattr(verdict, "reward")  # type-enforced: a flaky task exposes NO reward
    assert verdict.distinct_outcomes >= 2
    assert verdict.runs == 4


def test_transient_then_stable_is_absorbed() -> None:
    # A read-after-create eventual-consistency transient on a run's first attempt must be absorbed
    # by the bounded retry, NOT counted as flakiness or scored as a false-negative 0.
    calls = {"n": 0}

    def transient_once() -> GradeOutcome:
        calls["n"] += 1
        if calls["n"] == 1:
            raise TransientGradeError(TransientKind.EVENTUAL_CONSISTENCY, "not yet visible")
        return reward_1()

    verdict = reproduce(transient_once, runs=3, sleep=lambda _d: None)
    assert isinstance(verdict, Reproducible)
    assert verdict.reward is Reward.number_1


def test_transient_retry_invokes_injected_backoff() -> None:
    slept: list[float] = []
    calls = {"n": 0}

    def transient_once() -> GradeOutcome:
        calls["n"] += 1
        if calls["n"] == 1:
            raise TransientGradeError(TransientKind.EVENTUAL_CONSISTENCY, "not yet visible")
        return reward_1()

    reproduce(transient_once, runs=2, sleep=slept.append)
    assert len(slept) == 1  # exactly one backoff sleep for the single transient retry


def test_genuine_bug_fails_closed_not_retried() -> None:
    calls = {"n": 0}

    def genuine() -> GradeOutcome:
        calls["n"] += 1
        raise RuntimeError("verifier internal error")

    with pytest.raises(RuntimeError):
        reproduce(genuine, runs=3)
    assert calls["n"] == 1  # genuine ⇒ NOT retried; fail closed on the first attempt


def test_access_denied_fails_closed_not_masked() -> None:
    # AccessDenied is an isolation/permissions alarm — genuine, never retried into a silent reward.
    calls = {"n": 0}

    def denied() -> GradeOutcome:
        calls["n"] += 1
        raise FakeClientError("AccessDeniedException")

    with pytest.raises(FakeClientError):
        reproduce(denied, runs=3, sleep=lambda _d: None)
    assert calls["n"] == 1


def test_transient_budget_exhausted_fails_closed_with_kind() -> None:
    # A transient that never settles within the budget fails closed via TransientBudgetExhausted —
    # bounded retries, never an unbounded loop, never reward 1. The kind is carried so the caller
    # maps it: EVENTUAL_CONSISTENCY (NotFound) ⇒ reward 0; INFRA (throttle) ⇒ quarantine.
    calls = {"n": 0}

    def always_eventual_consistency() -> GradeOutcome:
        calls["n"] += 1
        raise TransientGradeError(TransientKind.EVENTUAL_CONSISTENCY, "never settles")

    with pytest.raises(TransientBudgetExhausted) as exc_info:
        reproduce(
            always_eventual_consistency, runs=2, max_transient_retries=2, sleep=lambda _d: None
        )
    assert exc_info.value.kind is TransientKind.EVENTUAL_CONSISTENCY
    assert calls["n"] == 3  # bounded: 1 initial + 2 retries, then fail closed (no second run)


def test_exhausted_throttle_carries_infra_kind() -> None:
    # A sustained throttle (a raw ClientError) exhausts the budget with kind INFRA — so the caller
    # quarantines / retries the episode, NOT reward 0 (which would be the false-negative).
    def always_throttled() -> GradeOutcome:
        raise FakeClientError("ThrottlingException")

    with pytest.raises(TransientBudgetExhausted) as exc_info:
        reproduce(always_throttled, runs=2, max_transient_retries=1, sleep=lambda _d: None)
    assert exc_info.value.kind is TransientKind.INFRA


def test_runs_below_two_rejected() -> None:
    # K-run reproduce needs >= 2 runs to detect variance.
    with pytest.raises(ValueError):
        reproduce(reward_1, runs=1)


def test_verdict_is_deterministic_for_a_stable_grade() -> None:
    # The harness's own verdict is reproducible: a stable grade ×K yields an equal verdict.
    assert reproduce(reward_1, runs=3) == reproduce(reward_1, runs=3)


def test_reproducible_carries_the_verified_outcome() -> None:
    # The gate returns the VERIFIED GradeOutcome (not just the reward), so the ledger signs the
    # exact diff the K runs certified — no re-grade outside the gate.
    verdict = reproduce(reward_1, runs=3)
    assert isinstance(verdict, Reproducible)
    assert verdict.reward is verdict.outcome.reward is Reward.number_1
    assert canonicalize(verdict.outcome.diff) == canonicalize(reward_1().diff)


def test_surfaced_throttle_is_transient_and_absorbed() -> None:
    # A throttle is NOT a wrong answer (deterministic-verification skill; #141 scope 1). A surfaced
    # throttle ClientError is a transient the K-run RE-ATTEMPTS (never scored 0) — so a
    # throttle-then-stable read settles to a reward instead of a false-negative.
    calls = {"n": 0}

    def throttle_once() -> GradeOutcome:
        calls["n"] += 1
        if calls["n"] == 1:
            raise FakeClientError("ThrottlingException")
        return reward_1()

    verdict = reproduce(throttle_once, runs=3, sleep=lambda _d: None)
    assert isinstance(verdict, Reproducible)
    assert verdict.reward is Reward.number_1


def test_same_reward_different_diff_is_quarantined() -> None:
    # Read non-determinism with a STABLE reward (both reward 0, different values) is still a
    # non-reproducible signed proof, so it is quarantined — locking the diff into the signature.
    outcomes = [reward_0(), reward_0_other()]
    calls = {"n": 0}

    def flaky_same_reward() -> GradeOutcome:
        outcome = outcomes[calls["n"] % len(outcomes)]
        calls["n"] += 1
        return outcome

    verdict = reproduce(flaky_same_reward, runs=4)
    assert isinstance(verdict, Quarantined)
    assert verdict.distinct_outcomes == 2


def test_max_transient_retries_negative_rejected() -> None:
    with pytest.raises(ValueError):
        reproduce(reward_1, runs=2, max_transient_retries=-1)


def test_genuine_after_a_successful_run_fails_closed() -> None:
    # A genuine failure on a later run aborts and fails closed (raises) — never ships the earlier
    # successful run's reward.
    calls = {"n": 0}

    def ok_then_genuine() -> GradeOutcome:
        calls["n"] += 1
        if calls["n"] == 1:
            return reward_1()
        raise RuntimeError("genuine on run 2")

    with pytest.raises(RuntimeError):
        reproduce(ok_then_genuine, runs=3)
