"""A SYNTHETIC engine-validation corpus module -- NOT the private corpus (#76).

The committed fixture for the loader's tests only (held-out residency: real tasks/goldens live in
the private store, never in a code repo -- DECISIONS.md I11). Mirrors the contract a real private
corpus directory's ``corpus.py`` must satisfy: ``REGISTRY`` (the per-task golden builders),
``READ_SCOPE`` (the closed-world type x Region matrix), optional ``BRIDGE_REGISTRY``.
"""

from __future__ import annotations

from assayops_verifier import GoldenContext, GoldenRegistry, GoldenResource
from assayops_verifier.read_scope import Listability, ReadScope, RegionScope, TypeCoverage


def _bucket_builder(ctx: GoldenContext) -> list[GoldenResource]:
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


REGISTRY = GoldenRegistry()
REGISTRY.register("synthetic-corpus-task", _bucket_builder)

READ_SCOPE = ReadScope(
    coverages=(
        TypeCoverage("AWS::S3::Bucket", RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),
    ),
    allowed_regions=("us-east-1",),
)
