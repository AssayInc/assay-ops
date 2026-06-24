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


def _require_utf8(text: str) -> None:
    # An unpaired surrogate is a valid str but not UTF-8-encodable: model_dump coerces a surrogate
    # KEY to the replacement char (distinct keys → one digest, a collision); rfc8785 raises on a
    # surrogate VALUE (a raw leak). Reject both.
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"non-UTF-8 (surrogate?) string in golden properties: {text!r}") from exc


def _assert_deterministic_json(value: object) -> None:
    """Reject a property value that would canonicalize non-deterministically or lose information.

    The golden is content-addressed (JCS → SHA-256), so every leaf must be a JSON type with a single
    canonical form. Rejected: ``set``/``frozenset`` (``PYTHONHASHSEED``-ordered); a non-finite float
    (NaN/inf — ``model_dump`` silently nulls it); an int outside the JCS-safe range; a non-UTF-8
    (surrogate) string key/value (digest collision / raw leak). ``bool`` is admitted before the int
    bound; JSON-type subclasses (e.g. ``IntEnum``) coerce to their base value; other non-JSON types
    (bytes, tuple, ``datetime``, ``Decimal``, …) are rejected below.
    """
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        _require_utf8(value)
        return
    if isinstance(value, int):
        if not -_MAX_JCS_SAFE_INT <= value <= _MAX_JCS_SAFE_INT:
            raise ValueError(f"int outside the JCS-safe range (±(2^53−1)): {value}")
        return
    if isinstance(value, float):
        # No magnitude bound (unlike int): rfc8785 serializes any finite float deterministically, so
        # there's no generate-succeeds-but-digest-fails gap — IEEE precision is the builder's type
        # choice (use int for an exact large integer, which is bounded above).
        if not math.isfinite(value):
            raise ValueError(f"non-finite float in golden properties: {value!r}")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"non-string property key: {key!r}")
            _require_utf8(key)
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
        for resource in resources:
            # Re-check properties: a builder may have mutated a resource's open dict after the
            # GoldenResource validator ran (frozen is shallow), and Pydantic doesn't re-validate
            # nested instances by default — without this, generate() could return an invalid golden.
            _assert_deterministic_json(resource.properties)
        return tuple(sorted(resources, key=lambda resource: resource.address))

    def assert_canonical(self) -> None:
        """Re-check the LIVE golden before content-addressing or grading.

        ``frozen`` is shallow, so a resource's open ``properties`` dict can be mutated after
        construction. Re-checking the live values (not a ``model_dump`` round-trip, which would
        silently coerce a ``BaseModel``/``IntEnum`` leaf to its JSON form) keeps the content address
        pinned to a valid golden. Raises ``ValueError`` on any non-deterministic / non-JSON value;
        the caller wraps it as ``GoldenError``.
        """
        for resource in self.resources:
            _assert_deterministic_json(resource.properties)
