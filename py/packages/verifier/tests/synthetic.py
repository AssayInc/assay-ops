"""Synthetic engine-validation fixtures — NOT the private golden corpus (#76).

These exercise the golden-target generator *engine* in-repo. The real per-task golden builders live
in the private store (DECISIONS.md I11 + the held-out-data residency rule — gold/corpus never
committed); only synthetic fixtures are committed here.
"""

from __future__ import annotations

from assayops_contracts import TaskSpec, Tool

from assayops_verifier.golden import GoldenContext
from assayops_verifier.models import GoldenResource

SYNTHETIC_TASK_ID = "synthetic-s3-bucket"


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


def make_task(task_id: str = SYNTHETIC_TASK_ID, seed: str = "seed-001") -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        title="Synthetic S3 bucket",
        description="Deploy a versioned S3 bucket (engine-validation fixture).",
        tool=Tool.terraform,
        seed=seed,
    )
