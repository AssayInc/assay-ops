"""The golden target — the verifier-internal expected normalized resource set (DECISIONS.md 2A/6A).

NOT a contract schema (the cross-language spine is the four codegen'd records); the golden is an
account-B-internal artifact. Only its content address (a SHA-256 over JCS canonical bytes) is
recorded, and it is regenerable from (task, seed), so it never has to cross a process/language
boundary. The field vocabulary (``address``/``type``) matches the diff-IR resource on purpose: a
per-tool adapter (E3/#34) normalizes deployed state into the same shape to diff against it.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator

# JCS/I-JSON exact-integer bound (±(2^53−1)): rfc8785 raises on an integer outside it, so a golden
# carrying one would generate but then fail to content-address. Matches the contract schema's bound.
_MAX_JCS_SAFE_INT = 9007199254740991


def _assert_deterministic_json(value: object) -> None:
    """Reject a property value that would canonicalize non-deterministically or lose information.

    The golden is content-addressed (JCS → SHA-256), so every leaf must be a JSON type with a single
    canonical form. A ``set``/``frozenset`` serializes in ``PYTHONHASHSEED``-dependent order
    (non-deterministic bytes across processes); a non-finite float (NaN/inf) is silently coerced to
    JSON ``null`` by ``model_dump`` (silent loss); an int outside the JCS-safe range is not
    rfc8785-representable. ``bool`` is an ``int`` subclass, admitted before the bound check.
    """
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        if not -_MAX_JCS_SAFE_INT <= value <= _MAX_JCS_SAFE_INT:
            raise ValueError(f"int outside the JCS-safe range (±(2^53−1)): {value}")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite float in golden properties: {value!r}")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"non-string property key: {key!r}")
            _assert_deterministic_json(item)
        return
    if isinstance(value, list):
        for item in value:
            _assert_deterministic_json(item)
        return
    raise ValueError(
        f"non-JSON / non-deterministic value in golden properties: {type(value).__name__}"
    )


class GoldenResource(BaseModel):
    """One expected resource in the golden target, already in normalized form."""

    # Hardened for a content-addressed (hashed) record: immutable, extra-forbid, no silent coercion.
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    address: str = Field(
        min_length=1,
        description="Normalized structural/logical address (never a physical AWS id).",
    )
    type: str = Field(min_length=1, description="Resource type, e.g. AWS::S3::Bucket.")
    properties: dict[str, object] = Field(
        default_factory=dict,
        description="Expected intent-bearing properties — open JSON (`object`, not `Any`).",
    )

    @field_validator("properties", mode="after")
    @classmethod
    def _deterministic_json_properties(cls, properties: dict[str, object]) -> dict[str, object]:
        _assert_deterministic_json(properties)
        return properties


class GoldenTarget(BaseModel):
    """The regenerated golden: the full expected resource set the verifier grades against."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    # A tuple, not a list: the resource set can't be emptied/extended after validation (frozen is
    # shallow), so the content address stays pinned to what the validator approved.
    resources: tuple[GoldenResource, ...] = Field(
        description="Expected resources in canonical order (sorted by address)."
    )

    @field_validator("resources", mode="after")
    @classmethod
    def _canonical_resources(
        cls, resources: tuple[GoldenResource, ...]
    ) -> tuple[GoldenResource, ...]:
        # Canonical-by-construction so the content address is meaningful for ANY golden, not just an
        # engine-built one: non-empty (empty grades a no-op deploy as in-sync — vector #15),
        # unique addresses (else ambiguous), sorted by address (so the digest is order-independent).
        if not resources:
            raise ValueError("a golden target must declare at least one resource")
        addresses = [resource.address for resource in resources]
        duplicates = sorted({a for a in addresses if addresses.count(a) > 1})
        if duplicates:
            raise ValueError(f"duplicate resource addresses: {duplicates}")
        return tuple(sorted(resources, key=lambda resource: resource.address))
