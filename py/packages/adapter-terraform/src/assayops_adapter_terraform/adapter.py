"""``normalize`` -- the Terraform adapter's only entry (DECISIONS.md 6A / T2 / T1).

Turns settled, already-enumerated Cloud Control deployed-state reads into the diff-ir
``NormalizedState(DEPLOYED_READ)`` the shared reward core grades against the golden. Reads only the
records it is given -- no boto3, no ``terraform``/provider run, no ``.tfstate``/plan read (T1, the
moat). Fails closed on any read it cannot vouch for; never silently drops one (vector #15).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from assayops_diff_ir import NormalizedResource, NormalizedState, Provenance
from pydantic import ValidationError

from assayops_adapter_terraform.errors import (
    AdapterError,
    AddressBridgeError,
    DuplicateAddressError,
    UnreadableResourceError,
)
from assayops_adapter_terraform.models import DeployedRead, UnreadableResource
from assayops_adapter_terraform.registry import BridgeRegistry, TypeBridge, default_registry

# The reserved AssayOps tag namespace + its one bridge key. Case-sensitive (founder T2 rule).
# The tag value is untrusted deployed-state data.
RESERVED_TAG_PREFIX = "assayops:"
ADDRESS_TAG = "assayops:address"
# A logical address (the golden's diff key): a bounded ASCII identifier. A malformed value
# (whitespace, control/non-ASCII, a `$` IR marker, over-long) fails closed -- never an address.
_ADDRESS_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_./-]{0,255}\Z")


def normalize(
    reads: Iterable[DeployedRead], registry: BridgeRegistry | None = None
) -> NormalizedState:
    """Normalize Cloud Control reads to ``NormalizedState(DEPLOYED_READ)``, or fail closed."""
    bridges = registry if registry is not None else default_registry()
    resources = [_normalize_one(read, bridges) for read in reads]
    _reject_duplicate_addresses(resources)
    # Sort by address so the output is canonical / order-independent (the core sorts too).
    resources.sort(key=lambda resource: resource.address)
    return NormalizedState(provenance=Provenance.DEPLOYED_READ, resources=tuple(resources))


def _reject_duplicate_addresses(resources: list[NormalizedResource]) -> None:
    """Fail closed if two reads resolve to the same logical address.

    They would collapse in the diff's address map (a lost resource, a wrong grade). The diff-ir
    ``NormalizedState`` rejects duplicates too; this raises the adapter's typed diagnostic first.
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for resource in resources:
        if resource.address in seen:
            duplicates.add(resource.address)
        seen.add(resource.address)
    if duplicates:
        raise DuplicateAddressError(
            f"two or more deployed resources resolve to the same address: {sorted(duplicates)}"
        )


def _normalize_one(read: DeployedRead, registry: BridgeRegistry) -> NormalizedResource:
    if isinstance(read, UnreadableResource):
        raise UnreadableResourceError(
            f"resource {read.identifier!r} (type {read.type_name!r}) is unreadable: {read.reason}; "
            "an unreadable resource fails closed, never silently rewarded (vector #15)"
        )
    bridge = registry.get(read.type_name)  # UnsupportedResourceTypeError on an unregistered type
    tags = _parse_tag_list(read.properties.get(bridge.tag_property), bridge.tag_property)
    address = _resolve_address(tags, bridge.tag_property)
    properties = _normalize_properties(read.properties, tags, bridge)
    try:
        return NormalizedResource(address=address, type=read.type_name, properties=properties)
    except ValidationError as exc:
        # A real read is `json.loads` output, but `properties` is open `object`; a value the diff-ir
        # validator rejects (non-exact-JSON, NaN/inf, oversized int) fails closed here.
        raise AdapterError(
            f"resource {address!r} (type {read.type_name!r}) has a non-normalizable property: {exc}"
        ) from exc


def _parse_tag_list(raw: object, tag_property: str) -> list[tuple[str, str]]:
    """Parse a CloudFormation tag property (``[{Key, Value}, ...]``) into (key, value) pairs.

    Fail closed on any other shape -- the value is untrusted deployed-state data.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise AddressBridgeError(
            f"the {tag_property!r} tag property must be a list of {{Key, Value}} tags, "
            f"got {type(raw).__name__}"
        )
    pairs: list[tuple[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise AddressBridgeError(f"each {tag_property!r} tag must be a {{Key, Value}} object")
        key = entry.get("Key")
        value = entry.get("Value")
        if not isinstance(key, str) or not isinstance(value, str):
            raise AddressBridgeError(
                f"each {tag_property!r} tag must have a string Key and a string Value"
            )
        pairs.append((key, value))
    return pairs


def _resolve_address(tags: list[tuple[str, str]], tag_property: str) -> str:
    """Resolve the single ``assayops:address`` value.

    Fail closed on a missing/duplicate/malformed value, or a stray reserved ``assayops:*`` tag.
    """
    reserved = sorted(
        {key for key, _ in tags if key.startswith(RESERVED_TAG_PREFIX) and key != ADDRESS_TAG}
    )
    if reserved:
        raise AddressBridgeError(
            f"reserved AssayOps tag(s) {reserved} in {tag_property!r} are not permitted "
            "(the assayops: namespace is reserved)"
        )
    addresses = [value for key, value in tags if key == ADDRESS_TAG]
    if not addresses:
        raise AddressBridgeError(
            f"a supported resource must carry exactly one {ADDRESS_TAG!r} tag; none found"
        )
    if len(addresses) > 1:
        raise AddressBridgeError(
            f"a resource must carry exactly one {ADDRESS_TAG!r} tag; found {len(addresses)}"
        )
    address = addresses[0]
    if not _ADDRESS_RE.match(address):
        raise AddressBridgeError(
            f"malformed logical address {address!r} in the {ADDRESS_TAG!r} tag"
        )
    return address


def _normalize_properties(
    properties: dict[str, object], tags: list[tuple[str, str]], bridge: TypeBridge
) -> dict[str, object]:
    """Drop the tag property + server-filled readOnly properties; re-attach the user tags, sorted.

    ``_resolve_address`` has already rejected any reserved ``assayops:*`` tag, so the remaining
    non-address tags are user tags -- intent the golden may assert, kept (sorted; the core compares
    lists order-sensitively). With no user tags left, the tag property is dropped entirely.
    """
    normalized = {
        key: value
        for key, value in properties.items()
        if key != bridge.tag_property and key not in bridge.read_only_paths
    }
    for path in bridge.set_paths:
        if path in normalized:
            normalized[path] = _sort_set(normalized[path])
    user_tags = [{"Key": key, "Value": value} for key, value in tags if key != ADDRESS_TAG]
    if user_tags:
        normalized[bridge.tag_property] = sorted(
            user_tags, key=lambda entry: (entry["Key"], entry["Value"])
        )
    return normalized


def _sort_set(value: object) -> object:
    """Order-normalize a declared set-valued property so a reordered-but-equal collection yields the
    same IR. The core compares lists by JCS bytes (order matters), so only the adapter sorts a set.
    Keyed by canonical JSON for a total order.
    """
    if not isinstance(value, list):
        return value
    try:
        return sorted(value, key=lambda element: json.dumps(element, sort_keys=True))
    except TypeError as exc:
        raise AdapterError(f"a set-valued property has a non-JSON element: {exc}") from exc
