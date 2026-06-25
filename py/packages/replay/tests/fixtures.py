"""Shared fixtures for the determinism-harness tests.

``GradeOutcome``s are built through the **real** diff-ir reward core (``grade``), so the harness is
exercised against genuine outcomes rather than fabricated ones. ``FakeClientError`` is a
botocore-``ClientError``-shaped exception so the fail-closed / classifier paths run without
importing boto3 (the determinism package is boto3-free).
"""

from __future__ import annotations

from assayops_diff_ir import (
    GradeOutcome,
    NormalizedResource,
    NormalizedState,
    Provenance,
    grade,
)


def _state(provenance: Provenance, bucket: str) -> NormalizedState:
    return NormalizedState(
        provenance=provenance,
        resources=(
            NormalizedResource(
                address="primary",
                type="AWS::S3::Bucket",
                properties={"BucketName": bucket},
            ),
        ),
    )


def reward_1() -> GradeOutcome:
    """A real reward-1 outcome: deployed read == golden (zero normalized diff)."""
    return grade(
        _state(Provenance.DEPLOYED_READ, "assayops-correct"),
        _state(Provenance.GOLDEN_TARGET, "assayops-correct"),
    )


def reward_0() -> GradeOutcome:
    """A real reward-0 outcome: deployed read != golden (a nonzero property diff)."""
    return grade(
        _state(Provenance.DEPLOYED_READ, "assayops-wrong"),
        _state(Provenance.GOLDEN_TARGET, "assayops-expected"),
    )


def reward_0_other() -> GradeOutcome:
    """A second real reward-0 outcome with a DIFFERENT diff (a different wrong value) — same reward
    as ``reward_0`` but distinct canonical diff bytes, for the same-reward/different-diff test."""
    return grade(
        _state(Provenance.DEPLOYED_READ, "assayops-other-wrong"),
        _state(Provenance.GOLDEN_TARGET, "assayops-expected"),
    )


class FakeClientError(Exception):
    """A botocore-``ClientError``-shaped exception (``.response['Error']['Code']``) — lets tests
    exercise the code-based classifier and the fail-closed paths without importing boto3."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}
