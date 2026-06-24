"""The open ``properties`` channel must stay deterministic + JSON-safe (the golden is hashed).

A builder is trusted corpus code, but a bug there must **fail closed**, never silently produce a
non-deterministic or information-lossy golden (AC1 determinism + vector #15). The two ways the open
``dict[str, object]`` field could betray that, past every other test (which use empty properties):
a ``set`` serializes in ``PYTHONHASHSEED``-order (non-deterministic bytes across processes), and a
non-finite float is silently coerced to JSON ``null`` by ``model_dump`` (silent loss).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from synthetic import make_task

from assayops_verifier.golden import GoldenContext, GoldenError, GoldenRegistry
from assayops_verifier.models import GoldenResource


def _resource_with(value: object) -> GoldenResource:
    return GoldenResource(address="a", type="AWS::S3::Bucket", properties={"x": value})


def test_set_valued_property_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _resource_with({"alpha", "bravo"})


def test_non_finite_float_property_is_rejected() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError):
            _resource_with(bad)


def test_oversized_int_property_is_rejected() -> None:
    # Beyond ±(2^53−1): rfc8785 can't represent it, so the golden would build but fail to digest.
    with pytest.raises(ValidationError):
        _resource_with(2**53)


def test_nested_json_properties_are_accepted() -> None:
    resource = _resource_with({"nested": {"k": [1, "two", True, None]}})
    assert resource.properties == {"x": {"nested": {"k": [1, "two", True, None]}}}


def test_builder_emitting_an_invalid_property_fails_closed_as_golden_error() -> None:
    def bad_builder(_ctx: GoldenContext) -> list[GoldenResource]:
        return [
            GoldenResource(
                address="a", type="AWS::EC2::SecurityGroup", properties={"ports": {80, 443}}
            )
        ]

    registry = GoldenRegistry()
    registry.register("bad", bad_builder)
    with pytest.raises(GoldenError):
        registry.generate(make_task(task_id="bad"), "seed")
