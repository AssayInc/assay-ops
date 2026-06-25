"""The `assayops:address` bridge fails closed -- an unresolvable address never a silent reward."""

from __future__ import annotations

import pytest
from factories import ADDRESS_TAG, s3_read, s3_registry, tag

from assayops_adapter_terraform import AddressBridgeError, DeployedResourceRead, normalize

_WRONG_SHAPE_TAG_PROPERTIES: list[dict[str, object]] = [
    {"Tags": "not-a-list"},
    {"Tags": [{"Key": "assayops:address"}]},  # missing Value
    {"Tags": [{"Value": "primary_bucket"}]},  # missing Key
    {"Tags": [{"Key": "assayops:address", "Value": 7}]},  # non-string Value
    {"Tags": ["primary_bucket"]},  # entry is not a {Key, Value} object
]


def _normalize(read: DeployedResourceRead) -> object:
    return normalize([read], s3_registry())


def _s3(tags: list[dict[str, str]]) -> DeployedResourceRead:
    return DeployedResourceRead(
        type_name="AWS::S3::Bucket", identifier="assayops-a1b2c3d4", properties={"Tags": tags}
    )


def test_missing_address_tag_fails_closed() -> None:
    with pytest.raises(AddressBridgeError, match="assayops:address"):
        _normalize(s3_read(address=None, BucketName="b"))


def test_duplicate_address_tag_fails_closed() -> None:
    with pytest.raises(AddressBridgeError, match="exactly one"):
        _normalize(_s3([tag(ADDRESS_TAG, "a"), tag(ADDRESS_TAG, "b")]))


@pytest.mark.parametrize(
    "bad", ["", " ", "has space", "tab\there", "new\nline", "$type", "ünïcode", "a" * 300]
)
def test_malformed_address_value_fails_closed(bad: str) -> None:
    # Untrusted value: whitespace, control/non-ASCII, a `$` IR marker, over-long -> fail closed.
    with pytest.raises(AddressBridgeError):
        _normalize(_s3([tag(ADDRESS_TAG, bad)]))


@pytest.mark.parametrize("wrong_key", ["Assayops:Address", "ASSAYOPS:ADDRESS", "assayops:Address"])
def test_case_wrong_address_tag_is_not_the_bridge_tag(wrong_key: str) -> None:
    # The bridge key is exactly `assayops:address`; a case variant is missing-or-reserved.
    with pytest.raises(AddressBridgeError):
        _normalize(_s3([tag(wrong_key, "primary_bucket")]))


def test_reserved_assayops_namespace_tag_fails_closed() -> None:
    with pytest.raises(AddressBridgeError, match="reserved"):
        _normalize(_s3([tag(ADDRESS_TAG, "primary_bucket"), tag("assayops:secret", "x")]))


@pytest.mark.parametrize("bad_properties", _WRONG_SHAPE_TAG_PROPERTIES)
def test_wrong_shape_tag_property_fails_closed(bad_properties: dict[str, object]) -> None:
    read = DeployedResourceRead(
        type_name="AWS::S3::Bucket", identifier="assayops-a1b2c3d4", properties=bad_properties
    )
    with pytest.raises(AddressBridgeError):
        _normalize(read)
