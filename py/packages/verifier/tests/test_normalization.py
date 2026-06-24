"""Normalization — the golden is in canonical order (sorted by address), so the content address is
independent of the builder's emission order (a determinism requirement: the same expected state must
always canonicalize to the same bytes regardless of how a builder happened to list it).
"""

from __future__ import annotations

from collections.abc import Callable

from synthetic import make_task

from assayops_verifier.golden import GoldenContext, GoldenRegistry, golden_digest
from assayops_verifier.models import GoldenResource


def _emit(addresses: list[str]) -> Callable[[GoldenContext], list[GoldenResource]]:
    def builder(_ctx: GoldenContext) -> list[GoldenResource]:
        return [GoldenResource(address=address, type="AWS::S3::Bucket") for address in addresses]

    return builder


def test_resources_are_sorted_by_address() -> None:
    registry = GoldenRegistry()
    registry.register("unordered", _emit(["zebra", "alpha", "mike"]))

    golden = registry.generate(make_task(task_id="unordered"), "seed")

    assert [resource.address for resource in golden.resources] == ["alpha", "mike", "zebra"]


def test_content_address_is_independent_of_builder_emission_order() -> None:
    registry = GoldenRegistry()
    registry.register("forward", _emit(["alpha", "mike", "zebra"]))
    registry.register("reverse", _emit(["zebra", "mike", "alpha"]))

    forward = registry.generate(make_task(task_id="forward"), "seed")
    reverse = registry.generate(make_task(task_id="reverse"), "seed")

    assert golden_digest(forward) == golden_digest(reverse)


def test_property_key_order_does_not_affect_the_address() -> None:
    # JCS sorts object keys, so the content address is independent of property insertion order.
    def forward_keys(_ctx: GoldenContext) -> list[GoldenResource]:
        return [GoldenResource(address="a", type="AWS::S3::Bucket", properties={"x": 1, "y": 2})]

    def reverse_keys(_ctx: GoldenContext) -> list[GoldenResource]:
        return [GoldenResource(address="a", type="AWS::S3::Bucket", properties={"y": 2, "x": 1})]

    registry = GoldenRegistry()
    registry.register("fwd", forward_keys)
    registry.register("rev", reverse_keys)
    fwd = registry.generate(make_task(task_id="fwd"), "seed")
    rev = registry.generate(make_task(task_id="rev"), "seed")
    assert golden_digest(fwd) == golden_digest(rev)
