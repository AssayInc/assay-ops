"""AssayOps account-B verifier core (DECISIONS.md §1/§8, T1).

E2-5 (#75): the golden-target generator (``GoldenRegistry.generate(task, seed)`` → a
content-addressed ``GoldenTarget``; the per-task builders are the private corpus #76, this package
is the engine). E2-2 (#31): the grade entry ``grade_deployment`` — regenerate the golden, bridge it
into the reward core's IR, and grade a B-side deployed-state read against it → ``reward ∈ {0, 1}``.

E2-1 (#30) + E2-6 (#141): the deployed-state read path + closed-world read-coverage enforcement. The
boto3-dependent pieces -- ``DeployedStateReader`` / ``read_closed_world`` / ``ClosedWorldError`` (in
``assayops_verifier.read``) and the ``verify`` entry + ``VerifyVerdict`` (in
``assayops_verifier.verify``) -- are kept OUT of this top-level import so golden/grade stay
cloud-free (the determinism subprocess needs no boto3). The PURE read-coverage matrix + gate (in
``assayops_verifier.read_scope``) is cloud-free, so it is re-exported here. The reward-record/ledger
handoff is E2-3/#32.
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
from assayops_verifier.read_scope import (
    Listability,
    ReadScope,
    RegionScope,
    TypeCoverage,
    UnknownReadCoverageError,
    UnreadableGoldenPropertyError,
    assert_golden_readable,
)

__all__ = [
    "GoldenBuilder",
    "GoldenContext",
    "GoldenError",
    "GoldenNotGradableError",
    "GoldenRegistry",
    "GoldenResource",
    "GoldenTarget",
    "Listability",
    "ReadScope",
    "RegionScope",
    "TypeCoverage",
    "UnknownReadCoverageError",
    "UnknownTaskError",
    "UnreadableGoldenPropertyError",
    "assert_golden_readable",
    "golden_as_normalized_state",
    "golden_digest",
    "grade_deployment",
]
