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


def test_the_default_registry_bridges_an_iam_role_read() -> None:
    # AWS::IAM::Role joins the default registry (its Cloud Control tag-return is proven by the
    # infra-local smoke). Schema facts: readOnlyProperties = Arn + RoleId (dropped -- they vary
    # across identical deploys); tagProperty = Tags.
    read = DeployedResourceRead(
        type_name="AWS::IAM::Role",
        identifier="assayops-role",
        properties={
            "RoleName": "assayops-role",
            "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": []},
            "MaxSessionDuration": 3600,
            "Path": "/",
            "Arn": "arn:aws:iam::000000000000:role/assayops-role",
            "RoleId": "AROAEXAMPLE",
            "Tags": [tag(ADDRESS_TAG, "ci_role")],
        },
    )
    [resource] = normalize([read]).resources
    assert resource.address == "ci_role"
    assert "Arn" not in resource.properties
    assert "RoleId" not in resource.properties
    assert resource.properties["MaxSessionDuration"] == 3600


def test_the_default_registry_bridges_a_kms_key_read() -> None:
    # AWS::KMS::Key joins the default registry (tag-return proven by the infra-local smoke).
    # Schema facts: readOnlyProperties = Arn + KeyId (dropped); tagProperty = Tags.
    read = DeployedResourceRead(
        type_name="AWS::KMS::Key",
        identifier="6135f98c-87de-4309-b85a-cf90d231f177",
        properties={
            "Enabled": True,
            "EnableKeyRotation": False,
            "KeySpec": "SYMMETRIC_DEFAULT",
            "Arn": "arn:aws:kms:us-east-1:000000000000:key/6135f98c",
            "KeyId": "6135f98c-87de-4309-b85a-cf90d231f177",
            "Tags": [tag(ADDRESS_TAG, "audit_key")],
        },
    )
    [resource] = normalize([read]).resources
    assert resource.address == "audit_key"
    assert "Arn" not in resource.properties
    assert "KeyId" not in resource.properties
    assert resource.properties["EnableKeyRotation"] is False
