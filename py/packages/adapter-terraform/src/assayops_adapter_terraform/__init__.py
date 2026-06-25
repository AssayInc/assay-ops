"""AssayOps Terraform adapter (DECISIONS.md 6A / T2) -- the deployed side of the 6A diff.

Normalizes the verifier's read-only B-side Cloud Control deployed-state read into the diff-ir
``NormalizedState(DEPLOYED_READ)`` (#34), which the shared reward core ``grade`` diffs against the
regenerated golden (#75). The IR shape it emits is the engine the CDK adapter (#66) conforms to.

**Pure normalization, never a read.** No boto3 call; never runs ``terraform``, loads providers, or
reads the agent's ``.tfstate`` / plan JSON -- those are untrusted agent code/data, the T1 surface.
It consumes already-enumerated Cloud Control records; enumeration and closed-world coverage are
the read harness's job (#30/#141/#53).
"""

from assayops_adapter_terraform.adapter import ADDRESS_TAG, normalize
from assayops_adapter_terraform.errors import (
    AdapterError,
    AddressBridgeError,
    DuplicateAddressError,
    UnreadableResourceError,
    UnsupportedResourceTypeError,
)
from assayops_adapter_terraform.models import DeployedResourceRead, UnreadableResource
from assayops_adapter_terraform.registry import BridgeRegistry, TypeBridge, default_registry

__all__ = [
    "ADDRESS_TAG",
    "AdapterError",
    "AddressBridgeError",
    "BridgeRegistry",
    "DeployedResourceRead",
    "DuplicateAddressError",
    "TypeBridge",
    "UnreadableResource",
    "UnreadableResourceError",
    "UnsupportedResourceTypeError",
    "default_registry",
    "normalize",
]
