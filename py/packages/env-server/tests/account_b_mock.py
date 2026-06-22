"""MOCK account-B — the write-isolated verifier + reward ledger (test harness, NOT shipped).

Stands in for the real account-B services so the spike can prove the reward boundary end-to-end
without real KMS / S3 Object Lock / cross-account infra. It alone holds the signing key and the
golden target; the A-side env-server holds neither — that asymmetry *is* the boundary.

Faithful to the locked design but minimal:
- the canonical reward record is ``@assayops/contracts`` ``RewardRecord`` (binary ``reward`` in
  ``{0, 1}``, the ``trajectory_id`` join key, ``attempt``, ``reportDigest``, ``graderVersion``,
  ``gradedAt``, ``nonce``); this mirrors those fields and adds the signature;
- signing is asymmetric **ECDSA P-256** over SHA-256 (the KMS ``Sign`` analog, DECISIONS.md I3);
  the agent holds no private key, so it cannot forge a verifiable record;
- the store is **WORM**: append-only, keyed by ``(trajectory_id, attempt)``; a re-grade is a new
  attempt, never an overwrite (DECISIONS.md 4B / §8).

Stand-ins (real services do better, out of spike scope): canonicalization here is sorted-key
compact JSON, not RFC 8785 JCS (#28 owns JCS); the golden grade is a toy predicate, not a
regenerated target.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import BaseModel, ConfigDict

# The B-side golden target — independently held; the A-side env never sees it (DECISIONS.md 2A).
_GOLDEN_RESOURCE = "AWS::S3::Bucket"


class GradedRewardRecord(BaseModel):
    """Mirror of ``@assayops/contracts`` ``RewardRecord``, plus the signature."""

    model_config = ConfigDict(extra="forbid")

    trajectory_id: str
    attempt: int
    reward: Literal[0, 1]
    reportDigest: str  # camelCase mirrors the contract schema
    graderVersion: str  # camelCase mirrors the contract schema
    gradedAt: str  # camelCase mirrors the contract schema
    nonce: str
    signature: str  # hex ECDSA P-256 over the canonical (unsigned) record


def _canonical_unsigned(record: dict[str, Any]) -> bytes:
    """Deterministic bytes the signature covers (everything but the signature itself)."""
    unsigned = {key: value for key, value in record.items() if key != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


class MockAccountBVerifierLedger:
    def __init__(self) -> None:
        # The agent NEVER holds this key — it lives only account-B.
        self._key = ec.generate_private_key(ec.SECP256R1())
        self._worm: dict[tuple[str, int], GradedRewardRecord] = {}

    @property
    def public_key(self) -> ec.EllipticCurvePublicKey:
        return self._key.public_key()

    def _grade(self, deployed_state: dict[str, Any]) -> Literal[0, 1]:
        # Execution-grounded toy grade: reward 1 iff the golden target was deployed correctly.
        bucket = deployed_state.get(_GOLDEN_RESOURCE)
        if isinstance(bucket, dict) and bucket.get("VersioningEnabled") is True:
            return 1
        return 0

    def grade_and_record(
        self,
        trajectory_id: str,
        deployed_state: dict[str, Any],
        *,
        nonce: str,
        attempt: int = 0,
    ) -> GradedRewardRecord:
        key = (trajectory_id, attempt)
        if key in self._worm:
            # Append-only: a divergent re-grade appends a new attempt, never overwrites.
            raise ValueError(f"WORM violation: {key} already written")
        reward = self._grade(deployed_state)
        report = json.dumps(
            {"trajectory_id": trajectory_id, "deployed_state": deployed_state, "reward": reward},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        fields: dict[str, Any] = {
            "trajectory_id": trajectory_id,
            "attempt": attempt,
            "reward": reward,
            "reportDigest": hashlib.sha256(report).hexdigest(),
            "graderVersion": "mock-account-b/0.1.0",
            "gradedAt": str(time.time_ns()),
            "nonce": nonce,
        }
        signature = self._key.sign(_canonical_unsigned(fields), ec.ECDSA(hashes.SHA256()))
        record = GradedRewardRecord(**fields, signature=signature.hex())
        self._worm[key] = record
        return record

    def fetch(self, trajectory_id: str) -> GradedRewardRecord | None:
        """Read-only lookup by the join key (latest attempt)."""
        matches = [record for (tid, _), record in self._worm.items() if tid == trajectory_id]
        if not matches:
            return None
        return max(matches, key=lambda record: record.attempt)

    def verify(self, record: GradedRewardRecord) -> bool:
        try:
            self.public_key.verify(
                bytes.fromhex(record.signature),
                _canonical_unsigned(record.model_dump()),
                ec.ECDSA(hashes.SHA256()),
            )
            return True
        except InvalidSignature:
            return False
