"""E2-1 (#30) + E2-6 (#141): the account-B deployed-state read harness + closed-world read coverage.

DECISIONS.md section 1/8, T1/1C. The write-isolated verifier runs in account B and reads DEPLOYED
resource state read-only via Cloud Control (``get_resource`` / ``list_resources``) through the
injected client's credentials, which determine the target account. A B->A cross-account read
obtains account-A credentials by STS ``AssumeRole`` into a READ-ONLY role in account A and builds
the client with them (#33/E8) -- never an A->B path (vector #10). It NEVER runs the agent's
``terraform plan`` / ``cdk synth`` or reads a ``.tfstate`` / plan file (vectors #1/#4/#5): the only
injected Cloud Control client -- ground truth the agent cannot forge.

The read surface is exactly Cloud Control ``get_resource`` + ``list_resources`` (IAM
``cloudformation:GetResource`` / ``cloudformation:ListResources``; #141 scopes least-privilege to
these). The injected client's ``Config(retries=...)`` absorbs SDK-level throttles/5xx WITHIN a read
(boto3 adaptive, never a hand-rolled loop). A failure that surfaces past that is **classified** by
the 7A policy (#141 scope 1): a transient (throttle / 5xx / timeout / list-get race) raises
``TransientGradeError`` so the K-run re-attempts it (never scored 0 on the spot -- the
false-negative); a genuine failure fails CLOSED to ``UnreadableResource`` (the adapter then
raises -- never a silent reward, #15).

This module owns the read path: the per-resource read (``read_resource``), the per-type enumeration
in one Region (``read_type``), and the **closed-world** ``deployed set == golden set`` walk over
the in-scope type x Region matrix (``read_closed_world``, #141 scope 2 -- exhaustive / paginated /
fail-closed). The per-property coverage gate is ``read_scope.assert_golden_readable`` (#141 scope
3); the K-run verdict that drives ``reproduce`` over this read is ``verify.verify`` (#141 scope 1).
Deferred (real-AWS / a live account): the cross-account read-only role assumption is #33 (its SCP
allow-list #53, the E8 role infra #52); the real-AWS coverage-matrix regeneration tool +
``describe-type`` IAM derivation is T7-gated; CloudFormation drift is the CDK path (#66); the
reward-record / ledger handoff is #32. Terraform is graded via Cloud Control only (#80, section 1).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
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
from assayops_replay import TransientGradeError, TransientKind, transient_kind
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from assayops_verifier.golden import GoldenRegistry
from assayops_verifier.grading import grade_deployment
from assayops_verifier.read_scope import Listability, ReadScope


@dataclass(frozen=True)
class DeployedStateReader:
    """A read-only wrapper over an account-B boto3 Cloud Control client.

    The injected ``client`` carries the credentials that decide which account is read. For a single
    account / LocalStack that is account-B's own; a B->A cross-account read uses account-A
    read-only credentials obtained by STS ``AssumeRole`` into a read-only role in A (#33/E8) --
    never an A->B path (vector #10). The reader holds no credentials of its own.
    """

    client: BaseClient

    def read_resource(
        self, type_name: str, identifier: str
    ) -> DeployedResourceRead | UnreadableResource | None:
        """Read one resource's deployed state, classifying a read failure (7A; #141 scope 1).

        ``None`` if absent (``ResourceNotFoundException``) -- at the single-read level "not in the
        deployed set". (The list/get RACE -- an enumerated id that reads back absent -- is the
        EVENTUAL_CONSISTENCY case ``read_type`` raises, where the "it was listed" context lives.) A
        post-(boto3-adaptive)-retry ``ClientError`` / ``BotoCoreError`` is routed by the 7A
        classifier: a **transient** (throttle / 5xx / timeout) raises ``TransientGradeError`` so
        the K-run re-attempts it -- never scored 0 on the spot (the false-negative the
        deterministic-verification skill names). A **genuine** failure (AccessDenied / validation),
        or an unparseable response, fails closed to ``UnreadableResource`` (the adapter then
        raises; AccessDenied is an isolation alarm, never masked into a retry).
        """
        try:
            response: object = self.client.get_resource(TypeName=type_name, Identifier=identifier)
        except self.client.exceptions.ResourceNotFoundException:
            return None
        except (ClientError, BotoCoreError) as error:
            kind = transient_kind(error)
            if kind is not None:
                raise TransientGradeError(kind, _failure_reason(error)) from error
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

        The paginator follows every ``NextToken`` to exhaustion -- so a normal return is the
        COMPLETE identifier set, never a truncated page (no ``MaxItems`` cap that would silently
        stop). A throttle / 5xx DURING enumeration is a **transient** -- routed through the 7A
        K-run (``TransientGradeError``), never read as "no extra resources" (a truncated
        enumeration must never fail OPEN, vector #15; #141 scope 2). A **genuine** list error (an
        unlistable type, an invalid request) FAILS CLOSED -- it propagates, never a partial/empty
        enumeration. A malformed page raises in ``_identifiers_in_page`` (also fail-closed).
        """
        paginator = self.client.get_paginator("list_resources")
        identifiers: list[str] = []
        try:
            for page in paginator.paginate(TypeName=type_name):
                identifiers.extend(_identifiers_in_page(page))
        except (ClientError, BotoCoreError) as error:
            kind = transient_kind(error)
            if kind is not None:
                raise TransientGradeError(kind, _failure_reason(error)) from error
            raise
        return identifiers

    def read_type(self, type_name: str) -> list[DeployedRead]:
        """Read one type's deployed resources in this reader's Region: list, then get each.

        Every enumerated resource is surfaced -- a successful read, or an ``UnreadableResource`` so
        the adapter fails closed (never dropped, which would hide a blind spot -- vector #15). A
        resource ``list_resources`` returned but ``get_resource`` then reads back absent (a race)
        is NOT "absent": dropping it could hide an extra resource, so it is routed through the 7A
        determinism layer as an ``EVENTUAL_CONSISTENCY`` transient (the K-run re-attempts it)
        rather than settled here. The closed-world walk across types and Regions is
        ``read_closed_world``.
        """
        reads: list[DeployedRead] = []
        for identifier in self.list_resource_identifiers(type_name):
            read = self.read_resource(type_name, identifier)
            if read is None:
                raise TransientGradeError(
                    TransientKind.EVENTUAL_CONSISTENCY,
                    f"{identifier!r} (type {type_name!r}) was listed but read back absent "
                    "(list/get race)",
                )
            reads.append(read)
        return reads


class ClosedWorldError(ValueError):
    """Closed-world enumeration cannot be proven exhaustive -- fail closed, never a silent reward.

    Raised for a structural gap the read path cannot fill: an in-scope type that cannot be
    flat-enumerated (UNLISTABLE / CONTEXT_LISTABLE), or a required Region with no reader. Either
    would leave a blind spot an extra resource could hide in (vector #15), so the episode fails
    closed rather than grading against an incomplete deployed set. A GENUINE failure, not transient.
    """


def read_closed_world(
    readers: Mapping[str, DeployedStateReader], scope: ReadScope
) -> list[DeployedRead]:
    """Enumerate the in-scope account EXHAUSTIVELY over the type x Region matrix (#141 scope 2).

    The closed-world ``deployed set == golden set`` predicate (vector #15) is sound only over a
    COMPLETE deployed set, so this reads every in-scope type in every Region its coverage allows
    (REGIONAL -> all allowed Regions; GLOBAL -> the control Region), via that Region's reader, and
    unions the results. A type that cannot be flat-enumerated (UNLISTABLE / CONTEXT_LISTABLE), or a
    required Region with no reader, is a blind spot an extra could hide in -- so it FAILS CLOSED
    (``ClosedWorldError``) rather than enumerate a partial account. A list / get transient surfaces
    from ``read_type`` as ``TransientGradeError`` (the 7A K-run re-attempts it upstream); the reward
    core flags any *enumerated* extra (an address in deployed not in golden) as a diff.
    """
    reads: list[DeployedRead] = []
    for coverage in scope.coverages:
        if coverage.listability is not Listability.DIRECTLY_LISTABLE:
            raise ClosedWorldError(
                f"in-scope type {coverage.type_name!r} is {coverage.listability.value} -- it "
                "cannot be flat-enumerated, so closed-world cannot be proven; quarantine it (#15)"
            )
        for region in scope.regions_for(coverage):
            reader = readers.get(region)
            if reader is None:
                raise ClosedWorldError(
                    f"no reader for required Region {region!r} (type {coverage.type_name!r}): "
                    "that Region cannot be enumerated, so an extra resource there could hide -- "
                    "fail closed (#15)"
                )
            reads.extend(reader.read_type(coverage.type_name))
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
    golden from (task, seed) and grades it (#31) -> reward in {0, 1}. ``type_names`` is the
    in-scope set to read in this reader's single Region. Fails closed (never a silent reward) on an
    unreadable or unsupported deployed resource (vector #15).

    This is the single-Region #30 path. The sound closed-world entry -- exhaustive type x Region
    enumeration + the 7A K-run + the per-property gate -- is ``assayops_verifier.verify.verify``.
    """
    reads = [read for type_name in type_names for read in reader.read_type(type_name)]
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

    Returns ``None`` (fail closed) on any unexpected shape: the boto3 response is open data
    narrowed to ``dict[str, object]`` at the boundary, never trusted as-is.
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
