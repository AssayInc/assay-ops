"""Author the locked JCS golden-vector corpus -> contracts/vectors/jcs-golden.json.

Regenerate with ``just vectors``. The corpus locks the canonical RFC 8785 (JCS) bytes of
representative contract records (DECISIONS.md I3) so the Python signer (``rfc8785``) and the TS
consumer (npm ``canonicalize``) stay byte-identical -- the parity the cross-runtime reward signature
rests on. Deterministic: re-running produces no diff (the #29 parity-gate precondition).

EDIT THE RECORD SET ONLY IN A ``fixture-change`` PR (DECISIONS.md Section 8): the agent that writes
code never edits what scores it; ``contracts/vectors`` is editable only in PRs from #28.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

from pydantic import BaseModel

from assayops_contracts import DiffIR, RewardRecord, TaskSpec, Trajectory
from assayops_contracts.jcs import canonicalize

GOLDEN = pathlib.Path(__file__).resolve().parents[4] / "contracts" / "vectors" / "jcs-golden.json"

# The authored corpus. The reward-record (the signed artifact) covers both reward values + the
# ns-timestamp digit string. diff-ir vectors carry a number in an open `Any` field and omitted
# optional property-sides (null). One task-spec carries non-ASCII (raw UTF-8). Numbers stay
# IEEE-754-representable (the contract strings large values, #26); rfc8785 fails closed otherwise.
# EDIT ONLY IN A `fixture-change` PR (DECISIONS.md Section 8).

_REWARD_ONE = RewardRecord.model_validate(
    {
        "trajectory_id": "traj-01J9Z3K8QmR2",
        "attempt": 0,
        "reward": 1,
        "reportDigest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "graderVersion": "grader@1.0.0",
        "gradedAt": "1782518400000000000",
        "nonce": "5f4dcc3b5aa765d61d8327deb882cf99",
    }
)

_REWARD_ZERO = RewardRecord.model_validate(
    {
        "trajectory_id": "traj-01J9Z3K8QmR3",
        "attempt": 1,
        "reward": 0,
        "reportDigest": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
        "graderVersion": "grader@1.0.0",
        "gradedAt": "1782604800000000000",
        "nonce": "ad0234829205b9033196ba818f7a872b",
    }
)

_TRAJECTORY = Trajectory.model_validate(
    {
        "trajectory_id": "traj-01J9Z3K8QmR2",
        "task_id": "task-s3-versioning-001",
        "createdAt": "1782518400000000000",
        "steps": [{"index": 0, "observation": {}, "action": {}}],
    }
)

_DIFF_IR = DiffIR.model_validate(
    {
        "resources": [
            {
                "address": "AppBucket",
                "type": "AWS::S3::Bucket",
                "change": "modified",
                "propertyDiffs": [
                    {
                        "path": "VersioningConfiguration.Status",
                        "expected": "Enabled",
                        "actual": "Suspended",
                    }
                ],
            },
            {
                "address": "LogBucket",
                "type": "AWS::S3::Bucket",
                "change": "unchanged",
                "propertyDiffs": [],
            },
        ]
    }
)

_DIFF_IR_NUMERIC = DiffIR.model_validate(
    {
        "resources": [
            {
                "address": "LogBucket",
                "type": "AWS::S3::Bucket",
                "change": "modified",
                "propertyDiffs": [
                    {
                        "path": "LifecycleConfiguration.Rules[0].ExpirationInDays",
                        "expected": 30,
                        "actual": 7,
                    }
                ],
            }
        ]
    }
)

# Two propertyDiffs, each omitting one optional side (anyOf requires one of expected/actual). The
# model materializes the missing side to null (`actual:null` / `expected:null`), both schema-valid.
# Locks the PropertyDiff optional parity, both sides. `propertyDiffs` -> INVALID null (#26/#27 bug).
_DIFF_IR_OPTIONAL_SIDES = DiffIR.model_validate(
    {
        "resources": [
            {
                "address": "AppBucket",
                "type": "AWS::S3::Bucket",
                "change": "modified",
                "propertyDiffs": [
                    {"path": "VersioningConfiguration.Status", "expected": "Enabled"},
                    {"path": "LoggingConfiguration.Enabled", "actual": "true"},
                ],
            }
        ]
    }
)

_TASK_TERRAFORM = TaskSpec.model_validate(
    {
        "task_id": "task-s3-versioning-001",
        "title": "Enable versioning on the app S3 bucket",
        "description": "Deploy an S3 bucket with versioning enabled.",
        "tool": "terraform",
        "seed": "seed-9a3f1c2e",
    }
)

_TASK_CDK_UNICODE = TaskSpec.model_validate(
    {
        "task_id": "task-rds-encryption-002",
        "title": "Activer le chiffrement RDS",
        "description": "Déployer une instance RDS avec le chiffrement au repos activé.",
        "tool": "cdk",
        "seed": "seed-7b2e4f1a",
    }
)


def _records() -> list[tuple[str, str, BaseModel]]:
    return [
        ("reward-record/reward-one", "reward-record", _REWARD_ONE),
        ("reward-record/reward-zero", "reward-record", _REWARD_ZERO),
        ("trajectory/with-step", "trajectory", _TRAJECTORY),
        ("diff-ir/modified-and-unchanged", "diff-ir", _DIFF_IR),
        ("diff-ir/numeric-property", "diff-ir", _DIFF_IR_NUMERIC),
        ("diff-ir/optional-property-sides", "diff-ir", _DIFF_IR_OPTIONAL_SIDES),
        ("task-spec/terraform", "task-spec", _TASK_TERRAFORM),
        ("task-spec/cdk-unicode", "task-spec", _TASK_CDK_UNICODE),
    ]


def _build() -> dict[str, object]:
    vectors: list[dict[str, object]] = []
    for name, schema, model in _records():
        canonical = canonicalize(model)
        vectors.append(
            {
                "name": name,
                "schema": schema,
                "record": model.model_dump(mode="json"),
                "canonical": canonical.decode("utf-8"),
                "sha256": hashlib.sha256(canonical).hexdigest(),
            }
        )
    return {
        "$comment": (
            "Locked JCS golden corpus (DECISIONS.md I3, Section 8) -- edit only in a fixture-change"
            " PR; regenerate with `just vectors`. Per vector: record -> canonical (RFC 8785 JCS) ->"
            " sha256. Python `rfc8785` and TS `canonicalize` must reproduce it byte-for-byte."
        ),
        "vectors": vectors,
    }


def main() -> None:
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(
        json.dumps(_build(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
