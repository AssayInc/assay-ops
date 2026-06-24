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


def _validate_and_copy_json(value: object) -> object:
    """Validate exact-type finite JSON (string keys) and return an INDEPENDENT copy, in one pass.

    NO ``copy.deepcopy`` / ``model_dump`` on untrusted values -- both invoke user dunders
    (``__deepcopy__`` / serializers) that could launder a non-JSON object into JSON before the type
    gate runs. This checks the EXACT built-in type first, then copies node-by-node from verified
    built-ins only, so an injected object (a scalar subclass with an overloaded ``__eq__``, a
    BaseModel/dataclass, a ``__deepcopy__`` launderer) is rejected at its node and never copied
    through. Closes the value-type-collapse (``True``/``1``, ``1``/``1.0``), non-string-key
    (``{1: ...}``/``{True: ...}`` collide), NaN, and laundering false-reward-1 paths.
    """
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value  # immutable JSON scalars are their own copy (identity `is`, never `==`)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("property values must be finite numbers (no NaN/Infinity)")
        return value
    if type(value) is dict:
        snapshot: dict[str, object] = {}
        for key, nested in value.items():
            if type(key) is not str:
                raise ValueError(f"object keys must be strings, got {type(key).__name__}")
            snapshot[key] = _validate_and_copy_json(nested)
        return snapshot
    if type(value) is list:
        return [_validate_and_copy_json(nested) for nested in value]
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

    @field_validator("properties", mode="after")
    @classmethod
    def _properties_are_a_validated_snapshot(
        cls, properties: dict[str, object]
    ) -> dict[str, object]:
        # Validate + snapshot in one pass (NORMALIZATION.md): reject reserved `$`-keys (the $type
        # marker) and a present `None` (absent = omit the key; exclude_none can't tell None from
        # absent); `_validate_and_copy_json` enforces the exact JSON domain and returns a copy.
        snapshot: dict[str, object] = {}
        for key, value in properties.items():
            if key.startswith("$"):
                raise ValueError(f"property key {key!r} is reserved: keys must not start with '$'")
            if value is None:
                raise ValueError(
                    f"property {key!r} is None: omit an absent property, never store None"
                )
            snapshot[key] = _validate_and_copy_json(value)
        return snapshot


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
