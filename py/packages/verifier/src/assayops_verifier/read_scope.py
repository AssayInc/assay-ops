"""E2-6 (#141): the verifier-side read-coverage matrix (DECISIONS.md section 1 "E3-4 read coverage").

The closed-world ``deployed set == golden set`` check (vector #15) is only sound if the read path
enumerates the deployed account **exhaustively**. ``list_resources`` is per-``TypeName``/per-Region, so
"exhaustive" is defined by a per-type matrix: which **in-scope** types exist, which Regions each is
enumerated in (GLOBAL services at one control Region; REGIONAL services at every allowed Region), and
whether each is **directly listable** at all. This module is that matrix.

It is the verifier's codification of the #80 read-coverage matrix's *read-side* facets (Region scope,
listability, write-only properties), distinct from the Terraform adapter's ``BridgeRegistry`` (the
*normalization* facets: tag property + readOnly drop-list). A real-AWS regeneration tool
(``cloudformation describe-type``, scope 4) populates both from one source; that tool is T7-gated and
deferred (it needs a live account). In-repo this is hand-declared + exercised on synthetic fixtures.

Fails closed: an in-scope type with no coverage entry raises (the read path can never prove closed-world
for a type it has no coverage for). An UNLISTABLE / CONTEXT_LISTABLE type is enumerated-fail-closed by
the read harness (#141 scope 2) -- it cannot be flat-enumerated, so it is quarantined, never assumed
empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from assayops_verifier.models import GoldenTarget

# Where a GLOBAL service is enumerated. IAM / CloudFront / Route53 expose one control-Region endpoint
# (us-east-1); enumerating a global type per-Region would double-count it. AWS-fixed, not agent input.
_GLOBAL_CONTROL_REGION = "us-east-1"


class UnknownReadCoverageError(ValueError):
    """No read-coverage entry for an in-scope type -- fail closed (never assume it is empty/absent).

    The closed-world predicate (``deployed set == golden set``, vector #15) is unsound for a type the
    verifier has no coverage matrix for: it cannot know the type's Region scope or whether it is even
    listable, so it cannot prove no extra resource of that type exists. Quarantine, never silently pass.
    """


class UnreadableGoldenPropertyError(ValueError):
    """A golden asserts a property ``GetResource`` does not return (a write-only property) -- ungradable.

    A CORRECT deploy of such a task reads back WITHOUT the write-only property, so the reward core would
    score it a false 0. The per-property gate catches this at corpus-authoring time and quarantines the
    task (DECISIONS.md section 1; the issue's "quarantine or add a service-specific fallback"), rather
    than admitting a task that can never legitimately score reward 1.
    """


class RegionScope(StrEnum):
    """How a type's resources are distributed across Regions -- the per-type enumeration matrix."""

    # A regional service: a resource can exist in ANY allowed Region, so enumerate every one of them.
    REGIONAL = "regional"
    # A global service (IAM / Route53 / CloudFront): one control Region holds all of them.
    GLOBAL = "global"


class Listability(StrEnum):
    """Whether ``list_resources(TypeName)`` can flat-enumerate a type (DECISIONS.md section 1).

    Only ``DIRECTLY_LISTABLE`` types can be enumerated by the closed-world read path; the other two are
    **quarantined** -- never assumed to hold no resources, which would silently hide an extra (#15).
    """

    # ``list_resources`` returns a flat ``(TypeName) -> identifiers`` list -- closed-world-enumerable.
    DIRECTLY_LISTABLE = "directly_listable"
    # ``list_resources`` needs parent/context ``ResourceModel`` fields (a child under an unenumerated
    # parent). Sound enumeration requires proving recursive parent enumeration -- not built; quarantine.
    CONTEXT_LISTABLE = "context_listable"
    # No ``list`` handler at all -- cannot be enumerated, so cannot be proven closed-world; quarantine.
    UNLISTABLE = "unlistable"


@dataclass(frozen=True)
class TypeCoverage:
    """The verifier's read-coverage for one in-scope CloudFormation type."""

    type_name: str
    region_scope: RegionScope
    listability: Listability
    # Properties Cloud Control ``GetResource`` does NOT return (the schema ``writeOnlyProperties``). A
    # golden that asserts one is ungradable -- a correct deploy would read back without it and score a
    # false 0 -- so the per-property gate (``assert_golden_readable``) quarantines such a task. Top-level
    # property names; nested write-only paths are handled when a corpus type needs them (YAGNI for now).
    write_only_paths: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ReadScope:
    """The in-scope read-coverage matrix the closed-world enumeration walks -- fail-closed on a gap."""

    coverages: tuple[TypeCoverage, ...]
    # The Regions a REGIONAL type is enumerated across (the agent's allowed deploy Regions). A GLOBAL
    # type is enumerated at its control Region instead (which need not be one of these).
    allowed_regions: tuple[str, ...]
    global_control_region: str = _GLOBAL_CONTROL_REGION

    def __post_init__(self) -> None:
        if not self.allowed_regions:
            raise ValueError("a ReadScope must declare at least one allowed region")
        type_names = [coverage.type_name for coverage in self.coverages]
        duplicates = sorted({name for name in type_names if type_names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate type coverages in the read scope: {duplicates}")

    def coverage(self, type_name: str) -> TypeCoverage:
        """The coverage entry for ``type_name``, or fail closed (``UnknownReadCoverageError``)."""
        for coverage in self.coverages:
            if coverage.type_name == type_name:
                return coverage
        raise UnknownReadCoverageError(
            f"no read-coverage entry for in-scope type {type_name!r}: a type with no coverage cannot "
            "be proven closed-world (vector #15); quarantine it, never assume it is empty"
        )

    def regions_for(self, coverage: TypeCoverage) -> tuple[str, ...]:
        """The Regions to enumerate ``coverage``'s type in -- the per-type Region matrix.

        REGIONAL -> every allowed Region (an extra could hide in any unscanned one). GLOBAL -> only the
        control Region (enumerating per-Region would double-count a global resource).
        """
        if coverage.region_scope is RegionScope.GLOBAL:
            return (self.global_control_region,)
        return self.allowed_regions


def assert_golden_readable(golden: GoldenTarget, scope: ReadScope) -> None:
    """The per-asserted-property coverage gate (#141 scope 3) -- fail closed on an ungradable golden.

    For each golden resource, every asserted top-level property must be one ``GetResource`` actually
    returns: a property in the type's ``write_only_paths`` is omitted by Cloud Control, so a correct
    deploy reads back without it and would score a false 0. Such a golden is quarantined
    (``UnreadableGoldenPropertyError``). A type with no read-coverage entry fails closed too
    (``UnknownReadCoverageError`` from ``scope.coverage``). Authoring-time -- run when admitting a task,
    not in the hot grade path.
    """
    for resource in golden.resources:
        coverage = scope.coverage(resource.type)
        unreadable = sorted(frozenset(resource.properties) & coverage.write_only_paths)
        if unreadable:
            raise UnreadableGoldenPropertyError(
                f"golden resource {resource.address!r} (type {resource.type!r}) asserts write-only "
                f"propert{'y' if len(unreadable) == 1 else 'ies'} {unreadable} that Cloud Control "
                "GetResource does not return; a correct deploy would read back without it and score a "
                "false 0 -- quarantine the task or add a service-specific read fallback (vector #15)"
            )
