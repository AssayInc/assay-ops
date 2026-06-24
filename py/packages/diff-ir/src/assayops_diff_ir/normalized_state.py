"""The normalized-state IR -- the adapter -> reward-core interface (DECISIONS.md 6A).

A per-tool adapter (read-back deployed state) and the golden-target generator each produce a
``NormalizedState``: a provenance-tagged, tool-agnostic set of resources after *tool-specific*
normalization (AWS-assigned ids/timestamps/suffixes dropped, references resolved structurally,
order-insensitive collections sorted -- see ``NORMALIZATION.md``). The shared reward core diffs two
of these. This IR is internal Python (the cross-package adapter handoff), not a signed/wire
contract -- the wire contracts (``DiffIR``, ``RewardRecord``) live in ``assayops_contracts``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Provenance(StrEnum):
    """Where a normalized state came from -- the reward core grades ONLY the first two.

    ``AGENT_PLAN`` / ``AGENT_STATE`` name the forbidden T1 sources (the agent's ``terraform
    plan``/``show``/state file) explicitly, so the reward core can fail closed on them and the
    boundary is testable -- they must never reach the grade (DECISIONS.md T1).
    """

    DEPLOYED_READ = "deployed_read"
    GOLDEN_TARGET = "golden_target"
    AGENT_PLAN = "agent_plan"
    AGENT_STATE = "agent_state"


class NormalizedResource(BaseModel):
    """One normalized resource: a structural address, its type, and intent-bearing properties."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    address: Annotated[
        str,
        Field(
            min_length=1,
            description="Normalized structural/logical address (never a physical AWS id).",
        ),
    ]
    type: Annotated[str, Field(min_length=1, description="Resource type, e.g. AWS::S3::Bucket.")]
    # Open JSON object -> `object` (the `unknown` equivalent), never `Any`. The core compares
    # property values structurally; order-insensitive collections are sorted by the adapter.
    properties: dict[str, object] = Field(default_factory=dict)


class NormalizedState(BaseModel):
    """A provenance-tagged set of normalized resources -- one side of the diff."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provenance: Provenance
    resources: tuple[NormalizedResource, ...] = ()

    @model_validator(mode="after")
    def _addresses_must_be_unique(self) -> NormalizedState:
        addresses = [r.address for r in self.resources]
        if len(addresses) != len(set(addresses)):
            raise ValueError("resource addresses must be unique within a NormalizedState")
        return self
