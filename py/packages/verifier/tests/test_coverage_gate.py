"""E2-6 (#141) scope 3: the per-asserted-property coverage gate (DECISIONS.md section 1).

Cloud Control ``GetResource`` omits a type's **write-only** properties (passwords, policy bodies). A
golden that asserts one is **ungradable**: a CORRECT deploy reads back WITHOUT that property, so the
reward core scores it a false 0. ``assert_golden_readable`` is the authoring-time gate that catches this
and quarantines the task (the issue's "quarantine or add a service-specific fallback"), rather than
shipping a task that can never score 1.
"""

from __future__ import annotations

import pytest

from assayops_verifier.models import GoldenResource, GoldenTarget
from assayops_verifier.read_scope import (
    Listability,
    ReadScope,
    RegionScope,
    TypeCoverage,
    UnknownReadCoverageError,
    UnreadableGoldenPropertyError,
    assert_golden_readable,
)

S3 = "AWS::S3::Bucket"
# A synthetic type whose schema marks `SecretBody` write-only (GetResource never returns it).
SECRETIVE = "AWS::Synthetic::Secretive"


def _scope() -> ReadScope:
    return ReadScope(
        coverages=(
            TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),
            TypeCoverage(
                SECRETIVE,
                RegionScope.REGIONAL,
                Listability.DIRECTLY_LISTABLE,
                write_only_paths=frozenset({"SecretBody"}),
            ),
        ),
        allowed_regions=("us-east-1",),
    )


def _golden(resource_type: str, properties: dict[str, object]) -> GoldenTarget:
    return GoldenTarget(
        resources=(GoldenResource(address="a", type=resource_type, properties=properties),)
    )


def test_a_fully_readable_golden_passes() -> None:
    assert_golden_readable(_golden(S3, {"BucketName": "b", "Versioning": "Enabled"}), _scope())


def test_a_golden_asserting_a_write_only_property_is_quarantined() -> None:
    # GetResource never returns `SecretBody`, so a correct deploy reads back without it -> a false 0.
    # The gate must reject this golden at authoring time (vector #15 -- never a silently-ungradable task).
    with pytest.raises(UnreadableGoldenPropertyError, match="SecretBody"):
        assert_golden_readable(_golden(SECRETIVE, {"SecretBody": "hunter2"}), _scope())


def test_a_readable_property_on_a_type_that_has_write_only_props_passes() -> None:
    # The adjacent-correct case (lessons.md): only the write-only paths are gated. A DIFFERENT,
    # readable property on the same type must STILL pass -- the gate must not over-reject the type.
    assert_golden_readable(_golden(SECRETIVE, {"Description": "readable"}), _scope())


def test_a_golden_whose_type_is_out_of_scope_fails_closed() -> None:
    # A golden type with no read-coverage entry cannot be graded soundly -> fail closed (never assume
    # readable). Reuses the scope's fail-closed lookup.
    with pytest.raises(UnknownReadCoverageError):
        assert_golden_readable(_golden("AWS::SQS::Queue", {"QueueName": "q"}), _scope())
