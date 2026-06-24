"""The golden target — the verifier-internal expected normalized resource set (DECISIONS.md 2A/6A).

NOT a contract schema (the cross-language spine is the four codegen'd records); the golden is an
account-B-internal artifact. Only its content address (a SHA-256 over JCS canonical bytes) is
recorded, and it is regenerable from (task, seed), so it never has to cross a process/language
boundary. The field vocabulary (``address``/``type``) matches the diff-IR resource on purpose: a
per-tool adapter (E3/#34) normalizes deployed state into the same shape to diff against it.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


class GoldenTarget(BaseModel):
    """The regenerated golden: the full expected resource set the verifier grades against."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    resources: list[GoldenResource] = Field(
        description="Expected resources in canonical order (sorted by address)."
    )
