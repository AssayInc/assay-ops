"""E2-6 (#141) scope 1: the closed-world verify entry -- read -> grade through the 7A K-run.

``verify`` is the sound account-B grade entry (DECISIONS.md section 1, T1): it enumerates deployed
state closed-world (``read_closed_world``), normalizes it (#35), regenerates the golden and grades
it (#31), and drives that whole read->grade K times through the ``reproduce`` determinism gate (#45)
so a flaky reward is never shipped. The outcome maps to a ``VerifyVerdict`` the reward ledger (#32)
consumes -- three reward-meaningful shapes:

- ``Reproducible`` -- a settled, K-reproduced grade (reward 1 clean / reward 0 drift / reward 0 on
  an enumerated extra). Carries the verified ``GradeOutcome`` the ledger signs.
- ``FailedClosed`` (reward 0, fail closed) -- the floor's "genuine unreadability => reward=0"
  (DECISIONS.md section 1): a genuine / un-gradable INSTANCE of agent-controlled deployed state the
  verifier cannot vouch for -- a persistent EVENTUAL_CONSISTENCY race, a settled AccessDenied /
  validation / unparseable read, or a malformed / missing / duplicate ``assayops:address`` tag. We
  cannot confirm the deploy, so never a false 1; and a wrong deploy must not DODGE a deserved 0 by
  denying the read-role or dropping its tag, so it is scored 0 (NOT raised into a pulled episode --
  the cause rides in the verdict ``reason``, surfaced out-of-band, never masked; the resource is
  never dropped -- a drop could hide an extra, vector #15).
- ``Quarantined`` -- pulled from scoring, no reward: a non-reproducing (flaky) grade, or a
  persistent INFRA transient (throttle/5xx the read could not complete -- NOT reward 0, a
  false-negative).

A CORPUS / CONFIG / VERIFIER error PROPAGATES (raise), NOT scored 0 -- it is the verifier's bug, not
the agent's deploy, and scoring it 0 would hide a corpus gap as a systematic false-negative: an
unsupported type (``UnsupportedResourceTypeError`` -- the authoring gate should have quarantined
it), a closed-world gap (``ClosedWorldError``), a non-gradable golden (``GoldenError`` /
``GoldenNotGradableError``). PRECONDITION for the FailedClosed mapping above: the #60/#52 readiness
gate (isolated from the grade) must exercise the PER-TYPE read perms, so a grade-time AccessDenied
is provably agent-induced, not a verifier-side per-type read-role hole.

The per-property coverage gate (``read_scope.assert_golden_readable``, #141 scope 3) is
authoring-time -- run when admitting a task, not per-episode here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from assayops_adapter_terraform import (
    AddressBridgeError,
    BridgeRegistry,
    DuplicateAddressError,
    UnreadableResourceError,
    normalize,
)
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
    except (UnreadableResourceError, AddressBridgeError, DuplicateAddressError) as exc:
        # A genuine / un-gradable INSTANCE of agent-controlled deployed state: an AccessDenied
        # / validation / unparseable read, or a malformed / missing / duplicate address tag. The
        # floor (DECISIONS.md s1) is reward=0 ("instance genuinely unreadable, type supported =>
        # reward=0"); a wrong deploy must NOT DODGE a 0 by denying the read-role or dropping
        # its tag -- the agent controls both (a same-account resource-policy explicit-Deny wins ->
        # AccessDenied; the tag is in the agent's IaC). So -> FailedClosed(0) with the cause in the
        # reason (surfaced out-of-band, NOT masked). The verifier-side "read role broken" case is
        # caught UPSTREAM by the #60/#52 readiness gate (isolated from the grade -- see the module
        # docstring PRECONDITION). Corpus/config errors do NOT land here; they propagate. [2-review
        # decision -- Opus 4.8 max + Codex gpt-5.5 xhigh.]
        return FailedClosed(reason=str(exc))
