"""The adapter's input envelope -- already-enumerated, settled Cloud Control read records.

The read harness (#30/#141) enumerates deployed state and hands the adapter these records, which it
only normalizes (it never enumerates or reads a plan/state file -- T1). ``properties`` is
open, untrusted data (``dict[str, object]``, the ``unknown`` equivalent, never ``Any``); its values
are validated when they flow into the diff-ir ``NormalizedResource``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeployedResourceRead:
    """One settled Cloud Control ``GetResource`` result for a deployed resource."""

    # The CloudFormation type, e.g. "AWS::S3::Bucket" -- Cloud Control returns CFN types regardless
    # of the provisioning tool, so this is never a Terraform type name.
    type_name: str
    # The physical Cloud Control identifier -- diagnostics only, NEVER the diff address. The address
    # is the `assayops:address` tag, never a physical id or natural key (founder T2 rule).
    identifier: str
    # The parsed resource model (``json.loads`` of the GetResource ``Properties`` string).
    properties: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class UnreadableResource:
    """A resource the read harness could not settle -- a per-record coverage gap.

    The adapter fails closed on it (never a silent reward -- vector #15); a distinct input variant,
    so the harness can hand the adapter a complete, fail-closed picture of one episode.
    """

    type_name: str
    identifier: str
    reason: str


# The adapter consumes a stream of settled reads and explicit coverage gaps.
DeployedRead = DeployedResourceRead | UnreadableResource
