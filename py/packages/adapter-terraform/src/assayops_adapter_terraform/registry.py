"""The per-type bridge registry -- the codified #80 read-coverage matrix.

A ``TypeBridge`` is the adapter's knowledge of one supported CloudFormation type: where tags live
(the schema ``tagging.tagProperty``) and which properties are AWS-computed and dropped (the schema
``readOnlyProperties``). Registering a type asserts the #80 matrix marked it readable and an
``infra-local`` smoke proved Cloud Control returns the
``assayops:address`` tag for it (founder T2 rule). An unregistered type fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass

from assayops_adapter_terraform.errors import UnsupportedResourceTypeError


@dataclass(frozen=True)
class TypeBridge:
    """How to bridge + normalize one supported CloudFormation type."""

    type_name: str
    # The schema ``tagging.tagProperty`` -- the property holding the tag list. Defaults to "Tags"; a
    # type whose schema names it differently overrides it (proven per type).
    tag_property: str = "Tags"
    # The schema ``readOnlyProperties`` (top-level names): AWS-computed, varying across identical
    # deploys (Arn/DomainName/...). Dropped before the diff, else a correct deploy scores a nonzero
    # diff -- a nondeterministic reward. A frozenset is an immutable, frozen-safe default.
    read_only_paths: frozenset[str] = frozenset()
    # Order-insensitive set normalization (policy statements, ingress rules) is deferred to the CDK
    # adapter (#66), which has the nested set-bearing types and designs it JCS-aligned.


class BridgeRegistry:
    """Resolves a CloudFormation type to its bridge; fail-closed on an unregistered type."""

    def __init__(self) -> None:
        self._bridges: dict[str, TypeBridge] = {}

    def register(self, bridge: TypeBridge) -> None:
        if bridge.type_name in self._bridges:
            raise ValueError(f"a bridge is already registered for type {bridge.type_name!r}")
        self._bridges[bridge.type_name] = bridge

    def get(self, type_name: str) -> TypeBridge:
        try:
            return self._bridges[type_name]
        except KeyError:
            raise UnsupportedResourceTypeError(
                f"no bridge registered for resource type {type_name!r}: unsupported types fail "
                "closed (the #80 read-coverage matrix); never silently rewarded"
            ) from None


# The AWS::S3::Bucket schema ``readOnlyProperties`` -- server-computed attributes that vary across
# deploys. Its ``assayops:address`` tag-return is proven by the ``infra-local`` Cloud Control smoke.
_S3_BUCKET = TypeBridge(
    type_name="AWS::S3::Bucket",
    read_only_paths=frozenset(
        {"Arn", "DomainName", "DualStackDomainName", "RegionalDomainName", "WebsiteURL"}
    ),
)


def default_registry() -> BridgeRegistry:
    """The Phase-1 default registry: types whose Cloud Control tag-return ``infra-local`` proves.

    The Terraform A-spike engine supports ``AWS::S3::Bucket`` (the synthetic type, #75). Other
    corpus-readable types register here as their per-type smoke lands.
    """
    registry = BridgeRegistry()
    registry.register(_S3_BUCKET)
    return registry
