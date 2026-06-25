"""Tiny builders for the Terraform-adapter tests -- each test reads as intent, not boilerplate."""

from __future__ import annotations

from assayops_adapter_terraform import BridgeRegistry, DeployedResourceRead, TypeBridge

ADDRESS_TAG = "assayops:address"

# AWS::S3::Bucket readOnly (server-computed) properties: they vary across identical deploys, so the
# adapter drops them (the CloudFormation schema `readOnlyProperties`).
S3_READ_ONLY = frozenset(
    {"Arn", "DomainName", "DualStackDomainName", "RegionalDomainName", "WebsiteURL"}
)


def s3_registry() -> BridgeRegistry:
    """A registry supporting AWS::S3::Bucket (the synthetic engine-validation type, #75)."""
    registry = BridgeRegistry()
    registry.register(TypeBridge(type_name="AWS::S3::Bucket", read_only_paths=S3_READ_ONLY))
    return registry


def tag(key: str, value: str) -> dict[str, str]:
    return {"Key": key, "Value": value}


def s3_read(
    address: str | None = "primary_bucket",
    identifier: str = "assayops-a1b2c3d4",
    *,
    tags: dict[str, str] | None = None,
    **properties: object,
) -> DeployedResourceRead:
    """An AWS::S3::Bucket read tagged with `address` (``None`` omits it), plus user `tags`."""
    tag_list: list[dict[str, str]] = []
    if address is not None:
        tag_list.append(tag(ADDRESS_TAG, address))
    if tags:
        tag_list += [tag(key, value) for key, value in tags.items()]
    props: dict[str, object] = dict(properties)
    if tag_list:
        props["Tags"] = tag_list
    return DeployedResourceRead(
        type_name="AWS::S3::Bucket", identifier=identifier, properties=props
    )
