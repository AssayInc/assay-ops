"""Record-level fail-closed: the adapter never silently drops or mis-grades a read."""

from __future__ import annotations

import pytest
from factories import ADDRESS_TAG, s3_read, s3_registry, tag

from assayops_adapter_terraform import (
    AdapterError,
    DeployedResourceRead,
    DuplicateAddressError,
    UnreadableResource,
    UnsupportedResourceTypeError,
    normalize,
)


def test_unsupported_type_fails_closed() -> None:
    # A type with no registered bridge is never silently normalized (AC4 / the #80 matrix).
    read = DeployedResourceRead(
        type_name="AWS::EC2::Instance",
        identifier="i-123",
        properties={"Tags": [tag(ADDRESS_TAG, "web")]},
    )
    with pytest.raises(UnsupportedResourceTypeError, match="AWS::EC2::Instance"):
        normalize([read], s3_registry())


def test_unreadable_record_fails_closed() -> None:
    # A resource the harness could not read is a coverage gap -> reward must not be 1 (vector #15).
    unreadable = UnreadableResource(type_name="AWS::S3::Bucket", identifier="b", reason="throttled")
    with pytest.raises(AdapterError, match="unreadable"):
        normalize([unreadable], s3_registry())


def test_duplicate_logical_address_fails_closed() -> None:
    reads = [s3_read("dup", identifier="b1"), s3_read("dup", identifier="b2")]
    with pytest.raises(DuplicateAddressError, match="dup"):
        normalize(reads, s3_registry())


def test_a_non_json_property_value_fails_closed() -> None:
    # Defense-in-depth: a real read is `json.loads` output, but `properties` is open `object`; a
    # value outside exact JSON fails closed with an adapter diagnostic.
    read = s3_read("primary_bucket", BadProp={1, 2, 3})  # a set is not JSON
    with pytest.raises(AdapterError):
        normalize([read], s3_registry())


def test_a_deeply_nested_property_fails_closed() -> None:
    # A crafted deep-nested property must stay inside the AdapterError family, never escape as a
    # RecursionError (a fail-closed-contract break + a verifier-crash DoS).
    nested: object = "leaf"
    for _ in range(2000):
        nested = {"k": nested}
    read = s3_read("primary_bucket", BadProp=nested)
    with pytest.raises(AdapterError):
        normalize([read], s3_registry())
