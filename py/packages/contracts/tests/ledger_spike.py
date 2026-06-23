"""E17-S2 (#115) spike helper — the real reward-ledger primitives, proven feasible.

Proves DECISIONS.md I3 / 4B / §8 / T4 feasible in the Python core before E4 builds the
ledger — these are the real primitives that will replace #114's stand-ins (sorted-key
JSON, message-hash ECDSA, in-memory WORM); this spike does not touch that mock. See the
test module for the proof and findings; the ``reward-ledger-worm`` skill for the rules.

Primitives: ``canonicalize`` (RFC 8785 JCS via ``rfc8785``), ``AccountBSigningKey``
(the account-B KMS asymmetric-key analog: ECDSA P-256, ``MessageType=DIGEST`` over
the JCS→SHA-256 digest, I3), ``verify_offline`` (verify with only the public key),
and the WORM envelope + append-only key.

``cryptography`` backs the signing because moto's KMS crypto is non-functional (the
boto3 KMS call shape is proven in the test module). The private key never leaves
"account B". NOT the E4 build — real KMS/S3/IAM + policies live in account B (E4).
"""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import json

import rfc8785
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from assayops_contracts import RewardRecord

ALG = "ECDSA_SHA_256"  # KMS SigningAlgorithm: ECDSA P-256 over a SHA-256 digest (DECISIONS.md I3)


def canonicalize(record: RewardRecord) -> bytes:
    """RFC 8785 (JCS) canonical bytes of the record — the bytes the signature covers.

    JSON mode so ``reward`` serializes to a bare ``0``/``1``; a conformant library
    (not hand-rolled ``json.dumps``) makes the bytes identical across runtimes."""
    return rfc8785.dumps(record.model_dump(mode="json"))


@dataclasses.dataclass(frozen=True)
class SignedRecord:
    """The WORM object: the canonical payload + a detached signature envelope.

    Per the ``reward-ledger-worm`` skill, store ``{payload, signature, keyId, alg}``."""

    payload: bytes  # JCS(record) — the signed bytes
    signature: bytes  # DER ECDSA-P256 over SHA-256(payload)
    key_id: str
    alg: str = ALG


class AccountBSigningKey:
    """Analog of the account-B KMS asymmetric signing key (``ECC_NIST_P256`` / ``SIGN_VERIFY``).

    The private key lives ONLY here (account B); the agent never holds it. The interface
    mirrors KMS so E4 can swap in boto3 KMS unchanged: ``sign_record`` ≙ ``kms:Sign``,
    ``public_key_spki_der`` ≙ ``kms:GetPublicKey``."""

    def __init__(self, key_id: str = "account-b/reward-signer") -> None:
        self._key = ec.generate_private_key(ec.SECP256R1())
        self.key_id = key_id

    def public_key_spki_der(self) -> bytes:
        """The public key as SPKI DER — distributed once for offline verification."""
        return self._key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def sign_record(self, record: RewardRecord) -> SignedRecord:
        payload = canonicalize(record)
        digest = hashlib.sha256(payload).digest()
        # MessageType=DIGEST: sign the precomputed digest (KMS hashes nothing further). The verifier
        # recomputes SHA-256 over the canonical payload, so the two agree on the signed digest.
        signature = self._key.sign(digest, ec.ECDSA(Prehashed(hashes.SHA256())))
        return SignedRecord(payload=payload, signature=signature, key_id=self.key_id)


def verify_offline(public_key_spki_der: bytes, payload: bytes, signature: bytes) -> bool:
    """The portable proof: verify ``signature`` over ``payload`` with ONLY the public key, offline.

    Pins the exact KMS recipe — an ECDSA **P-256** (SECP256R1) key over SHA-256 — so a non-EC or
    wrong-curve key fails closed. Verification never trusts an envelope's ``alg``/``keyId``; E4
    binds key selection. Returns ``False`` (never raises) for a bad signature, a foreign/wrong-curve
    key, or malformed bytes — the verifier controls none of the agent-submitted bytes."""
    try:
        public_key = serialization.load_der_public_key(public_key_spki_der)
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False
        if not isinstance(public_key.curve, ec.SECP256R1):
            return False
        public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError, UnsupportedAlgorithm):
        return False


def worm_object_key(trajectory_id: str, attempt: int) -> str:
    """Append-only ledger key: a re-grade is a new ``attempt``, never an overwrite."""
    return f"{trajectory_id}#{attempt}"


def envelope_json(signed: SignedRecord) -> bytes:
    """The stored WORM bytes for a signed record (canonical, so the object is deterministic)."""
    return rfc8785.dumps(
        {
            "payload": signed.payload.decode("utf-8"),
            "signature": base64.b64encode(signed.signature).decode("ascii"),
            "keyId": signed.key_id,
            "alg": signed.alg,
        }
    )


def parse_envelope(body: bytes) -> SignedRecord:
    """Inverse of ``envelope_json`` — reconstruct the signed record from stored WORM bytes."""
    envelope = json.loads(body)
    return SignedRecord(
        payload=envelope["payload"].encode("utf-8"),
        signature=base64.b64decode(envelope["signature"]),
        key_id=envelope["keyId"],
        alg=envelope["alg"],
    )
