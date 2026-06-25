"""Content-address integrity — ``golden_digest`` pins a canonical golden even though Pydantic
``frozen`` is shallow (the open ``properties`` dict stays mutable). The resource set is a tuple
(cannot be emptied/extended), and ``golden_digest`` re-validates so post-generation tampering (a
verifier-internal bug, never agent-reachable) fails closed, not a misleading address.
"""

from __future__ import annotations

import pytest
from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_verifier.golden import GoldenContext, GoldenError, GoldenRegistry, golden_digest
from assayops_verifier.models import GoldenResource, GoldenTarget


def _golden() -> GoldenTarget:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry.generate(make_task(), "seed")


def test_resources_is_an_immutable_tuple() -> None:
    # A tuple cannot be emptied/extended after generation (frozen alone would leave a list mutable).
    assert isinstance(_golden().resources, tuple)


def test_tampering_a_property_fails_closed_at_digest() -> None:
    golden = _golden()
    # frozen is shallow: the properties dict is still mutable. Inject a non-deterministic value.
    golden.resources[0].properties["injected"] = {"a", "b"}
    with pytest.raises(GoldenError):
        golden_digest(golden)  # re-validation rejects the set — fail closed, no misleading address


def test_builder_mutating_a_resource_after_construction_fails_closed() -> None:
    # A resource valid at construction, mutated to an invalid value before return. Pydantic doesn't
    # re-validate nested instances, so GoldenTarget re-checks each resource's properties.
    def mutating_builder(_ctx: GoldenContext) -> list[GoldenResource]:
        resource = GoldenResource(address="a", type="AWS::S3::Bucket", properties={"ok": 1})
        resource.properties["bad"] = {1, 2}  # mutate the open dict after its validator ran
        return [resource]

    registry = GoldenRegistry()
    registry.register("mut", mutating_builder)
    with pytest.raises(GoldenError):
        registry.generate(make_task(task_id="mut"), "seed")


def test_tampering_to_a_cycle_fails_closed_at_digest() -> None:
    # A cyclic property would RecursionError in model_dump; golden_digest wraps it as GoldenError
    # rather than leaking a raw RecursionError.
    golden = _golden()
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    golden.resources[0].properties["cyclic"] = cyclic
    with pytest.raises(GoldenError):
        golden_digest(golden)


def test_tampering_with_a_model_property_fails_closed_at_digest() -> None:
    # A BaseModel leaf: a model_dump-then-validate check would coerce it to a dict and miss it. The
    # live re-check before canonicalizing catches the non-JSON leaf.
    golden = _golden()
    golden.resources[0].properties["model"] = GoldenResource(address="x", type="AWS::S3::Bucket")
    with pytest.raises(GoldenError):
        golden_digest(golden)
