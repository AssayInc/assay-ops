"""E2-1 (#30): the account-B Cloud Control read harness -- unit behavior + the read-only moat.

Drives ``DeployedStateReader`` against a faithful, recording fake of the boto3 cloudcontrol client
(``cloud_control_fakes``): GetResource parsing, the absent/unreadable fail-closed classification,
paginated discovery, the ``role_arn`` B->A read-only hook, and -- the moat -- that the harness
performs READ operations only (DECISIONS.md section 1/8, T1; vectors #1 and #10).
"""

from __future__ import annotations

import pytest
from assayops_adapter_terraform import DeployedResourceRead, UnreadableResource
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
    # ResourceNotFoundException means the resource is not in the deployed set: a golden resource
    # that is absent is a `removed` drift, never a coverage gap.
    reader = DeployedStateReader(FakeCloudControlClient())

    assert reader.read_resource(S3, "missing") is None


def test_read_resource_fails_closed_to_unreadable_on_a_client_error() -> None:
    # A post-retry throttle / network / service error fails CLOSED to an UnreadableResource (never a
    # silent reward -- vector #15); the adapter turns it into UnreadableResourceError downstream.
    client = FakeCloudControlClient(unreadable={(S3, "throttled")})

    read = DeployedStateReader(client).read_resource(S3, "throttled")

    assert read == UnreadableResource(
        type_name=S3, identifier="throttled", reason="ThrottlingException"
    )


def test_read_resource_fails_closed_to_unreadable_on_unparseable_properties() -> None:
    # A response whose Properties is not JSON is a coverage gap, not a silent skip.
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


def test_read_types_lists_then_gets_each_in_scope_type() -> None:
    client = FakeCloudControlClient(
        {(S3, "b1"): {"BucketName": "b1"}, (S3, "b2"): {"BucketName": "b2"}}
    )

    reads = DeployedStateReader(client).read_types([S3])

    assert sorted(reads, key=lambda r: r.identifier) == [
        DeployedResourceRead(type_name=S3, identifier="b1", properties={"BucketName": "b1"}),
        DeployedResourceRead(type_name=S3, identifier="b2", properties={"BucketName": "b2"}),
    ]


def test_read_types_carries_an_unreadable_resource_through_fail_closed() -> None:
    # An enumerable-but-unreadable resource is surfaced as an UnreadableResource (the adapter then
    # fails closed) -- never dropped, which would silently reward a blind spot.
    client = FakeCloudControlClient({(S3, "ok"): {"BucketName": "ok"}}, unreadable={(S3, "blind")})

    reads = DeployedStateReader(client).read_types([S3])

    assert (
        UnreadableResource(type_name=S3, identifier="blind", reason="ThrottlingException") in reads
    )


def test_role_arn_is_threaded_as_the_b_to_a_read_only_hook() -> None:
    # Cross-account reads pass a READ-ONLY role ARN to Cloud Control (a B->A read; never an A->B
    # assume, vector #10). With no role_arn (LocalStack / single account) none is sent.
    role = "arn:aws:iam::111111111111:role/assayops-verifier-readonly"
    client = FakeCloudControlClient({(S3, "b1"): {"BucketName": "b1"}})

    DeployedStateReader(client, role_arn=role).read_types([S3])

    get_calls = [kwargs for op, kwargs in client.invoked if op == "get_resource"]
    list_calls = [kwargs for op, kwargs in client.invoked if op == "list_resources"]
    assert all(call["RoleArn"] == role for call in get_calls)
    assert all(call["RoleArn"] == role for call in list_calls)


def test_the_reader_performs_read_operations_only() -> None:
    # The moat (DECISIONS.md section 1/8, T1): the verifier READS deployed state; it never writes,
    # mutates, or runs agent code -- so vector #1 (fs/state write to the grader) and vector #10
    # (A->B assume) fail by construction. The recording fake forbids any non-read op, so this
    # asserts the harness's ACTUAL behavior, not the fake's.
    client = FakeCloudControlClient({(S3, "b1"): {"BucketName": "b1"}})

    DeployedStateReader(client).read_types([S3])

    assert client.invoked_operations <= {"get_resource", "get_paginator", "list_resources"}


def test_read_resource_fails_closed_to_unreadable_on_a_botocore_error() -> None:
    # A post-retry connection/timeout is a BotoCoreError (NOT a ClientError); it must still fail
    # closed to an UnreadableResource, never escape raw (the read path's fail-closed contract).
    client = FakeCloudControlClient(network_error={(S3, "offline")})

    read = DeployedStateReader(client).read_resource(S3, "offline")

    assert read == UnreadableResource(
        type_name=S3, identifier="offline", reason="EndpointConnectionError"
    )


def test_read_types_surfaces_a_listed_then_absent_resource_as_unreadable() -> None:
    # A resource list_resources returned but get_resource then reports absent (a list/get race) is a
    # coverage gap, not "absent": fail closed, never drop (a drop could hide an extra, #15).
    client = FakeCloudControlClient(vanished={(S3, "ghost")})

    reads = DeployedStateReader(client).read_types([S3])

    assert reads == [
        UnreadableResource(
            type_name=S3,
            identifier="ghost",
            reason="listed but absent on read (list/get inconsistency)",
        )
    ]


def test_identifiers_in_page_fails_closed_on_a_malformed_page() -> None:
    # A page missing ResourceDescriptions must fail closed, NOT default to empty -- a fail-open
    # would hide deployed resources (vector #15). A non-list ResourceDescriptions also fails closed.
    with pytest.raises(ValueError, match="malformed page"):
        _identifiers_in_page({"TypeName": S3})
    with pytest.raises(ValueError, match="malformed page"):
        _identifiers_in_page({"ResourceDescriptions": "not-a-list"})


def test_properties_of_fails_closed_on_valid_json_that_is_not_an_object() -> None:
    # Properties that parse as JSON but are not a JSON object are unusable -> fail closed (None).
    response = {"ResourceDescription": {"Identifier": "x", "Properties": "[1, 2, 3]"}}

    assert _properties_of(response) is None
