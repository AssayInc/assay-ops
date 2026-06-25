"""E3-1 (#34) -- the reward core's T1 trust boundary (the moat, at the code level).

DECISIONS.md T1/1C + the write-isolated-verifier skill: the reward core grades ONLY the verifier's
read-only B-side deployed-state read and the regenerated golden target -- never the agent's
``terraform plan``/``show``/state or a provider plugin. Executing *or trusting* agent-controlled
data in the grader is the reward-hacking surface the product exists to close. The core fails closed
on any other input provenance. This guard is the code-level expression of T1; it complements (does
not replace) the account-B isolation that is the moat.
"""

from __future__ import annotations

import pytest
from factories import deployed, golden, res

from assayops_diff_ir import NormalizedState, Provenance, UntrustedInputError, grade


def test_grade_accepts_a_deployed_read_against_a_golden_target() -> None:
    # The one sanctioned shape: a B-side deployed read graded against the regenerated golden.
    outcome = grade(deployed(res("bucket")), golden(res("bucket")))
    assert outcome is not None


@pytest.mark.parametrize(
    "tainted_provenance",
    [Provenance.AGENT_PLAN, Provenance.AGENT_STATE, Provenance.GOLDEN_TARGET],
)
def test_grade_rejects_anything_but_a_deployed_read_in_the_deployed_slot(
    tainted_provenance: Provenance,
) -> None:
    # Agent plan/state here is the T1 hole; a golden here is a wiring mistake. Both fail closed.
    tainted = NormalizedState(provenance=tainted_provenance, resources=(res("bucket"),))
    with pytest.raises(UntrustedInputError):
        grade(tainted, golden(res("bucket")))


@pytest.mark.parametrize(
    "tainted_provenance",
    [Provenance.AGENT_PLAN, Provenance.AGENT_STATE, Provenance.DEPLOYED_READ],
)
def test_grade_rejects_anything_but_a_golden_target_in_the_golden_slot(
    tainted_provenance: Provenance,
) -> None:
    tainted = NormalizedState(provenance=tainted_provenance, resources=(res("bucket"),))
    with pytest.raises(UntrustedInputError):
        grade(deployed(res("bucket")), tainted)


def test_normalized_state_rejects_duplicate_addresses() -> None:
    # A duplicate address would silently collapse in the diff's address map -- a wrong grade.
    with pytest.raises(ValueError, match="unique"):
        NormalizedState(
            provenance=Provenance.GOLDEN_TARGET,
            resources=(res("dup"), res("dup")),
        )


def test_untrusted_input_error_is_in_the_value_error_family() -> None:
    # Invalid input -> ValueError (python-error-handling Pattern 4), consistent with the value
    # validators, so a caller can catch any malformed grade input uniformly as ValueError.
    assert issubclass(UntrustedInputError, ValueError)
    tainted = NormalizedState(provenance=Provenance.AGENT_PLAN, resources=(res("x"),))
    with pytest.raises(ValueError):
        grade(tainted, golden(res("x")))
