"""The verifier's grade entry: regenerate the golden, bridge it, grade deployed state (2A/6A/T1).

E2-2 (#31) — the seam between the golden-target generator (E2-5/#75, ``generate(task, seed)``) and
the shared, write-isolated reward core (E3-1/#34, ``grade(deployed, golden)``). The account-B
verifier **regenerates** the golden from (task, seed) — never accepting one from the caller (2A, the
"independently regenerated golden") — bridges it into the reward core's ``NormalizedState`` IR, and
grades a B-side deployed-state read against it → ``reward ∈ {0, 1}`` = zero normalized diff. It runs
no agent code; the deployed-state read is produced upstream by the read path (#30/#141) and passed
in here as a ``DEPLOYED_READ`` ``NormalizedState``.
"""

from __future__ import annotations

from assayops_contracts import TaskSpec
from assayops_diff_ir import (
    GradeOutcome,
    NormalizedResource,
    NormalizedState,
    Provenance,
    grade,
)

from assayops_verifier.golden import GoldenRegistry
from assayops_verifier.models import GoldenTarget


class GoldenNotGradableError(ValueError):
    """A regenerated golden that cannot be normalized into the reward core's IR — fail closed.

    The golden generator (#75) accepts values the grading core (#34) forbids — a ``None`` property
    value, a ``$``-prefixed key — because the grading core is the stricter trust gate. Rather than
    silently grade (or grade a coerced value), the bridge fails closed here: a ``ValueError``,
    consistent with the core's ``UntrustedInputError`` and the value validators, so a caller catches
    malformed grade input uniformly. Never a silent reward (DECISIONS.md §8, vector #15).
    """


def golden_as_normalized_state(target: GoldenTarget) -> NormalizedState:
    """Bridge a regenerated golden target into a ``GOLDEN_TARGET``-provenance ``NormalizedState``.

    Reconstructs each ``GoldenResource`` through ``NormalizedResource``, which re-validates and
    canonicalizes the open ``properties`` under the reward core's stricter JSON-domain rules —
    rejecting a subclass / non-JSON / ``$``-key / ``None`` value the generator's looser gate let
    through. So a golden the core cannot represent fails closed (``GoldenNotGradableError``) instead
    of being silently graded, and the state is tagged ``GOLDEN_TARGET`` so the core's golden-slot
    guard stays meaningful.
    """
    try:
        resources = tuple(
            NormalizedResource(address=r.address, type=r.type, properties=r.properties)
            for r in target.resources
        )
        return NormalizedState(provenance=Provenance.GOLDEN_TARGET, resources=resources)
    except ValueError as exc:
        # A property the grading core rejects (looser-generator divergence) or a post-construction
        # mutation surfaces as a pydantic ValidationError (a ValueError subclass) — fail closed,
        # never a silent reward. A non-ValueError is a verifier bug, so it propagates loudly.
        raise GoldenNotGradableError(
            f"regenerated golden cannot be normalized for grading: {exc}"
        ) from exc


def grade_deployment(
    registry: GoldenRegistry, task: TaskSpec, seed: str, deployed: NormalizedState
) -> GradeOutcome:
    """Grade a B-side deployed-state read against the regenerated golden → reward + diff report.

    The golden is **regenerated** here from (task, seed) via ``registry`` — never supplied by the
    caller (2A/T1) — then bridged and handed to the shared reward core. ``grade`` enforces that
    ``deployed`` is a ``DEPLOYED_READ`` state (the agent's plan/state is rejected, T1). Fails closed
    on an unregistered task / bad builder (``GoldenError``), a non-normalizable golden
    (``GoldenNotGradableError``), or an untrusted input slot (``UntrustedInputError``) — never a
    silent reward. ``seed`` is explicit (canonical = ``task.seed``; a fresh seed is #75's
    anti-memorization variant) — a seed not matching the episode regrades to 0, never a forged 1.
    """
    golden = golden_as_normalized_state(registry.generate(task, seed))
    return grade(deployed, golden)
