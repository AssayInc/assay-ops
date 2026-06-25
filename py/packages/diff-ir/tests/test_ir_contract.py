"""E3-1 (#34, AC1) -- the IR is tool-agnostic and round-trips through the reward core.

The normalized-state IR and the produced ``DiffIR`` carry ``type``/``address`` as opaque strings;
the core never branches on the source tool (Terraform now, CDK/CFN later). The produced ``DiffIR``
is a faithful, serializable contract artifact: it round-trips, and its sparse serialization
(``exclude_none``) is schema-valid -- no ``propertyDiffs: null`` (the ISSUES.md DiffIR residual),
the form the reward ledger (E4) digests into ``RewardRecord.reportDigest``.
"""

from __future__ import annotations

from assayops_contracts import DiffIR, Reward
from factories import deployed, golden, res

from assayops_diff_ir import GradeOutcome, grade


def _rich_outcome() -> GradeOutcome:
    # A diff that exercises every change type: unchanged, modified, added, removed.
    return grade(
        deployed(
            res("keep", v="same"),
            res("change", v="actual"),
            res("extra", rtype="AWS::SQS::Queue"),
        ),
        golden(
            res("keep", v="same"),
            res("change", v="golden"),
            res("gone", rtype="AWS::SNS::Topic"),
        ),
    )


def test_grade_is_tool_agnostic_across_naming_conventions() -> None:
    # Terraform-style and CloudFormation/CDK-style addresses both flow through the same core.
    tf = grade(
        deployed(res("aws_s3_bucket.data", rtype="aws_s3_bucket", acl="private")),
        golden(res("aws_s3_bucket.data", rtype="aws_s3_bucket", acl="private")),
    )
    cfn = grade(
        deployed(res("DataBucket", rtype="AWS::S3::Bucket", acl="private")),
        golden(res("DataBucket", rtype="AWS::S3::Bucket", acl="private")),
    )
    assert tf.reward is Reward.number_1
    assert cfn.reward is Reward.number_1


def test_produced_diff_ir_round_trips_through_the_contract_model() -> None:
    diff = _rich_outcome().diff
    dumped = diff.model_dump(mode="json", exclude_none=True)
    reparsed = DiffIR.model_validate(dumped)
    assert reparsed == diff
    # Idempotent: re-dumping the reparsed report yields identical JSON (any union member).
    assert reparsed.model_dump(mode="json", exclude_none=True) == dumped


def test_sparse_serialization_is_schema_valid_no_null_property_diffs() -> None:
    outcome = grade(
        deployed(res("keep"), res("change")),
        golden(res("keep"), res("change", v="x")),
    )
    dumped = outcome.diff.model_dump(mode="json", exclude_none=True)
    indexed = {r["address"]: r for r in dumped["resources"]}
    # Non-modified: the optional key is omitted -- never `propertyDiffs: null` (schema-invalid).
    assert "propertyDiffs" not in indexed["keep"]
    # Modified: present + non-empty; the missing-from-deployed side dumps expected-only.
    property_diffs = indexed["change"]["propertyDiffs"]
    assert property_diffs
    assert "actual" not in property_diffs[0]
    assert property_diffs[0]["expected"] == "x"
