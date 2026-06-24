"""The normalized-state IR -- the adapter -> reward-core interface (DECISIONS.md 6A).

A per-tool adapter (read-back deployed state) and the golden-target generator each produce a
``NormalizedState``: a provenance-tagged, tool-agnostic set of resources after *tool-specific*
normalization (AWS-assigned ids/timestamps/suffixes dropped, references resolved structurally,
order-insensitive collections sorted -- see ``NORMALIZATION.md``). The shared reward core diffs two
of these. This IR is internal Python (the cross-package adapter handoff), not a signed/wire
contract -- the wire contracts (``DiffIR``, ``RewardRecord``) live in ``assayops_contracts``.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


def _validate_json_value(value: object) -> None:
    """Fail closed unless ``value`` is a finite JSON value with string object keys (recursive).

    Rejects what would forge a reward or break the signed digest: non-string dict keys (``{1: ...}``
    and ``{True: ...}`` collide under Python equality -- a false reward 1), non-finite numbers
    (NaN/Infinity break determinism + RFC 8785 JCS), and non-JSON types (tuple/set/bytes/objects).
    """
    if value is None or isinstance(value, (bool, int, str)):
        return  # JSON scalars (bool is an int subclass; nested None is a legal JSON value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("property values must be finite numbers (no NaN/Infinity)")
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError(f"object keys must be strings, got {type(key).__name__}")
            _validate_json_value(nested)
        return
    if isinstance(value, list):
        for nested in value:
            _validate_json_value(nested)
        return
    raise ValueError(f"property values must be JSON types, got {type(value).__name__}")


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
    # property values type-strictly; order-insensitive collections are sorted by the adapter.
    properties: dict[str, object] = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def _properties_must_be_representable(cls, properties: dict[str, object]) -> dict[str, object]:
        # Fail closed on values that would forge a reward or break the signed digest (see the review
        # hardening in NORMALIZATION.md): reserved `$`-keys (the $type marker), an ambiguous present
        # ambiguous `None` (absent = omit the key; exclude_none can't tell None from absent), and
        # non-finite numbers (NaN/Infinity break determinism and RFC 8785 JCS).
        for key, value in properties.items():
            if key.startswith("$"):
                raise ValueError(f"property key {key!r} is reserved: keys must not start with '$'")
            if value is None:
                raise ValueError(
                    f"property {key!r} is None: omit an absent property, never store None"
                )
            _validate_json_value(value)
        return properties


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
