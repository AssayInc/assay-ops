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


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_float_property_is_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        _resource_with(bad)


def test_oversized_int_property_is_rejected() -> None:
    # Beyond ±(2^53−1): rfc8785 can't represent it, so the golden would build but fail to digest.
    with pytest.raises(ValidationError):
        _resource_with(2**53)


def test_surrogate_string_value_is_rejected() -> None:
    # A lone surrogate is a valid str but not UTF-8-encodable → rfc8785 raises (a raw digest leak).
    with pytest.raises(ValidationError):
        _resource_with("\ud800")


def test_surrogate_string_key_is_rejected() -> None:
    # Distinct surrogate keys both dump to the replacement char → one digest (a content-address
    # collision). Reject them at the boundary.
    with pytest.raises(ValidationError):
        GoldenResource(address="a", type="AWS::S3::Bucket", properties={"\ud800": 1})


def test_dict_subclass_property_is_rejected() -> None:
    # A dict subclass can override iteration to show the validator clean items while model_dump
    # serializes different underlying storage — reject subclasses; require exact JSON types.
    class SneakyDict(dict[str, object]):
        pass

    with pytest.raises(ValidationError):
        _resource_with(SneakyDict({"a": 1}))


def test_list_subclass_property_is_rejected() -> None:
    class SneakyList(list[object]):
        pass

    with pytest.raises(ValidationError):
        _resource_with(SneakyList([1]))


def test_int_enum_property_is_rejected_as_a_non_plain_int() -> None:
    import enum

    class Color(enum.IntEnum):
        RED = 1

    with pytest.raises(ValidationError):
        _resource_with(Color.RED)


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
