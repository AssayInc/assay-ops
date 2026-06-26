"""E2-6 (#141) scope 2: the closed-world enumeration walk over the type x Region matrix.

``read_closed_world`` makes ``deployed set == golden set`` (vector #15) sound by enumerating the
in-scope account EXHAUSTIVELY: every in-scope listable type, in every Region its coverage allows
(REGIONAL -> all allowed Regions; GLOBAL -> the control Region), GetResource-normalizing each. It
FAILS CLOSED on anything that would leave a blind spot an extra resource could hide in: an
unlistable / context-listable in-scope type, or a required Region with no reader. (A list / get
transient is routed through the 7A K-run by the underlying ``read_type``; tested in test_read.)
"""

from __future__ import annotations

import pytest
from cloud_control_fakes import FakeCloudControlClient

from assayops_verifier.read import ClosedWorldError, DeployedStateReader, read_closed_world
from assayops_verifier.read_scope import Listability, ReadScope, RegionScope, TypeCoverage

S3 = "AWS::S3::Bucket"
IAM_ROLE = "AWS::IAM::Role"


def _reader(*resources: tuple[str, str]) -> DeployedStateReader:
    return DeployedStateReader(FakeCloudControlClient({key: {} for key in resources}))


def test_a_regional_type_is_enumerated_in_every_allowed_region() -> None:
    # bucket-a is in us-east-1, bucket-b in eu-west-1. A REGIONAL type MUST be read in both -- an
    # extra in an unscanned Region would hide (vector #15).
    east = _reader((S3, "bucket-a"))
    west = _reader((S3, "bucket-b"))
    scope = ReadScope(
        coverages=(TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),),
        allowed_regions=("us-east-1", "eu-west-1"),
    )

    reads = read_closed_world({"us-east-1": east, "eu-west-1": west}, scope)

    assert {read.identifier for read in reads} == {"bucket-a", "bucket-b"}


def test_a_global_type_is_enumerated_only_in_its_control_region() -> None:
    # IAM is GLOBAL: the control Region (us-east-1) holds it; the other Region's reader must NOT be
    # queried (enumerating a global type per-Region would double-count it).
    east = _reader((IAM_ROLE, "role-1"))
    west = _reader()
    scope = ReadScope(
        coverages=(TypeCoverage(IAM_ROLE, RegionScope.GLOBAL, Listability.DIRECTLY_LISTABLE),),
        allowed_regions=("us-east-1", "eu-west-1"),
    )

    reads = read_closed_world({"us-east-1": east, "eu-west-1": west}, scope)

    assert {read.identifier for read in reads} == {"role-1"}
    assert west.client.invoked_operations == set()  # the non-control Region's reader is untouched


def test_fails_closed_on_an_unlistable_in_scope_type() -> None:
    # An UNLISTABLE in-scope type cannot be enumerated, so closed-world cannot be proven for it ->
    # fail closed (quarantine the type), never assume it holds no resources (vector #15).
    scope = ReadScope(
        coverages=(TypeCoverage(S3, RegionScope.REGIONAL, Listability.UNLISTABLE),),
        allowed_regions=("us-east-1",),
    )

    with pytest.raises(ClosedWorldError, match="unlistable"):
        read_closed_world({"us-east-1": _reader()}, scope)


def test_fails_closed_on_a_context_listable_in_scope_type() -> None:
    # A CONTEXT_LISTABLE type needs proven recursive parent enumeration (not built) -- so it too
    # fails closed, not flat-enumerated -- else a child hides under an unenumerated parent.
    scope = ReadScope(
        coverages=(TypeCoverage(S3, RegionScope.REGIONAL, Listability.CONTEXT_LISTABLE),),
        allowed_regions=("us-east-1",),
    )

    with pytest.raises(ClosedWorldError, match="context"):
        read_closed_world({"us-east-1": _reader()}, scope)


def test_fails_closed_on_a_required_region_with_no_reader() -> None:
    # The scope requires eu-west-1 but no reader is supplied -> that Region cannot be enumerated ->
    # fail closed. Silently skipping it would let an extra resource hide there (vector #15).
    scope = ReadScope(
        coverages=(TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),),
        allowed_regions=("us-east-1", "eu-west-1"),
    )

    with pytest.raises(ClosedWorldError, match="eu-west-1"):
        read_closed_world({"us-east-1": _reader()}, scope)  # eu-west-1 reader missing


def test_enumerates_the_union_across_types_and_regions() -> None:
    # The exhaustive picture: every in-scope type x its Regions, unioned. A regional bucket in each
    # Region + a global role in the control Region -> all three surface.
    east = _reader((S3, "bucket-east"), (IAM_ROLE, "role-1"))
    west = _reader((S3, "bucket-west"))
    scope = ReadScope(
        coverages=(
            TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),
            TypeCoverage(IAM_ROLE, RegionScope.GLOBAL, Listability.DIRECTLY_LISTABLE),
        ),
        allowed_regions=("us-east-1", "eu-west-1"),
    )

    reads = read_closed_world({"us-east-1": east, "eu-west-1": west}, scope)

    assert {read.identifier for read in reads} == {"bucket-east", "bucket-west", "role-1"}
