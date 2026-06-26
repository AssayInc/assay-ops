"""E2-1 (#30) + E2-6 (#141): the account-B Cloud Control read harness -- reads + transient routing.

Drives ``DeployedStateReader`` against a faithful, recording fake of the boto3 cloudcontrol client
(``cloud_control_fakes``): GetResource parsing, the absent / genuine-unreadable / transient
classification (#141 scope 1), per-type list+get with the list/get-race routed through the 7A
determinism layer, and -- the moat -- that the harness performs READ operations only (DECISIONS.md
section 1/8, T1; vectors #1 and #10).

The #30 skeleton deferred the transient/genuine *classification* to #141: a throttle / 5xx /
timeout is TRANSIENT (raised as ``TransientGradeError`` so the K-run re-attempts it, never scored 0
on the spot -- the false-negative the deterministic-verification skill names); only a GENUINE
failure (AccessDenied / validation / unparseable) fails closed to ``UnreadableResource``. So the
#30 "throttle -> UnreadableResource" tests are updated here to the #141 routing.
"""

from __future__ import annotations

import pytest
from assayops_adapter_terraform import DeployedResourceRead, UnreadableResource
from assayops_replay import TransientGradeError, TransientKind
from botocore.exceptions import ClientError
from cloud_control_fakes import FakeCloudControlClient

from assayops_verifier.read import DeployedStateReader, _identifiers_in_page, _properties_of

S3 = "AWS::S3::Bucket"


def test_read_resource_parses_get_resource_into_a_deployed_resource_read() -> None:
    client = FakeCloudControlClient(
        {
            (S3, "bucket-1"): {
                "BucketName": "bucket-1",
                "VersioningConfiguration": {"Status": "Enabled"},
            }
        }
    )

    read = DeployedStateReader(client).read_resource(S3, "bucket-1")

    assert read == DeployedResourceRead(
        type_name=S3,
        identifier="bucket-1",
        properties={"BucketName": "bucket-1", "VersioningConfiguration": {"Status": "Enabled"}},
    )


def test_read_resource_returns_none_for_an_absent_resource() -> None:
    # ResourceNotFoundException at the single-read level means "not in the deployed set" (absent).
    # The list/get RACE (an enumerated id that then reads absent) is the EVENTUAL_CONSISTENCY case,
    # handled in read_type where the "it was listed" context lives -- not here.
    reader = DeployedStateReader(FakeCloudControlClient())

    assert reader.read_resource(S3, "missing") is None


def test_read_resource_routes_a_throttle_to_a_transient() -> None:
    # #141 scope 1: a post-(boto3-adaptive)-retry throttle is TRANSIENT, not a wrong answer. The
    # read raises TransientGradeError(INFRA) so the K-run re-attempts it -- never scored 0 on the
    # spot.
    client = FakeCloudControlClient(unreadable={(S3, "throttled")})

    with pytest.raises(TransientGradeError) as exc_info:
        DeployedStateReader(client).read_resource(S3, "throttled")
    assert exc_info.value.kind is TransientKind.INFRA


def test_read_resource_routes_a_network_error_to_a_transient() -> None:
    # A connection/timeout (BotoCoreError, not a ClientError) is also TRANSIENT (botocore's own
    # retry classification) -> TransientGradeError(INFRA), never an on-the-spot fail-closed 0.
    client = FakeCloudControlClient(network_error={(S3, "offline")})

    with pytest.raises(TransientGradeError) as exc_info:
        DeployedStateReader(client).read_resource(S3, "offline")
    assert exc_info.value.kind is TransientKind.INFRA


def test_read_resource_fails_closed_to_unreadable_on_a_genuine_error() -> None:
    # AccessDenied is GENUINE (an isolation alarm, never masked into a retry) ->
    # UnreadableResource, so the adapter fails closed downstream (UnreadableResourceError); never a
    # silent reward (vector #15).
    client = FakeCloudControlClient(access_denied={(S3, "denied")})

    read = DeployedStateReader(client).read_resource(S3, "denied")

    assert read == UnreadableResource(
        type_name=S3, identifier="denied", reason="AccessDeniedException"
    )


def test_read_resource_fails_closed_to_unreadable_on_unparseable_properties() -> None:
    # A response whose Properties is not JSON is a genuine coverage gap (not transient) -> fail
    # closed.
    client = FakeCloudControlClient(malformed={(S3, "garbled")})

    read = DeployedStateReader(client).read_resource(S3, "garbled")

    assert isinstance(read, UnreadableResource)
    assert read.identifier == "garbled"


def test_list_resource_identifiers_enumerates_every_page() -> None:
    # Discovery via the paginator across a NextToken boundary (page_size forces multiple pages).
    client = FakeCloudControlClient({(S3, "a"): {}, (S3, "b"): {}, (S3, "c"): {}}, page_size=2)

    identifiers = DeployedStateReader(client).list_resource_identifiers(S3)

    assert sorted(identifiers) == ["a", "b", "c"]
    assert (
        "list_resources" in client.invoked_operations
    )  # used the paginated read op, not a raw loop


def test_list_resource_identifiers_routes_a_throttle_to_a_transient() -> None:
    # A throttle DURING enumeration is transient -- route it through the K-run, never read it as
    # "no extra resources" (a truncated enumeration that fails OPEN would hide an extra, vector
    # #15).
    client = FakeCloudControlClient(list_throttle={S3})

    with pytest.raises(TransientGradeError) as exc_info:
        DeployedStateReader(client).list_resource_identifiers(S3)
    assert exc_info.value.kind is TransientKind.INFRA


def test_list_resource_identifiers_fails_closed_on_a_genuine_list_error() -> None:
    # A genuine list error (e.g. InvalidRequest) FAILS CLOSED (propagates) -- never a partial/empty
    # enumeration that would read as "no extra resources".
    client = FakeCloudControlClient(list_error={S3})

    with pytest.raises(ClientError):
        DeployedStateReader(client).list_resource_identifiers(S3)


def test_read_type_lists_then_gets_each_resource() -> None:
    client = FakeCloudControlClient(
        {(S3, "b1"): {"BucketName": "b1"}, (S3, "b2"): {"BucketName": "b2"}}
    )

    reads = DeployedStateReader(client).read_type(S3)

    assert sorted(reads, key=lambda r: r.identifier) == [
        DeployedResourceRead(type_name=S3, identifier="b1", properties={"BucketName": "b1"}),
        DeployedResourceRead(type_name=S3, identifier="b2", properties={"BucketName": "b2"}),
    ]


def test_read_type_carries_a_genuine_unreadable_through_fail_closed() -> None:
    # An enumerable-but-genuinely-unreadable resource is surfaced as an UnreadableResource (the
    # adapter then fails closed) -- never dropped, which would silently reward a blind spot (vector
    # #15).
    client = FakeCloudControlClient(
        {(S3, "ok"): {"BucketName": "ok"}}, access_denied={(S3, "blind")}
    )

    reads = DeployedStateReader(client).read_type(S3)

    assert (
        UnreadableResource(type_name=S3, identifier="blind", reason="AccessDeniedException")
        in reads
    )


def test_read_type_routes_a_list_get_race_to_eventual_consistency() -> None:
    # A resource list_resources returned but get_resource then reports absent (a list/get race) is
    # NOT "absent" (dropping it could hide an extra, #15): it routes through the determinism layer
    # as an EVENTUAL_CONSISTENCY transient, re-attempted by the K-run -- never silently dropped.
    client = FakeCloudControlClient(vanished={(S3, "ghost")})

    with pytest.raises(TransientGradeError) as exc_info:
        DeployedStateReader(client).read_type(S3)
    assert exc_info.value.kind is TransientKind.EVENTUAL_CONSISTENCY


def test_the_reader_performs_read_operations_only() -> None:
    # The moat (DECISIONS.md section 1/8, T1): the verifier READS deployed state; it never writes,
    # mutates, or runs agent code -- so vector #1 (fs/state write to the grader) and vector #10
    # (A->B assume) fail by construction. The recording fake forbids any non-read op, so this
    # asserts the harness's ACTUAL behavior, not the fake's.
    client = FakeCloudControlClient({(S3, "b1"): {"BucketName": "b1"}})

    DeployedStateReader(client).read_type(S3)

    assert client.invoked_operations <= {"get_resource", "get_paginator", "list_resources"}


def test_identifiers_in_page_treats_absent_resource_descriptions_as_empty() -> None:
    # An absent ResourceDescriptions is the empty-result shape (the AWS array is omittable when
    # empty; matches infra-local) -> []. Failing closed on it would false-crash the empty account.
    assert _identifiers_in_page({"TypeName": S3}) == []


def test_identifiers_in_page_fails_closed_on_a_malformed_page() -> None:
    # A present-but-malformed shape fails closed; truncation (a NextToken) the paginator follows.
    with pytest.raises(ValueError, match="malformed page"):
        _identifiers_in_page({"ResourceDescriptions": "not-a-list"})
    with pytest.raises(ValueError, match="malformed page"):
        _identifiers_in_page("not-a-dict")


def test_properties_of_fails_closed_on_valid_json_that_is_not_an_object() -> None:
    # Properties that parse as JSON but are not a JSON object are unusable -> fail closed (None).
    response = {"ResourceDescription": {"Identifier": "x", "Properties": "[1, 2, 3]"}}

    assert _properties_of(response) is None


def test_properties_of_fails_closed_on_deeply_nested_json() -> None:
    # json.loads raises RecursionError (NOT ValueError) on deeply-nested JSON; the read path must
    # fail closed (None -> UnreadableResource), never crash the worker (a DoS / fail-closed break).
    deep = "[" * 100_000 + "]" * 100_000
    response = {"ResourceDescription": {"Identifier": "x", "Properties": deep}}

    assert _properties_of(response) is None
