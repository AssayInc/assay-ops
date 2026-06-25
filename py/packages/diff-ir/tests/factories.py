"""Tiny builders for the normalized-state IR -- each test reads as intent, not boilerplate."""

from __future__ import annotations

from assayops_contracts import Resource

from assayops_diff_ir import GradeOutcome, NormalizedResource, NormalizedState, Provenance


def res(address: str, rtype: str = "AWS::S3::Bucket", **properties: object) -> NormalizedResource:
    return NormalizedResource(address=address, type=rtype, properties=dict(properties))


def deployed(*resources: NormalizedResource) -> NormalizedState:
    return NormalizedState(provenance=Provenance.DEPLOYED_READ, resources=resources)


def golden(*resources: NormalizedResource) -> NormalizedState:
    return NormalizedState(provenance=Provenance.GOLDEN_TARGET, resources=resources)


def by_address(outcome: GradeOutcome) -> dict[str, Resource]:
    return {r.address: r for r in outcome.diff.resources}
