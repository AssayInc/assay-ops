"""Synthetic engine-validation fixtures — NOT the private golden corpus (#76).

These exercise the golden-target generator *engine* and the #31 generate→grade integration in-repo.
The real per-task golden builders live in the private store (DECISIONS.md I11 + the held-out-data
residency rule — gold/corpus never committed); only synthetic fixtures are committed here.
"""

from __future__ import annotations

from assayops_contracts import TaskSpec, Tool
from assayops_diff_ir import NormalizedResource, NormalizedState, Provenance

from assayops_verifier.golden import GoldenContext
from assayops_verifier.models import GoldenResource, GoldenTarget

SYNTHETIC_TASK_ID = "synthetic-s3-bucket"
NORMALIZABLE_TASK_ID = "synthetic-normalizable"
NONE_PROPERTY_TASK_ID = "synthetic-none-property"
DOLLAR_KEY_TASK_ID = "synthetic-dollar-key"


def s3_bucket_builder(ctx: GoldenContext) -> list[GoldenResource]:
    # A versioned S3 bucket whose name is a seed-derived ephemeral *intent-bearing* identifier: the
    # agent must deploy a bucket with exactly this name, and it varies per seed (anti-memorization,
    # vector #14) yet regenerates byte-identically from the same seed (DECISIONS.md 2A).
    suffix = ctx.token("primary_bucket", length=8)
    return [
        GoldenResource(
            address="primary_bucket",
            type="AWS::S3::Bucket",
            properties={
                "BucketName": f"assayops-{suffix}",
                "VersioningConfiguration": {"Status": "Enabled"},
            },
        )
    ]


def normalizable_builder(ctx: GoldenContext) -> list[GoldenResource]:
    # Properties chosen so a CORRECT deploy can match by VALUE while differing in JSON
    # representation — the integration proof that "zero *normalized* diff" tolerates JCS-equal
    # encodings: an int golden value equals its float read-back (90 == 90.0) and object key order is
    # irrelevant. Reward must be 1.
    return [
        GoldenResource(
            address="config",
            type="AWS::S3::Bucket",
            properties={"RetentionDays": 90, "Tags": {"team": "core", "env": "test"}},
        )
    ]


def none_property_builder(ctx: GoldenContext) -> list[GoldenResource]:
    # A golden the generator ACCEPTS (#75's value validator allows a None value) but the diff-ir
    # grading validator (#34) REJECTS ("omit an absent property, never store None"). The bridge must
    # fail closed — never silently grade a golden the reward core cannot represent (§8, vector #15).
    return [GoldenResource(address="thing", type="AWS::S3::Bucket", properties={"Note": None})]


def dollar_key_builder(ctx: GoldenContext) -> list[GoldenResource]:
    # The second documented divergence: the generator (#75) doesn't reserve `$`, but the diff-ir
    # grading core (#34) reserves `$`-keys for the $type diff marker and REJECTS them. The bridge
    # must fail closed on a `$`-key golden too — the adjacent case to None (see lessons.md).
    return [GoldenResource(address="thing", type="AWS::S3::Bucket", properties={"$type": "spoof"})]


def make_task(task_id: str = SYNTHETIC_TASK_ID, seed: str = "seed-001") -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        title="Synthetic S3 bucket",
        description="Deploy a versioned S3 bucket (engine-validation fixture).",
        tool=Tool.terraform,
        seed=seed,
    )


def deployed_from_golden(target: GoldenTarget) -> NormalizedState:
    """The deployed read-back a CORRECT deploy yields: the golden's resources, tagged DEPLOYED_READ.

    Stands in for the boto3 Cloud Control read path (#30, not built yet) in #31's known-pair
    integration test — a correct deployment's read-back deployed state is, by definition, the
    golden's resource set. A *test* helper (not the production bridge, which tags GOLDEN_TARGET);
    drift cases perturb this.
    """
    return NormalizedState(
        provenance=Provenance.DEPLOYED_READ,
        resources=tuple(
            NormalizedResource(address=r.address, type=r.type, properties=r.properties)
            for r in target.resources
        ),
    )
