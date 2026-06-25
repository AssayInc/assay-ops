"""AssayOps normalized diff IR + shared reward core (DECISIONS.md 6A).

The write-isolated reward core: it consumes two normalized states -- the verifier's read-only read
of B-side deployed state and the independently regenerated golden target -- and grades
``reward in {0, 1}`` = zero normalized diff. Per-tool adapters (separate packages) do the
tool-specific normalization of one side; the determinism-critical diff lives here once,
tool-agnostically. See ``NORMALIZATION.md``.
"""

from assayops_diff_ir.normalized_state import (
    NormalizedResource,
    NormalizedState,
    Provenance,
)
from assayops_diff_ir.reward_core import GradeOutcome, UntrustedInputError, grade

__all__ = [
    "GradeOutcome",
    "NormalizedResource",
    "NormalizedState",
    "Provenance",
    "UntrustedInputError",
    "grade",
]
