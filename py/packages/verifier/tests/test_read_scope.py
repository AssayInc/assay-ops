"""E2-6 (#141): the verifier-side read-coverage matrix -- the closed-world enumeration's scope.

A ``ReadScope`` is the in-scope ``{type -> (region scope, listability, write-only props)}`` matrix
the closed-world enumeration walks (DECISIONS.md section 1 "E3-4 read coverage"; the #80 spike). It
fails closed on an unregistered in-scope type and resolves each type's enumeration Regions per its
scope (GLOBAL services at their control Region; REGIONAL services at every allowed Region) -- the
per-type Region matrix, never a blanket rule.
"""

from __future__ import annotations

import pytest

from assayops_verifier.read_scope import (
    Listability,
    ReadScope,
    RegionScope,
    TypeCoverage,
    UnknownReadCoverageError,
)

S3 = "AWS::S3::Bucket"
IAM_ROLE = "AWS::IAM::Role"


def _scope() -> ReadScope:
    return ReadScope(
        coverages=(
            TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),
            TypeCoverage(IAM_ROLE, RegionScope.GLOBAL, Listability.DIRECTLY_LISTABLE),
        ),
        allowed_regions=("us-east-1", "eu-west-1"),
    )


def test_coverage_resolves_a_registered_type() -> None:
    coverage = _scope().coverage(S3)

    assert coverage.type_name == S3
    assert coverage.region_scope is RegionScope.REGIONAL


def test_coverage_fails_closed_on_an_unregistered_type() -> None:
    # An in-scope type with no coverage entry cannot be enumerated soundly -> fail closed (the read
    # path can never prove `deployed set == golden set` for a type it has no coverage for, vector
    # #15).
    with pytest.raises(UnknownReadCoverageError):
        _scope().coverage("AWS::SQS::Queue")


def test_a_regional_type_enumerates_every_allowed_region() -> None:
    # A REGIONAL service can hold a resource in ANY allowed Region; missing one would let an extra
    # resource hide in an unscanned Region (vector #15) -- so it is enumerated across all of them.
    regions = _scope().regions_for(_scope().coverage(S3))

    assert regions == ("us-east-1", "eu-west-1")


def test_a_global_type_enumerates_only_its_control_region() -> None:
    # A GLOBAL service (IAM/Route53/CloudFront) lives at one control Region; enumerating it
    # per-Region would double-count. The matrix is per-type, not a blanket "every Region" rule
    # (DECISIONS.md s1).
    regions = _scope().regions_for(_scope().coverage(IAM_ROLE))

    assert regions == ("us-east-1",)


def test_a_scope_must_declare_at_least_one_region() -> None:
    with pytest.raises(ValueError, match="at least one allowed region"):
        ReadScope(
            coverages=(TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),),
            allowed_regions=(),
        )


def test_a_scope_rejects_duplicate_type_coverages() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ReadScope(
            coverages=(
                TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),
                TypeCoverage(S3, RegionScope.GLOBAL, Listability.DIRECTLY_LISTABLE),
            ),
            allowed_regions=("us-east-1",),
        )


def test_a_scope_rejects_duplicate_allowed_regions() -> None:
    # A region listed twice would read every REGIONAL resource twice -> a confusing adapter-level
    # DuplicateAddressError. Fail loud at the scope (mirrors the duplicate-type guard).
    with pytest.raises(ValueError, match="duplicate allowed_regions"):
        ReadScope(
            coverages=(TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),),
            allowed_regions=("us-east-1", "us-east-1"),
        )


def test_type_coverage_rejects_a_raw_json_pointer_write_only_path() -> None:
    # A nested write-only path (a JSON Pointer like "/Auth/Password") would silently miss the gate's
    # top-level check -- a false-0 hole. It fails closed at construction; the coverage-matrix source
    # must collapse each pointer to its top-level property name.
    with pytest.raises(ValueError, match="top-level property names"):
        TypeCoverage(
            S3,
            RegionScope.REGIONAL,
            Listability.DIRECTLY_LISTABLE,
            write_only_paths=frozenset({"/Auth/Password"}),
        )


def test_type_coverage_accepts_a_top_level_write_only_name() -> None:
    # The adjacent-correct case (lessons.md): a plain top-level name (collapsed form) is accepted.
    coverage = TypeCoverage(
        S3,
        RegionScope.REGIONAL,
        Listability.DIRECTLY_LISTABLE,
        write_only_paths=frozenset({"Password"}),
    )

    assert coverage.write_only_paths == frozenset({"Password"})
