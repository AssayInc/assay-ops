"""E17-S2 (#115) spike — the four reward-ledger primitives, proven real in the Python core.

A decision gate for E4 (the reward ledger): prove the primitives over the canonical
``@assayops/contracts`` ``RewardRecord`` (``reward∈{0,1}``), keyed by ``trajectory_id`` —
making #114's account-B mock stand-ins real (DECISIONS.md I3 / 4B / §8 / T4; the
``reward-ledger-worm`` skill):

- AC1  RFC 8785 JCS via ``rfc8785`` — conformant vs. the official vectors AND
       byte-identical to a TS ``canonicalize`` (the #29 signer ↔ consumer parity).
- AC2  KMS ``Sign`` call shape via boto3 — ECDSA P-256, ``MessageType=DIGEST`` (I3).
- AC3  S3 Object Lock WORM + conditional write-once; a re-grade appends a new attempt.
- AC4  Portable verify — verify the signed record OFFLINE with only the public key.

The go/no-go + full findings live in PROGRAM.md + the #115 comment. No AWS creds here, so
the boto3 call shapes run on ``moto`` and the recipe runs on real ``cryptography``: moto's
KMS crypto is non-functional (so AC4 is proven on cryptography; E4 must validate
offline-verify against real KMS), while moto S3 does enforce conditional write-once and
Compliance immutability of the signed version.
"""

from __future__ import annotations

import datetime
import glob
import hashlib
import json
import pathlib
import shutil
import subprocess

import boto3
import pytest
import rfc8785
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from ledger_spike import (
    ALG,
    AccountBSigningKey,
    canonicalize,
    envelope_json,
    parse_envelope,
    verify_offline,
    worm_object_key,
)
from moto import mock_aws

from assayops_contracts import RewardRecord

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
TS_CANONICALIZE = REPO_ROOT / "ts" / "packages" / "contracts" / "scripts" / "jcs-canonicalize.ts"
JCS_VECTORS = pathlib.Path(__file__).parent / "fixtures" / "jcs"

LEDGER_BUCKET = "assayops-reward-ledger-spike"
RETAIN_UNTIL = datetime.datetime(2035, 1, 1, tzinfo=datetime.UTC)


def sample_record(**over: object) -> RewardRecord:
    """A canonical reward record (per the schema's modeling rules); ``over`` mutates fields."""
    fields: dict[str, object] = {
        "trajectory_id": "traj-01J9Z3K8QmR2",
        "attempt": 0,
        "reward": 1,
        "reportDigest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "graderVersion": "grader@1.0.0",
        "gradedAt": "1782518400000000000",
        "nonce": "5f4dcc3b5aa765d61d8327deb882cf99",
    }
    fields.update(over)
    return RewardRecord.model_validate(fields)


# --- AC1: RFC 8785 JCS canonicalization + cross-runtime parity ---


def test_rfc8785_matches_the_official_conformance_vectors() -> None:
    """``rfc8785`` is RFC 8785 conformant: byte-exact on the official vectors (UTF-16 key sort,
    surrogate pairs, control escapes, ECMAScript number forms)."""
    vectors = sorted(glob.glob(str(JCS_VECTORS / "*.input.json")))
    assert vectors, "official JCS conformance vectors must be present"
    for input_path in vectors:
        name = pathlib.Path(input_path).name.removesuffix(".input.json")
        value = json.loads(pathlib.Path(input_path).read_bytes())
        expected = (JCS_VECTORS / f"{name}.output.json").read_bytes()
        assert rfc8785.dumps(value) == expected, name


def test_jcs_diverges_from_naive_sorted_key_json_where_the_spec_requires() -> None:
    """Why #114's sorted-key ``json.dumps`` was a stand-in: on non-ASCII keys + small floats it
    disagrees with JCS byte-for-byte, which would silently break a cross-runtime signature."""
    value = {"é": 0.000001, "a": 1}
    naive = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    jcs = rfc8785.dumps(value)
    assert naive != jcs
    assert b"\xc3\xa9" in jcs and b"0.000001" in jcs  # JCS: raw UTF-8 key + ECMAScript number form
    assert b"\\u00e9" in naive and b"1e-06" in naive  # naive: escaped unicode + Python float repr


def test_canonicalize_consumes_the_real_contract_reward_record() -> None:
    """The real generated ``RewardRecord`` flows through: keys sorted, binary reward a bare int."""
    jcs = canonicalize(sample_record(reward=1))
    assert jcs.startswith(b'{"attempt":0,')  # keys sorted lexicographically (attempt is first)
    assert b'"reward":1' in jcs and b'"reward":1.0' not in jcs  # binary int, never a float
    assert b" " not in jcs  # no insignificant whitespace


def test_python_rfc8785_is_byte_identical_to_ts_canonicalize() -> None:
    """The #29 signer ↔ consumer byte-parity, shown: ``rfc8785`` (Python) and
    ``canonicalize`` (the RFC 8785 reference JS impl) emit identical bytes."""
    bun = shutil.which("bun")
    assert bun is not None, "bun must be on PATH (monorepo setup: bun install && uv sync)"

    values = [
        json.loads(pathlib.Path(p).read_bytes())
        for p in sorted(glob.glob(str(JCS_VECTORS / "*.input.json")))
    ]
    values.append(sample_record().model_dump(mode="json"))

    proc = subprocess.run(
        [bun, "run", str(TS_CANONICALIZE)],
        input=json.dumps(values),
        capture_output=True,
        encoding="utf-8",
        check=True,
        cwd=REPO_ROOT,
    )
    ts_outputs = proc.stdout.split("\n")
    assert len(ts_outputs) == len(values)
    for value, ts_out in zip(values, ts_outputs, strict=True):
        assert rfc8785.dumps(value) == ts_out.encode("utf-8")


# --- AC2: KMS asymmetric Sign call shape (boto3 / moto) ---


def test_kms_sign_call_shape_matches_the_i3_recipe() -> None:
    """AC2: the boto3 KMS ``Sign`` call E4 will make — an ``ECC_NIST_P256`` / ``SIGN_VERIFY``
    key signing with ``MessageType=DIGEST`` + ``ECDSA_SHA_256`` over ``SHA-256(JCS(record))``
    — returns a signature + an exportable P-256 SPKI public key. (moto's KMS crypto is faked;
    correctness + offline verify is proven on real ``cryptography`` below.)"""
    digest = hashlib.sha256(canonicalize(sample_record())).digest()
    with mock_aws():
        kms = boto3.client("kms", region_name="us-east-1")
        key_id = kms.create_key(KeySpec="ECC_NIST_P256", KeyUsage="SIGN_VERIFY")["KeyMetadata"][
            "KeyId"
        ]
        signed = kms.sign(
            KeyId=key_id,
            Message=digest,
            MessageType="DIGEST",
            SigningAlgorithm="ECDSA_SHA_256",
        )
        assert signed["SigningAlgorithm"] == "ECDSA_SHA_256"
        assert isinstance(signed["Signature"], (bytes, bytearray)) and signed["Signature"]
        public_key = serialization.load_der_public_key(
            kms.get_public_key(KeyId=key_id)["PublicKey"]
        )
        assert isinstance(public_key, ec.EllipticCurvePublicKey)
        assert isinstance(public_key.curve, ec.SECP256R1)  # P-256, per I3


# --- AC4: portable/public offline verification (real cryptography) ---


def test_signed_record_verifies_offline_with_only_the_public_key() -> None:
    """AC4, the portable proof: account B signs (private key never leaves B); anyone
    verifies with ONLY the SPKI public key, offline — no KMS call, no trust in Assay."""
    signer = AccountBSigningKey()
    signed = signer.sign_record(sample_record())
    assert verify_offline(signer.public_key_spki_der(), signed.payload, signed.signature) is True
    assert signed.alg == ALG and signed.key_id


def test_a_tampered_record_fails_offline_verification() -> None:
    """Flip reward 1→0: the canonical bytes change, so the signature no longer covers them."""
    signer = AccountBSigningKey()
    signed = signer.sign_record(sample_record(reward=1))
    tampered_payload = canonicalize(sample_record(reward=0))
    assert tampered_payload != signed.payload
    assert verify_offline(signer.public_key_spki_der(), tampered_payload, signed.signature) is False


def test_a_record_signed_by_a_foreign_key_does_not_verify() -> None:
    """Vector #9 (forgery): a record signed by an agent's own key fails under B's key."""
    account_b = AccountBSigningKey()
    payload = canonicalize(sample_record(reward=1))
    attacker_signature = ec.generate_private_key(ec.SECP256R1()).sign(
        payload, ec.ECDSA(hashes.SHA256())
    )
    assert verify_offline(account_b.public_key_spki_der(), payload, attacker_signature) is False


def test_a_malformed_signature_fails_without_raising() -> None:
    """The agent controls the bytes, so malformed must mean 'does not verify', never raise."""
    signer = AccountBSigningKey()
    signed = signer.sign_record(sample_record())
    bad = verify_offline(signer.public_key_spki_der(), signed.payload, b"not-a-der-signature")
    assert bad is False


# --- AC3: S3 Object Lock WORM + conditional write-once (boto3 / moto) ---


def test_worm_conditional_write_is_first_writer_wins() -> None:
    """AC3: written exactly once. The first conditional ``PutObject`` (``If-None-Match=*``)
    wins; a second to the same key is REJECTED (412 ``PreconditionFailed``)."""
    signer = AccountBSigningKey()
    signed = signer.sign_record(sample_record())
    key = worm_object_key("traj-worm", 0)
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=LEDGER_BUCKET, ObjectLockEnabledForBucket=True)
        first = s3.put_object(
            Bucket=LEDGER_BUCKET,
            Key=key,
            Body=envelope_json(signed),
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=RETAIN_UNTIL,
            IfNoneMatch="*",
        )
        with pytest.raises(ClientError) as exc:
            s3.put_object(Bucket=LEDGER_BUCKET, Key=key, Body=b"second-writer", IfNoneMatch="*")
        assert exc.value.response["Error"]["Code"] == "PreconditionFailed"
        stored = s3.get_object(Bucket=LEDGER_BUCKET, Key=key, VersionId=first["VersionId"])[
            "Body"
        ].read()
        assert stored == envelope_json(signed)  # original record byte-unchanged


def test_object_lock_compliance_blocks_deletion_of_the_signed_version() -> None:
    """AC3 immutability: under Compliance retention no principal can delete the signed
    object *version* (delete → ``AccessDenied``); pinning ``(key, versionId)`` retrieves it."""
    signer = AccountBSigningKey()
    signed = signer.sign_record(sample_record())
    key = worm_object_key("traj-immutable", 0)
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=LEDGER_BUCKET, ObjectLockEnabledForBucket=True)
        put = s3.put_object(
            Bucket=LEDGER_BUCKET,
            Key=key,
            Body=envelope_json(signed),
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=RETAIN_UNTIL,
            IfNoneMatch="*",
        )
        with pytest.raises(ClientError) as exc:
            s3.delete_object(Bucket=LEDGER_BUCKET, Key=key, VersionId=put["VersionId"])
        assert exc.value.response["Error"]["Code"] == "AccessDenied"
        assert s3.get_object(Bucket=LEDGER_BUCKET, Key=key, VersionId=put["VersionId"])[
            "Body"
        ].read()


def test_object_lock_is_version_scoped_the_signed_version_survives_a_new_put() -> None:
    """Version-scoped caveat: an unconditioned overwrite makes a NEW version, but the signed
    version (pinned by ``versionId``) is preserved + still verifies — so we pin the version."""
    signer = AccountBSigningKey()
    signed = signer.sign_record(sample_record())
    key = worm_object_key("traj-versioned", 0)
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=LEDGER_BUCKET, ObjectLockEnabledForBucket=True)
        put = s3.put_object(
            Bucket=LEDGER_BUCKET,
            Key=key,
            Body=envelope_json(signed),
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=RETAIN_UNTIL,
            IfNoneMatch="*",
        )
        s3.put_object(Bucket=LEDGER_BUCKET, Key=key, Body=b"unconditioned-new-version")
        pinned = s3.get_object(Bucket=LEDGER_BUCKET, Key=key, VersionId=put["VersionId"])[
            "Body"
        ].read()
        assert pinned == envelope_json(signed)
        recovered = parse_envelope(pinned)
        assert verify_offline(signer.public_key_spki_der(), recovered.payload, recovered.signature)


def test_a_regrade_appends_a_new_attempt_and_never_overwrites() -> None:
    """A divergent re-grade is a NEW attempt under a new key (append-only) — ties to determinism
    (golden ×K → identical reward; a divergence must surface as a new signed record)."""
    signer = AccountBSigningKey()
    attempt0 = signer.sign_record(sample_record(trajectory_id="traj-rg", attempt=0, reward=1))
    attempt1 = signer.sign_record(sample_record(trajectory_id="traj-rg", attempt=1, reward=0))
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=LEDGER_BUCKET, ObjectLockEnabledForBucket=True)
        for attempt, signed in ((0, attempt0), (1, attempt1)):
            s3.put_object(
                Bucket=LEDGER_BUCKET,
                Key=worm_object_key("traj-rg", attempt),
                Body=envelope_json(signed),
                ObjectLockMode="COMPLIANCE",
                ObjectLockRetainUntilDate=RETAIN_UNTIL,
                IfNoneMatch="*",
            )
        keys = {obj["Key"] for obj in s3.list_objects_v2(Bucket=LEDGER_BUCKET)["Contents"]}
        assert keys == {"traj-rg#0", "traj-rg#1"}
        stored0 = s3.get_object(Bucket=LEDGER_BUCKET, Key="traj-rg#0")["Body"].read()
        assert stored0 == envelope_json(attempt0)  # attempt 0 untouched by the new attempt
        assert verify_offline(signer.public_key_spki_der(), attempt0.payload, attempt0.signature)


# --- Capstone: the full portable lifecycle (all four primitives end to end) ---


def test_full_portable_lifecycle_sign_worm_store_then_offline_verify() -> None:
    """End to end: account B JCS-canonicalizes + signs the record, WORM-stores it, and a
    buying lab reads it back and verifies OFFLINE with only the public key."""
    signer = AccountBSigningKey()
    public_key = signer.public_key_spki_der()  # distributed once (kms:GetPublicKey)
    record = sample_record(trajectory_id="traj-e2e", reward=1)
    signed = signer.sign_record(record)
    key = worm_object_key("traj-e2e", 0)
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=LEDGER_BUCKET, ObjectLockEnabledForBucket=True)
        put = s3.put_object(
            Bucket=LEDGER_BUCKET,
            Key=key,
            Body=envelope_json(signed),
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=RETAIN_UNTIL,
            IfNoneMatch="*",
        )
        stored = s3.get_object(Bucket=LEDGER_BUCKET, Key=key, VersionId=put["VersionId"])[
            "Body"
        ].read()

    # The lab holds only the bytes + the public key — no KMS, no boto3, no trust in Assay.
    recovered = parse_envelope(stored)
    assert verify_offline(public_key, recovered.payload, recovered.signature) is True
    # the payload decodes to the contract record it claims to be
    assert RewardRecord.model_validate_json(recovered.payload) == record
