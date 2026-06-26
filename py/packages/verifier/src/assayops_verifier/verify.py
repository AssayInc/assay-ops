"""E2-6 (#141) scope 1: the closed-world verify entry -- read -> grade through the 7A K-run.

``verify`` is the sound account-B grade entry (DECISIONS.md section 1, T1): it enumerates deployed
state closed-world (``read_closed_world``), normalizes it (#35), regenerates the golden and grades
it (#31), and drives that whole read->grade K times through the ``reproduce`` determinism gate (#45)
so a flaky reward is never shipped. The outcome maps to a ``VerifyVerdict`` the reward ledger (#32)
consumes -- three reward-meaningful shapes:

- ``Reproducible`` -- a settled, K-reproduced grade (reward 1 clean / reward 0 drift / reward 0 on
  an enumerated extra). Carries the verified ``GradeOutcome`` the ledger signs.
- ``FailedClosed`` -- reward 0, fail closed: a listed-but-unreadable resource the read could not
  settle (a persistent EVENTUAL_CONSISTENCY race). We cannot verify the set, so never a false 1 --
  but the resource is NOT dropped (a drop could hide an extra, vector #15).
- ``Quarantined`` -- pulled from scoring, no reward: a non-reproducing (flaky) grade, or a
  persistent INFRA transient (throttle/5xx the read could not complete -- NOT reward 0, a
  false-negative).

A GENUINE failure -- a genuinely-unreadable resource (``UnreadableResourceError``), an unsupported
type (``UnsupportedResourceTypeError``), a closed-world gap (``ClosedWorldError``), a non-gradable
golden (``GoldenError``) -- PROPAGATES (fail closed). An ``AccessDenied`` rides through as an
``UnreadableResourceError``: an isolation alarm surfaced loudly, never silently mapped to 0.

The per-property coverage gate (``read_scope.assert_golden_readable``, #141 scope 3) is
authoring-time -- run when admitting a task, not per-episode here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from assayops_adapter_terraform import BridgeRegistry, normalize
from assayops_contracts import Reward, TaskSpec
from assayops_diff_ir import GradeOutcome
from assayops_replay import (
    DEFAULT_RUNS,
    Quarantined,
    Reproducible,
    TransientBudgetExhausted,
    TransientKind,
    reproduce,
)

from assayops_verifier.golden import GoldenRegistry
from assayops_verifier.grading import grade_deployment
from assayops_verifier.read import DeployedStateReader, read_closed_world
from assayops_verifier.read_scope import ReadScope


@dataclass(frozen=True)
class FailedClosed:
    """Reward 0, fail closed: the deployed read could not settle into a complete, verifiable set.

    A listed-but-unreadable resource that never settled within the transient budget (a persistent
    EVENTUAL_CONSISTENCY race). We cannot confirm the deployed set, so the grade is forced to 0 --
    never a false 1 (vector #15) -- but the resource is NOT dropped (a drop could hide an extra). A
    reward-0 outcome distinct from a graded 0: it carries no diff, only the fail-closed reason.
    """

    reason: str

    @property
    def reward(self) -> Reward:
        return Reward.number_0


# The verify verdict -- three reward-meaningful shapes the reward ledger (#32) consumes.
VerifyVerdict = Reproducible | Quarantined | FailedClosed


def verify(
    readers: Mapping[str, DeployedStateReader],
    registry: GoldenRegistry,
    task: TaskSpec,
    seed: str,
    scope: ReadScope,
    *,
    bridge_registry: BridgeRegistry | None = None,
    runs: int = DEFAULT_RUNS,
) -> VerifyVerdict:
    """Grade a deployment closed-world through the 7A K-run -> a ``VerifyVerdict`` (#141 scope 1).

    ``readers`` is the per-Region account-B Cloud Control reader map; ``scope`` the in-scope
    read-coverage matrix; ``runs`` the determinism K (an unlocked parameter, default 3 -- tune per
    corpus). Each of the K runs reads closed-world, normalizes, and grades the **regenerated**
    golden (never a caller-supplied one, 2A/T1); ``reproduce`` absorbs a surfaced transient within a
    bounded retry and quarantines a non-reproducing reward. Returns a verdict; a genuine failure
    propagates (fail closed). Never returns reward 1 for a deployment it cannot fully verify (#15).
    """

    def grade_fn() -> GradeOutcome:
        reads = read_closed_world(readers, scope)
        deployed = normalize(reads, bridge_registry)
        return grade_deployment(registry, task, seed, deployed)

    try:
        return reproduce(grade_fn, runs=runs)
    except TransientBudgetExhausted as exc:
        if exc.kind is TransientKind.EVENTUAL_CONSISTENCY:
            # A listed-but-unreadable resource we could not settle: reward 0, fail closed -- never a
            # false 1, and never dropped (a drop could hide an extra, vector #15).
            return FailedClosed(reason=str(exc))
        # INFRA (a throttle/5xx the read could not complete) is NOT a wrong answer -- quarantine the
        # episode (pulled from scoring), never score it 0 (the false-negative).
        return Quarantined(reason=str(exc), runs=runs, distinct_outcomes=0)
