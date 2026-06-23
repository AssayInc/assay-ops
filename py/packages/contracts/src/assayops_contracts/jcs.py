"""RFC 8785 (JCS) canonicalization for AssayOps contract records.

The single definition of the canonical-byte recipe the account-B reward ledger signs (DECISIONS.md
I3): ``record -> RFC 8785 JCS -> UTF-8 -> SHA-256 -> KMS Sign (ECDSA P-256, MessageType=DIGEST)``. A
conformant library (``rfc8785``), not a hand-rolled ``json.dumps``, makes the bytes identical across
runtimes -- the parity the cross-runtime signature rests on: the TS consumer canonicalizes the same
record with npm ``canonicalize`` to verify. ``contracts/vectors/jcs-golden.json`` locks that parity.
"""

from __future__ import annotations

import hashlib

import rfc8785
from pydantic import BaseModel


def canonicalize(record: BaseModel) -> bytes:
    """The RFC 8785 (JCS) canonical bytes of a contract record -- the bytes the reward ledger signs.

    JSON mode so the binary ``reward`` is a bare ``0``/``1`` and ns-timestamps stay quoted strings;
    ``rfc8785`` pins every other degree of freedom (key sort, number form, string escapes).
    """
    return rfc8785.dumps(record.model_dump(mode="json"))


def canonical_digest(record: BaseModel) -> bytes:
    """SHA-256 over the canonical bytes -- the digest KMS signs (``MessageType=DIGEST``, I3)."""
    return hashlib.sha256(canonicalize(record)).digest()
