"""End-to-end (#35 acceptance criteria): normalize a deployed read, grade it against a golden.

The reward tracks the DEPLOYED state, never the agent's plan/state -- the adapter + the reward
core (#34) together close the T1 surface. These exercise the real ``grade`` (not a mock).
"""

from __future__ import annotations

from assayops_contracts import Change, Reward
from assayops_diff_ir import NormalizedResource, NormalizedState, Provenance, grade
from factories import s3_read, s3_registry

from assayops_adapter_terraform import normalize


def _golden(*resources: NormalizedResource) -> NormalizedState:
    return NormalizedState(provenance=Provenance.GOLDEN_TARGET, resources=resources)


def _bucket(address: str, **properties: object) -> NormalizedResource:
    return NormalizedResource(address=address, type="AWS::S3::Bucket", properties=properties)


def test_reproduces_the_nsync_no_diff_but_required_import_correct_case() -> None:
    # AC1: a resource adopted via `terraform import` shows an import line in a plan, but its
    # deployed state matches the golden -> zero diff -> reward 1. Grade reads state, not the plan.
    golden = _golden(
        _bucket(
            "primary", BucketName="assayops-shared", VersioningConfiguration={"Status": "Enabled"}
        )
    )
    deployed_read = s3_read(
        "primary",
        identifier="assayops-shared",
        BucketName="assayops-shared",
        Arn="arn:aws:s3:::assayops-shared",
        VersioningConfiguration={"Status": "Enabled"},
    )
    outcome = grade(normalize([deployed_read], s3_registry()), golden)
    assert outcome.reward is Reward.number_1


def test_grades_from_state_only_even_when_a_plan_would_differ() -> None:
    # AC2: deployed state matches the golden -> reward 1, regardless of a (never-consumed) plan.
    golden = _golden(
        _bucket(
            "primary", BucketName="assayops-shared", VersioningConfiguration={"Status": "Enabled"}
        )
    )
    deployed_read = s3_read(
        "primary",
        identifier="assayops-shared",
        BucketName="assayops-shared",
        VersioningConfiguration={"Status": "Enabled"},
    )
    plan_that_would_differ = {"resource_changes": [{"change": {"actions": ["update"]}}]}
    _ = plan_that_would_differ  # in the episode, but the adapter has no channel to read it
    outcome = grade(normalize([deployed_read], s3_registry()), golden)
    assert outcome.reward is Reward.number_1


def test_the_grade_tracks_deployed_state_not_an_agent_state_file_claim() -> None:
    # AC3: a poisoned `.tfstate` claiming Enabled can't rescue a deploy that actually Suspended
    # versioning -- the adapter reads the deployed value, so the real mismatch grades 0 (vector #7).
    golden = _golden(
        _bucket(
            "primary", BucketName="assayops-shared", VersioningConfiguration={"Status": "Enabled"}
        )
    )
    actually_suspended = s3_read(
        "primary",
        identifier="assayops-shared",
        BucketName="assayops-shared",
        VersioningConfiguration={"Status": "Suspended"},
    )
    outcome = grade(normalize([actually_suspended], s3_registry()), golden)
    assert outcome.reward is Reward.number_0


def test_an_extra_deployed_resource_grades_zero_never_filtered_away() -> None:
    # An extra resource (valid address, not in the golden) is emitted as `added` -> reward 0.
    golden = _golden(_bucket("primary", BucketName="assayops-shared"))
    reads = [
        s3_read("primary", identifier="assayops-shared", BucketName="assayops-shared"),
        s3_read("rogue", identifier="assayops-rogue", BucketName="assayops-rogue"),
    ]
    outcome = grade(normalize(reads, s3_registry()), golden)
    assert outcome.reward is Reward.number_0
    added = {r.address for r in outcome.diff.resources if r.change is Change.added}
    assert added == {"rogue"}
