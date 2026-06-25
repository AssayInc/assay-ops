"""E3-1 (#34) — the shared reward core's diff semantics (DECISIONS.md 6A/2A).

reward 1 = zero normalized diff against the regenerated golden (golden=expected, deployed=actual).
Every golden/deployed resource appears in the DiffIR with its change status; reward is ``number_1``
iff all are ``unchanged``. ``removed`` = a missing expected resource; ``added`` = an extra one.
"""

from __future__ import annotations

from assayops_contracts import Change, Reward
from factories import by_address, deployed, golden, res

from assayops_diff_ir import grade


def test_identical_states_grade_in_sync_with_reward_1() -> None:
    outcome = grade(
        deployed(res("bucket", versioning="Enabled")),
        golden(res("bucket", versioning="Enabled")),
    )
    assert outcome.reward is Reward.number_1
    assert by_address(outcome)["bucket"].change is Change.unchanged


def test_unchanged_resource_is_listed_with_no_property_diffs() -> None:
    outcome = grade(deployed(res("bucket")), golden(res("bucket")))
    bucket = by_address(outcome)["bucket"]
    assert bucket.change is Change.unchanged
    assert bucket.propertyDiffs is None


def test_resource_missing_from_deployed_grades_removed_and_reward_0() -> None:
    outcome = grade(
        deployed(res("bucket")),
        golden(res("bucket"), res("queue", rtype="AWS::SQS::Queue")),
    )
    assert outcome.reward is Reward.number_0
    assert by_address(outcome)["queue"].change is Change.removed


def test_extra_resource_in_deployed_grades_added_and_reward_0() -> None:
    outcome = grade(
        deployed(res("bucket"), res("queue", rtype="AWS::SQS::Queue")),
        golden(res("bucket")),
    )
    assert outcome.reward is Reward.number_0
    assert by_address(outcome)["queue"].change is Change.added


def test_property_mismatch_grades_modified_with_expected_and_actual() -> None:
    outcome = grade(
        deployed(res("bucket", versioning="Suspended")),
        golden(res("bucket", versioning="Enabled")),
    )
    assert outcome.reward is Reward.number_0
    bucket = by_address(outcome)["bucket"]
    assert bucket.change is Change.modified
    assert bucket.propertyDiffs is not None
    diffs = {pd.path: pd for pd in bucket.propertyDiffs}
    assert diffs["versioning"].expected == "Enabled"
    assert diffs["versioning"].actual == "Suspended"


def test_property_missing_from_deployed_grades_modified_with_expected_only() -> None:
    outcome = grade(deployed(res("bucket")), golden(res("bucket", versioning="Enabled")))
    bucket = by_address(outcome)["bucket"]
    assert bucket.change is Change.modified
    assert bucket.propertyDiffs is not None
    pd = bucket.propertyDiffs[0]
    assert pd.path == "versioning"
    assert pd.expected == "Enabled"
    assert pd.actual is None


def test_extra_property_in_deployed_grades_modified_with_actual_only() -> None:
    outcome = grade(deployed(res("bucket", versioning="Enabled")), golden(res("bucket")))
    bucket = by_address(outcome)["bucket"]
    assert bucket.change is Change.modified
    assert bucket.propertyDiffs is not None
    pd = bucket.propertyDiffs[0]
    assert pd.path == "versioning"
    assert pd.actual == "Enabled"
    assert pd.expected is None


def test_type_mismatch_at_same_address_grades_modified() -> None:
    outcome = grade(
        deployed(res("thing", rtype="AWS::SQS::Queue")),
        golden(res("thing", rtype="AWS::S3::Bucket")),
    )
    assert outcome.reward is Reward.number_0
    thing = by_address(outcome)["thing"]
    assert thing.change is Change.modified
    assert thing.propertyDiffs is not None
    diffs = {pd.path: pd for pd in thing.propertyDiffs}
    assert diffs["$type"].expected == "AWS::S3::Bucket"
    assert diffs["$type"].actual == "AWS::SQS::Queue"


def test_empty_states_grade_in_sync_with_reward_1() -> None:
    outcome = grade(deployed(), golden())
    assert outcome.reward is Reward.number_1
    assert outcome.diff.resources == []
