"""The normalized-state IR -- the adapter -> reward-core interface (DECISIONS.md 6A).

A per-tool adapter (read-back deployed state) and the golden-target generator each produce a
``NormalizedState``: a provenance-tagged, tool-agnostic set of resources after *tool-specific*
normalization (AWS-assigned ids/timestamps/suffixes dropped, references resolved structurally,
order-insensitive collections sorted -- see ``NORMALIZATION.md``). The shared reward core diffs two
of these. This IR is internal Python (the cross-package adapter handoff), not a signed/wire
contract -- the wire contracts (``DiffIR``, ``RewardRecord``) live in ``assayops_contracts``.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated

import rfc8785
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


def _canonical_bytes(value: object) -> bytes:
    """RFC 8785 (JCS) canonical bytes of an open JSON value -- the single bridge to the signed form.

    A property value's *validity* (does it canonicalize?) and its *equality* (same bytes?) are both
    defined here -- the form ``assayops_contracts.jcs`` signs the reward record with -- so the grade
    and the signed ``reportDigest`` agree by construction. ``rfc8785.dumps`` is itself the runtime
    validator: it raises ``CanonicalizationError`` (a ``ValueError``) on any non-JSON value.
    """
    # `value` is our open JSON payload, correctly typed `object` (no-`Any` policy). `dumps` is the
    # runtime validator (it raises on non-JSON), so passing `object` past its narrower `_Value`
    # parameter is a boundary cast behind a runtime check -- not a hand-rolled JSON-domain narrow.
    return rfc8785.dumps(value)  # type: ignore[arg-type]


def _canonical_json(value: object) -> object:
    """Validate + canonicalize + independently snapshot a property value via RFC 8785 JCS.

    ``_canonical_bytes`` fails closed on anything non-canonicalizable -- NaN/Infinity, non-string
    object keys, and non-JSON types (set/bytes/dataclass/arbitrary objects, including a
    ``__deepcopy__`` launderer, which it never invokes) -- subsuming the hand-rolled value guards.
    Re-parsing the canonical bytes yields a normalized, plain-JSON, independent snapshot: numbers
    canonicalized (``90.0`` -> ``90``), a scalar subclass reduced to its base value (an overloaded
    ``__eq__`` is never consulted), the report decoupled from the caller's input.
    """
    try:
        canonical_bytes = _canonical_bytes(value)
    except rfc8785.CanonicalizationError as exc:
        raise ValueError(f"property value is not canonicalizable JSON (RFC 8785): {exc}") from exc
    snapshot: object = json.loads(canonical_bytes)
    return snapshot


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
    # Open JSON object -> `object` (the `unknown` equivalent), never `Any`. Stored canonical (JCS);
    # order-insensitive collections within a value are sorted by the adapter.
    properties: dict[str, object] = Field(default_factory=dict)

    @field_validator("properties", mode="after")
    @classmethod
    def _properties_are_a_validated_snapshot(
        cls, properties: dict[str, object]
    ) -> dict[str, object]:
        # One-pass validate + canonicalize + snapshot (NORMALIZATION.md): reject a reserved `$`-key
        # (the $type marker) and a present `None` (absent = omit; exclude_none can't tell None from
        # absent). JCS accepts both, so they stay AssayOps rules; `_canonical_json` does the rest.
        snapshot: dict[str, object] = {}
        for key, value in properties.items():
            if key.startswith("$"):
                raise ValueError(f"property key {key!r} is reserved: keys must not start with '$'")
            if value is None:
                raise ValueError(
                    f"property {key!r} is None: omit an absent property, never store None"
                )
            snapshot[key] = _canonical_json(value)
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
