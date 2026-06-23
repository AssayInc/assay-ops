"""E1-3 (#28) — JCS canonicalization + the locked golden-vector corpus.

The contract spine's canonical-byte recipe (DECISIONS.md I3): a record canonicalizes to RFC 8785
(JCS) bytes -- the exact bytes the account-B reward ledger signs. The Python signer (``rfc8785``)
and the TS consumer (npm ``canonicalize``) emit **identical** bytes;
``contracts/vectors/jcs-golden.json`` locks them, and this module is the Python half of the gate.
Regenerate the corpus with ``just vectors`` -- a ``fixture-change`` PR only (DECISIONS.md Section 8;
the agent that writes code never edits the grader).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
from typing import TypedDict

from pydantic import BaseModel

from assayops_contracts import DiffIR, RewardRecord, TaskSpec, Trajectory
from assayops_contracts.jcs import canonical_digest, canonicalize

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
GOLDEN = REPO_ROOT / "contracts" / "vectors" / "jcs-golden.json"
TS_CANONICALIZE = REPO_ROOT / "ts" / "packages" / "contracts" / "scripts" / "jcs-canonicalize.ts"

MODELS: dict[str, type[BaseModel]] = {
    "reward-record": RewardRecord,
    "trajectory": Trajectory,
    "diff-ir": DiffIR,
    "task-spec": TaskSpec,
}


class Vector(TypedDict):
    name: str
    schema: str
    record: dict[str, object]
    canonical: str
    sha256: str


def load_vectors() -> list[Vector]:
    vectors: list[Vector] = json.loads(GOLDEN.read_text(encoding="utf-8"))["vectors"]
    return vectors


# --- the production canonicalize behaviour (the bytes the reward ledger signs, I3) ---

BASE: dict[str, object] = {
    "trajectory_id": "traj-01J9Z3K8QmR2",
    "attempt": 0,
    "reward": 1,
    "reportDigest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "graderVersion": "grader@1.0.0",
    "gradedAt": "1782518400000000000",
    "nonce": "5f4dcc3b5aa765d61d8327deb882cf99",
}


def record(**over: object) -> RewardRecord:
    return RewardRecord.model_validate({**BASE, **over})


def test_canonicalize_sorts_keys_and_strips_whitespace() -> None:
    jcs = canonicalize(record())
    assert jcs.startswith(
        b'{"attempt":0,'
    )  # keys sorted lexicographically (UTF-16) -> attempt first
    assert jcs.endswith(b'"trajectory_id":"traj-01J9Z3K8QmR2"}')  # ...trajectory_id last
    assert b" " not in jcs  # no insignificant whitespace


def test_canonicalize_keeps_the_binary_reward_a_bare_integer() -> None:
    # reward in {0,1} stays a bare integer in the signed bytes -- a 1.0 would change the digest.
    assert b'"reward":1' in canonicalize(record(reward=1))
    assert b'"reward":1.0' not in canonicalize(record(reward=1))
    assert b'"reward":0' in canonicalize(record(reward=0))


def test_canonicalize_keeps_the_ns_timestamp_a_quoted_string() -> None:
    # gradedAt stays a quoted digit string -- a number form would lose precision on 19-digit ns.
    assert b'"gradedAt":"1782518400000000000"' in canonicalize(record())


def test_canonical_digest_is_sha256_of_the_canonical_bytes() -> None:
    assert canonical_digest(record()) == hashlib.sha256(canonicalize(record())).digest()


# --- the locked golden corpus: both sides reproduce identical canonical bytes (#28 AC) ---


def test_golden_corpus_is_present_and_locks_both_binary_reward_values() -> None:
    vectors = load_vectors()
    assert vectors, (
        "contracts/vectors/jcs-golden.json must hold the locked corpus (run `just vectors`)"
    )
    rewards = {v["record"]["reward"] for v in vectors if v["schema"] == "reward-record"}
    assert rewards == {0, 1}, "the corpus must lock both binary reward values (the signed artifact)"


def test_python_canonicalize_reproduces_every_golden_vector() -> None:
    for v in load_vectors():
        model = MODELS[v["schema"]].model_validate(v["record"])
        # the stored record is the validation fixed point -- exactly what the signer canonicalizes
        assert model.model_dump(mode="json") == v["record"], v["name"]
        jcs = canonicalize(model)
        assert jcs == v["canonical"].encode("utf-8"), v["name"]
        assert canonical_digest(model).hex() == v["sha256"], v["name"]
        assert hashlib.sha256(jcs).hexdigest() == v["sha256"], v["name"]


def test_python_and_ts_canonicalize_are_byte_identical() -> None:
    """The cross-language byte-parity the reward signature rests on: the Python signer (``rfc8785``)
    and the TS consumer (npm ``canonicalize``) emit identical bytes for every golden record."""
    bun = shutil.which("bun")
    assert bun is not None, "bun must be on PATH (monorepo setup: bun install && uv sync)"
    vectors = load_vectors()
    proc = subprocess.run(
        [bun, "run", str(TS_CANONICALIZE)],
        input=json.dumps([v["record"] for v in vectors]),
        capture_output=True,
        encoding="utf-8",
        check=True,
        cwd=REPO_ROOT,
    )
    ts_outputs = proc.stdout.split("\n")
    assert len(ts_outputs) == len(vectors)
    for v, ts_out in zip(vectors, ts_outputs, strict=True):
        ts_bytes = ts_out.encode("utf-8")
        assert ts_bytes == v["canonical"].encode("utf-8"), v["name"]  # TS == the locked golden
        assert ts_bytes == canonicalize(MODELS[v["schema"]].model_validate(v["record"])), v["name"]
