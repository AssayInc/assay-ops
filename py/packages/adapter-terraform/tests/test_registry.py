"""The per-type bridge registry -- the codified #80 read-coverage matrix."""

from __future__ import annotations

import pytest
from factories import ADDRESS_TAG, tag

from assayops_adapter_terraform import BridgeRegistry, DeployedResourceRead, TypeBridge, normalize


def test_a_non_default_tag_property_is_read() -> None:
    # A type whose CFN schema names its tagProperty something other than "Tags" is read there.
    registry = BridgeRegistry()
    registry.register(TypeBridge(type_name="Custom::Thing", tag_property="TagSet"))
    read = DeployedResourceRead(
        type_name="Custom::Thing",
        identifier="t1",
        properties={"TagSet": [tag(ADDRESS_TAG, "thing")], "Size": "large"},
    )
    [resource] = normalize([read], registry).resources
    assert resource.address == "thing"
    assert resource.properties == {"Size": "large"}  # the bridge tag (only TagSet entry) is dropped


def test_registering_a_type_twice_is_rejected() -> None:
    registry = BridgeRegistry()
    registry.register(TypeBridge(type_name="AWS::S3::Bucket"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(TypeBridge(type_name="AWS::S3::Bucket"))
