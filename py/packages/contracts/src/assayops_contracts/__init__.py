"""AssayOps contract models (Pydantic v2).

Generated from ``contracts/schemas/*.schema.json`` by ``just codegen`` (datamodel-code-generator);
see docs/ARCHITECTURE.md. The generated modules live under ``assayops_contracts.models``; this
package re-exports the public models. Regenerate with ``just codegen``; never hand-edit the
generated modules under ``models/``.
"""

from assayops_contracts.jcs import canonical_digest, canonicalize
from assayops_contracts.models.diff_ir_schema import (
    Change,
    DiffIR,
    PropertyDiffs,
    PropertyDiffs1,
    Resource,
)
from assayops_contracts.models.reward_record_schema import Reward, RewardRecord
from assayops_contracts.models.task_spec_schema import TaskSpec, Tool
from assayops_contracts.models.trajectory_schema import Step, Trajectory

__all__ = [
    "Change",
    "DiffIR",
    "PropertyDiffs",
    "PropertyDiffs1",
    "Resource",
    "Reward",
    "RewardRecord",
    "Step",
    "TaskSpec",
    "Tool",
    "Trajectory",
    "canonical_digest",
    "canonicalize",
]
