"""AssayOps account-B verifier core (DECISIONS.md §1/§8, T1).

E2-5 (#75): the golden-target generator (``GoldenRegistry.generate(task, seed)`` → a
content-addressed ``GoldenTarget``; the per-task builders are the private corpus #76, this package
is the engine). E2-2 (#31): the grade entry ``grade_deployment`` — regenerate the golden, bridge it
into the reward core's IR, and grade a B-side deployed-state read against it → ``reward ∈ {0, 1}``.

E2-1 (#30): the deployed-state read path -- ``DeployedStateReader`` and ``verify_deployment`` --
lives in ``assayops_verifier.read``; it depends on boto3 + the Terraform adapter, kept out of this
top-level import so golden/grade stay cloud-free. The reward-record/ledger handoff is E2-3/#32.
"""

from __future__ import annotations

from assayops_verifier.golden import (
    GoldenBuilder,
    GoldenContext,
    GoldenError,
    GoldenRegistry,
    UnknownTaskError,
    golden_digest,
)
from assayops_verifier.grading import (
    GoldenNotGradableError,
    golden_as_normalized_state,
    grade_deployment,
)
from assayops_verifier.models import GoldenResource, GoldenTarget

__all__ = [
    "GoldenBuilder",
    "GoldenContext",
    "GoldenError",
    "GoldenNotGradableError",
    "GoldenRegistry",
    "GoldenResource",
    "GoldenTarget",
    "UnknownTaskError",
    "golden_as_normalized_state",
    "golden_digest",
    "grade_deployment",
]
