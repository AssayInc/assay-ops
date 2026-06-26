"""K-run reproduce + quarantine — the 7A determinism gate (DECISIONS.md 7A / T8, epic E6).

A reward must reproduce: grade K times → identical reward. ``reproduce`` drives an injected grade
callable K times, absorbs a **transiently-unreadable** read (throttle / 5xx / eventual consistency)
within a bounded, backed-off retry, and compares the settled outcomes. If they all agree it returns
the reward (``Reproducible``); if they disagree the task is flaky / non-deterministic and is
**quarantined** (``Quarantined``) — pulled from the scored set, never silently rewarded (vector #15;
a flaky reward poisons training). It is generic over the grade callable, so it neither imports the
verifier nor runs agent code; the deterministic comparison is by the diff report's signed canonical
bytes.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from assayops_contracts import Reward
from assayops_contracts.jcs import canonicalize
from assayops_diff_ir import GradeOutcome

from assayops_replay.classifier import TransientKind, transient_kind

# A settled grade attempt: returns reward ∈ {0,1} + diff, or raises a transient the harness absorbs
# (a TransientGradeError / throttle / read-after-create ClientError). Genuine failures fail closed.
GradeFn = Callable[[], GradeOutcome]

# K — the determinism gate runs the grade K times. NOT a floor-locked number (DECISIONS.md leaves K
# a parameter); 3 is a small default that detects variance cheaply (the per-read budget, spike #60,
# is sub-second). Tune per corpus; raising K trades cost for tighter flake detection.
DEFAULT_RUNS = 3
# The per-run transient retry budget — small and rarely-firing (DECISIONS.md §1: reads are
# sub-second), then fail closed. This is the determinism-layer K-run that #141 routes a surfaced
# transient into (#141 scope 1); the per-read throttle / 5xx RETRY is boto3 adaptive's, and
# read-after-create polling is #141's read.
DEFAULT_MAX_TRANSIENT_RETRIES = 2
# Deterministic capped exponential backoff (seconds). NO jitter: jitter exists to de-correlate many
# concurrent clients (python-resilience), but the verifier is a single grader and this is a
# determinism-critical package — a deterministic delay keeps the harness reproducible. The read
# path's boto3 adaptive mode owns SDK-level (jittered) throttle backoff.
_BACKOFF_BASE_SECONDS = 0.05
_BACKOFF_CAP_SECONDS = 2.0


class TransientBudgetExhausted(Exception):
    """A transient that never settled within the per-run retry budget — fail closed.

    The harness never fabricates a reward and never retries unboundedly. The caller maps it by
    ``kind``: ``EVENTUAL_CONSISTENCY`` (a read-after-create resource absent after the budget) is
    genuine unreadability ⇒ ``reward=0`` (DECISIONS.md §1, vector #15); ``INFRA`` (a throttle the
    read could not complete) is NOT ``reward=0`` — that would be a false-negative — so the caller
    quarantines / retries the episode (#141 scope 1). The underlying exception is chained as
    ``__cause__``.
    """

    def __init__(self, kind: TransientKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class Reproducible:
    """The K runs agreed on one settled outcome — safe to ship that reward.

    Carries the **verified** ``GradeOutcome`` (not just the reward): the reward record's signed
    ``reportDigest`` is taken over this exact diff, so the signed proof is the one the K-run gate
    certified — the consumer never has to re-grade outside the gate (which could itself diverge).
    The convenience ``reward`` property is what most consumers ship.
    """

    outcome: GradeOutcome
    runs: int

    @property
    def reward(self) -> Reward:
        return self.outcome.reward


@dataclass(frozen=True)
class Quarantined:
    """The K runs did NOT agree — the task is flaky / non-deterministic and is pulled from the
    scored set. Deliberately carries NO ``reward`` attribute: a flaky task can never be silently
    rewarded (DECISIONS.md 7A, vector #15)."""

    reason: str
    runs: int
    distinct_outcomes: int


ReproduceVerdict = Reproducible | Quarantined


def reproduce(
    grade_fn: GradeFn,
    *,
    runs: int = DEFAULT_RUNS,
    max_transient_retries: int = DEFAULT_MAX_TRANSIENT_RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> ReproduceVerdict:
    """Grade ``grade_fn`` ``runs`` times; return ``Reproducible`` iff every run settles to the same
    reward + diff report, else ``Quarantined`` (never a reward).

    Each run absorbs **transient** failures (``classify`` ⇒ TRANSIENT) with a bounded, backed-off
    retry; a **genuine** failure propagates (fail closed), and a transient that never settles raises
    ``TransientBudgetExhausted`` (fail closed) — never a silent or fabricated reward (vector #15).
    """
    if runs < 2:
        raise ValueError(f"K-run reproduce needs runs >= 2 to detect variance, got {runs}")
    if max_transient_retries < 0:
        raise ValueError(f"max_transient_retries must be >= 0, got {max_transient_retries}")

    outcomes = [_settle_once(grade_fn, max_transient_retries, sleep) for _ in range(runs)]
    signatures = {_signature(outcome) for outcome in outcomes}
    if len(signatures) == 1:
        # All K signatures are identical, so any settled outcome is THE verified one; carry
        # outcomes[0] (its diff is the canonical form the signature was built from) to sign.
        return Reproducible(outcome=outcomes[0], runs=runs)
    return Quarantined(
        reason=f"non-deterministic reward across {runs} runs ({len(signatures)} distinct outcomes)",
        runs=runs,
        distinct_outcomes=len(signatures),
    )


def _signature(outcome: GradeOutcome) -> tuple[Reward, bytes]:
    """A run's settled outcome reduced to its identity: the reward and the diff report's canonical
    (RFC 8785 JCS) bytes — the form the reward record is signed with, so two runs are "the same"
    here iff the signed record would be too. (The reward is a pure function of the diff, so pairing
    them is a cheap consistency check as much as a comparison.)

    Comparing the full diff, not just the reward, is intentional: a same-reward run whose mismatch
    *values* vary (e.g., an un-normalized field leaking into the read) is a non-reproducible signed
    proof, so it is quarantined, not passed as a stable reward."""
    return (outcome.reward, canonicalize(outcome.diff))


def _settle_once(
    grade_fn: GradeFn, max_transient_retries: int, sleep: Callable[[float], None]
) -> GradeOutcome:
    """One settled grade: absorb transient failures with a bounded backed-off retry; fail closed on
    a genuine failure or an exhausted transient budget. Returns only a settled ``GradeOutcome`` — a
    transient never returns; it retries, then raises (fail closed)."""
    for attempt in range(max_transient_retries + 1):
        try:
            return grade_fn()
        except Exception as exc:
            kind = transient_kind(exc)
            if kind is None:
                raise  # genuine ⇒ fail closed, never retried into a silent reward
            if attempt >= max_transient_retries:
                raise TransientBudgetExhausted(
                    kind,
                    f"transient {kind.value} did not settle in {max_transient_retries} retries",
                ) from exc
            sleep(_backoff_delay(attempt))
    raise AssertionError(
        "unreachable: the loop returns or raises every iteration"
    )  # pragma: no cover


def _backoff_delay(attempt: int) -> float:
    # 2.0 (not 2) so the exponentiation is float**int -> float; typeshed types int**int as Any
    # because a negative exponent would yield a float.
    return min(_BACKOFF_CAP_SECONDS, _BACKOFF_BASE_SECONDS * (2.0**attempt))
