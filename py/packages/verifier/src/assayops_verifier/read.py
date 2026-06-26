"""E2-1 (#30): the account-B deployed-state read harness -- the verifier skeleton's read path.

DECISIONS.md section 1/8, T1/1C. The write-isolated verifier runs in account B and reads DEPLOYED
resource state read-only via Cloud Control (``get_resource`` / ``list_resources``) through the
injected client's credentials, which determine the target account. A B->A cross-account read obtains
account-A credentials by STS ``AssumeRole`` into a READ-ONLY role in account A and builds the client
with them (#33/E8) -- never an A->B path (vector #10). It NEVER runs the agent's
``terraform plan`` / ``cdk synth`` or reads a ``.tfstate`` / plan file (vectors #1/#4/#5): the only
injected Cloud Control client -- ground truth the agent cannot forge.

The read surface is exactly Cloud Control ``get_resource`` + ``list_resources`` (IAM
``cloudformation:GetResource`` / ``cloudformation:ListResources``; #141 scopes least-privilege to
these). A throttle / un-propagated read is transient (the injected client's ``Config(retries=...)``
handles it, never a hand-rolled loop -- DECISIONS.md 7A); a genuine read failure fails CLOSED to an
``UnreadableResource``, so the adapter never rewards a blind spot (vector #15).

Scope: the read-and-grade skeleton. Deferred: the closed-world ``deployed set == golden set``
enumeration (exhaustive / paginated / Region-aware, fail-closed on truncation), the per-property
coverage gate, and the 7A transient/genuine classifier are #141; the cross-account read-only role
assumption is #33 (its SCP allow-list #53, the E8 role infra #52); CloudFormation drift is the CDK
path (#66); the reward-record / ledger handoff is #32. Terraform is graded via Cloud Control only
(#80, section 1).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from assayops_adapter_terraform import (
    BridgeRegistry,
    DeployedResourceRead,
    UnreadableResource,
    normalize,
)
from assayops_adapter_terraform.models import DeployedRead  # union alias (not re-exported)
from assayops_contracts import TaskSpec
from assayops_diff_ir import GradeOutcome
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from assayops_verifier.golden import GoldenRegistry
from assayops_verifier.grading import grade_deployment


@dataclass(frozen=True)
class DeployedStateReader:
    """A read-only wrapper over an account-B boto3 Cloud Control client.

    The injected ``client`` carries the credentials that decide which account is read. For a single
    account / LocalStack that is account-B's own; a B->A cross-account read uses account-A read-only
    credentials obtained by STS ``AssumeRole`` into a read-only role in A (#33/E8) -- never an A->B
    path (vector #10). The reader holds no credentials of its own.
    """

    client: BaseClient

    def read_resource(
        self, type_name: str, identifier: str
    ) -> DeployedResourceRead | UnreadableResource | None:
        """Read one resource's deployed state.

        ``None`` if absent (``ResourceNotFoundException``): an absent golden resource is a drift,
        not a coverage gap. An ``UnreadableResource`` if the read fails closed -- any post-retry
        ``ClientError`` or ``BotoCoreError`` (throttle / access-denied / network / timeout), or an
        unparseable response. Which failures are transient-retryable vs genuine -- the 7A classifier
        -- is #141; boto3's ``Config(retries=...)`` retries the transient ones first.
        """
        try:
            response: object = self.client.get_resource(TypeName=type_name, Identifier=identifier)
        except self.client.exceptions.ResourceNotFoundException:
            return None
        except (ClientError, BotoCoreError) as error:
            return UnreadableResource(
                type_name=type_name, identifier=identifier, reason=_failure_reason(error)
            )
        properties = _properties_of(response)
        if properties is None:
            return UnreadableResource(
                type_name=type_name,
                identifier=identifier,
                reason="unparseable Cloud Control GetResource response",
            )
        return DeployedResourceRead(
            type_name=type_name, identifier=identifier, properties=properties
        )

    def list_resource_identifiers(self, type_name: str) -> list[str]:
        """Enumerate a type's identifiers via the Cloud Control ``list_resources`` paginator.

        Basic single-Region discovery. The closed-world ``deployed set == golden set`` completeness
        -- exhaustive / Region-aware enumeration, and failing closed on a truncated or errored list
        -- is #141; a list-phase API error here propagates (fail-closed: no reward).
        """
        paginator = self.client.get_paginator("list_resources")
        identifiers: list[str] = []
        for page in paginator.paginate(TypeName=type_name):
            identifiers.extend(_identifiers_in_page(page))
        return identifiers

    def read_types(self, type_names: Iterable[str]) -> list[DeployedRead]:
        """Read each in-scope type's deployed resources: list, then get each (fail-closed per read).

        Every enumerated resource is surfaced -- a successful read, or an ``UnreadableResource`` so
        the adapter fails closed. A resource ``list_resources`` returned but ``get_resource`` then
        reports absent (a list/get race) is a coverage gap, NOT "absent": dropping it could hide an
        extra resource (vector #15), so it too fails closed.
        """
        reads: list[DeployedRead] = []
        for type_name in type_names:
            for identifier in self.list_resource_identifiers(type_name):
                read = self.read_resource(type_name, identifier)
                if read is None:
                    read = UnreadableResource(
                        type_name=type_name,
                        identifier=identifier,
                        reason="listed but absent on read (list/get inconsistency)",
                    )
                reads.append(read)
        return reads


def verify_deployment(
    reader: DeployedStateReader,
    registry: GoldenRegistry,
    task: TaskSpec,
    seed: str,
    type_names: Iterable[str],
    bridge_registry: BridgeRegistry | None = None,
) -> GradeOutcome:
    """Read deployed state, normalize it, and grade it against the regenerated golden.

    The verifier skeleton's end-to-end path (DECISIONS.md section 1, T1): boto3 Cloud Control read
    (#30) -> ``normalize`` to the DEPLOYED_READ IR (#35) -> ``grade_deployment`` regenerates the
    golden from (task, seed) and grades it (#31) -> reward in {0, 1}. ``type_names`` is the in-scope
    set to read; the closed-world ``deployed set == golden set`` completeness over it is #141. Fails
    closed (never a silent reward) on an unreadable or unsupported deployed resource (vector #15).
    """
    reads = reader.read_types(type_names)
    deployed = normalize(reads, bridge_registry)
    return grade_deployment(registry, task, seed, deployed)


def _failure_reason(error: BaseException) -> str:
    """A read-failure reason: a ``ClientError``'s AWS error code, else the exception class name."""
    response: object = getattr(error, "response", None)
    if isinstance(response, dict):
        meta = response.get("Error")
        if isinstance(meta, dict):
            code = meta.get("Code")
            if isinstance(code, str):
                return code
    return type(error).__name__


def _properties_of(response: object) -> dict[str, object] | None:
    """Narrow an untyped ``get_resource`` response to its parsed ``Properties`` dict.

    Returns ``None`` (fail closed) on any unexpected shape: the boto3 response is open data narrowed
    to ``dict[str, object]`` at the boundary, never trusted as-is.
    """
    if not isinstance(response, dict):
        return None
    description = response.get("ResourceDescription")
    if not isinstance(description, dict):
        return None
    raw = description.get("Properties")
    if not isinstance(raw, str):
        return None
    try:
        parsed: object = json.loads(raw)
    except (ValueError, RecursionError):
        # RecursionError (NOT a ValueError) on deeply-nested JSON: fail closed, never crash the
        # worker (a DoS / fail-closed-contract break). Mirrors the adapter's deep-nesting guard.
        return None
    if not isinstance(parsed, dict):
        return None
    properties: dict[str, object] = parsed
    return properties


def _identifiers_in_page(page: object) -> list[str]:
    """Narrow an untyped ``list_resources`` page to its identifiers (fail closed on a bad shape).

    An absent ``ResourceDescriptions`` is the AWS empty-result shape (the array may be omitted when
    the type has no resources; ``infra-local`` assumes the same) -> ``[]``; failing closed on it
    would false-crash the normal empty-account case. A present-but-non-list value fails CLOSED.
    Failing closed on a TRUNCATED enumeration (a ``NextToken`` the paginator follows) is the
    closed-world concern -> #141, not this per-page shape check.
    """
    if not isinstance(page, dict):
        raise ValueError(f"Cloud Control list_resources returned a malformed page: {page!r}")
    descriptions = page.get("ResourceDescriptions", [])
    if not isinstance(descriptions, list):
        raise ValueError(f"Cloud Control list_resources returned a malformed page: {page!r}")
    identifiers: list[str] = []
    for description in descriptions:
        if not isinstance(description, dict):
            raise ValueError(f"malformed Cloud Control resource description: {description!r}")
        identifier = description.get("Identifier")
        if not isinstance(identifier, str):
            raise ValueError(
                f"Cloud Control resource description has no string Identifier: {description!r}"
            )
        identifiers.append(identifier)
    return identifiers
