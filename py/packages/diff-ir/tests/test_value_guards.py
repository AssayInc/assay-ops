"""E3-1 (#34) — value guards + type-strict comparison (review-hardening).

The reward core must never grade a real divergence as in-sync. Python `==` collapses `True == 1` and
`1 == 1.0`, and `NaN != NaN`; a property value of `None` is ambiguous with "absent" under the sparse
serialization. So the normalized IR fails closed on values that break determinism or the digest
(non-finite floats, `None`, `$`-reserved keys), and the diff compares values **type-strictly**
(`bool` != `int` != `float`) so no value-type coercion can forge a reward 1.
"""

from __future__ import annotations

import dataclasses

import pytest
from assayops_contracts import Change, Reward
from factories import by_address, deployed, golden, res

from assayops_diff_ir import NormalizedResource, grade

# --- type-strict comparison: no value-type coercion can forge a reward 1 (F1/F3) ---


def test_bool_and_int_property_values_are_not_equal() -> None:
    # golden requires the integer 1; deployed reads back the boolean True -- a real divergence.
    outcome = grade(deployed(res("r", flag=True)), golden(res("r", flag=1)))
    assert outcome.reward is Reward.number_0
    assert by_address(outcome)["r"].change is Change.modified


def test_int_and_float_property_values_are_not_equal() -> None:
    outcome = grade(deployed(res("r", n=90.0)), golden(res("r", n=90)))
    assert outcome.reward is Reward.number_0


def test_bool_and_int_nested_in_a_dict_are_not_equal() -> None:
    outcome = grade(
        deployed(res("r", cfg={"BlockPublicAcls": 1})),
        golden(res("r", cfg={"BlockPublicAcls": True})),
    )
    assert outcome.reward is Reward.number_0


# --- fail closed on values that break the digest / sparse serialization (F2/F4/F5) ---


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_normalized_resource_rejects_non_finite_float(bad: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        res("r", metric=bad)


def test_normalized_resource_rejects_non_finite_float_nested() -> None:
    with pytest.raises(ValueError, match="finite"):
        res("r", cfg={"threshold": float("nan")})


def test_normalized_resource_rejects_none_property_value() -> None:
    # Absent = omit the key; a present None is ambiguous with "absent" under exclude_none.
    with pytest.raises(ValueError, match="None"):
        res("r", maybe=None)


def test_normalized_resource_rejects_dollar_prefixed_property_key() -> None:
    # `$`-prefixed paths are reserved by the IR (the $type marker); a real $type would collide.
    with pytest.raises(ValueError, match=r"\$"):
        NormalizedResource(address="r", type="AWS::S3::Bucket", properties={"$type": "x"})


def test_normalized_resource_rejects_non_string_nested_object_key() -> None:
    # {1: ...} and {True: ...} collide under Python dict-key equality -> a false reward 1.
    with pytest.raises(ValueError, match="string"):
        res("r", cfg={1: "x"})


def test_normalized_resource_rejects_a_non_json_property_value() -> None:
    with pytest.raises(ValueError, match="JSON"):
        res("r", bad=(1, 2))


def test_normalized_resource_rejects_a_scalar_subclass_with_overloaded_eq() -> None:
    # A bool/int/float/str SUBCLASS passes isinstance and can overload __eq__ to forge a reward 1.
    class _Sneaky(int):
        def __eq__(self, other: object) -> bool:
            return True

        __hash__ = int.__hash__

    with pytest.raises(ValueError, match="JSON"):
        res("r", v=_Sneaky(1))


def test_grade_revalidates_inputs_and_rejects_post_construction_tampering() -> None:
    # frozen blocks attribute reassignment, NOT in-place mutation of the properties dict; grade
    # re-validates at the trust boundary so tampering past the construction guards fails closed.
    tampered = res("r", cfg="v")
    tampered.properties["$evil"] = "x"
    with pytest.raises(ValueError):
        grade(deployed(tampered), golden(res("r", cfg="v")))


def test_grade_revalidation_rejects_a_serializable_object_value_mutation() -> None:
    # A BaseModel/dataclass value would be serialized to plain JSON by model_dump BEFORE validation;
    # re-validation must check the RAW object graph so the injected non-JSON object fails closed.
    @dataclasses.dataclass
    class _Sneaky:
        v: int

    tampered = res("r", cfg="seed")
    tampered.properties["cfg"] = _Sneaky(1)
    with pytest.raises(ValueError):
        grade(deployed(tampered), golden(res("r", cfg="seed")))


def test_grade_rejects_a_deepcopy_laundering_object_mutation() -> None:
    # An object whose __deepcopy__ returns JSON must not launder past validation: the snapshot is
    # built from exact built-in types, never copy.deepcopy/model_dump on raw values (user dunders).
    class _Launder:
        def __deepcopy__(self, memo: object) -> str:
            return "ok"

    tampered = res("r", cfg="seed")
    tampered.properties["cfg"] = _Launder()
    with pytest.raises(ValueError):
        grade(deployed(tampered), golden(res("r", cfg="ok")))


def test_grade_report_is_an_independent_snapshot_of_the_inputs() -> None:
    # The report must not alias the inputs: mutating an input's nested value after grade() must not
    # change the already-returned diff report (report-byte determinism for the reportDigest).
    deployed_state = deployed(res("r", cfg={"a": 1}))
    golden_state = golden(res("r", cfg={"a": 2}))
    outcome = grade(deployed_state, golden_state)
    before = outcome.diff.model_dump(mode="json", exclude_none=True)
    cfg = deployed_state.resources[0].properties["cfg"]
    assert isinstance(cfg, dict)
    cfg["a"] = 999  # mutate the input's nested value after grading
    assert outcome.diff.model_dump(mode="json", exclude_none=True) == before


# --- coverage regression guards (P2) ---


def test_reward_0_when_some_resources_unchanged_and_one_changed() -> None:
    outcome = grade(
        deployed(res("keep"), res("drift", v="actual")),
        golden(res("keep"), res("drift", v="golden")),
    )
    assert outcome.reward is Reward.number_0
    assert by_address(outcome)["keep"].change is Change.unchanged


def test_all_property_diffs_present_and_sorted_with_three_changes() -> None:
    outcome = grade(
        deployed(res("r", c="c2", a="a2", b="b2")),
        golden(res("r", a="a1", b="b1", c="c1")),
    )
    resource = by_address(outcome)["r"]
    assert resource.propertyDiffs is not None
    assert [pd.path for pd in resource.propertyDiffs] == ["a", "b", "c"]


def test_nested_dict_with_reordered_keys_is_unchanged() -> None:
    outcome = grade(
        deployed(res("r", cfg={"a": 1, "b": 2})),
        golden(res("r", cfg={"b": 2, "a": 1})),
    )
    assert outcome.reward is Reward.number_1


def test_reordered_list_property_is_a_diff_the_core_does_not_sort() -> None:
    # The core compares lists order-sensitively; the adapter sorts order-insensitive collections.
    outcome = grade(
        deployed(res("r", rules=["b", "a"])),
        golden(res("r", rules=["a", "b"])),
    )
    assert outcome.reward is Reward.number_0
