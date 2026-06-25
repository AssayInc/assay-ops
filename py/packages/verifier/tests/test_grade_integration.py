"""#31 (E2-2, AC1) — generate→bridge→grade on a known pair (DECISIONS.md 2A/6A/T1).

The verifier regenerates the #75 golden from (task, seed) and grades a B-side deployed-state read
against it: zero *normalized* diff = reward 1, else 0. These prove the COMPOSITION end-to-end (the
diff-ir core unit-tests each diff branch in its own package); here a correct deploy → 1, each drift
→ 0, and "normalized" tolerates JCS-equal encodings — all through the full generate→bridge→grade
path.
"""

from __future__ import annotations

from assayops_contracts import Change, Reward
from assayops_diff_ir import NormalizedResource, NormalizedState, Provenance
from synthetic import (
    NORMALIZABLE_TASK_ID,
    SYNTHETIC_TASK_ID,
    deployed_from_golden,
    make_task,
    normalizable_builder,
    s3_bucket_builder,
)

from assayops_verifier import GoldenRegistry, grade_deployment

SEED = "episode-7"


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    registry.register(NORMALIZABLE_TASK_ID, normalizable_builder)
    return registry


def _deployed(*resources: NormalizedResource) -> NormalizedState:
    return NormalizedState(provenance=Provenance.DEPLOYED_READ, resources=resources)


def test_correct_deploy_grades_reward_1() -> None:
    registry = _registry()
    task = make_task(seed=SEED)
    deployed = deployed_from_golden(registry.generate(task, SEED))

    outcome = grade_deployment(registry, task, SEED, deployed)

    assert outcome.reward is Reward.number_1
    assert outcome.diff.resources  # the golden resource is present in the report...
    assert all(r.change is Change.unchanged for r in outcome.diff.resources)  # ...and unchanged


def test_property_drift_grades_reward_0() -> None:
    registry = _registry()
    task = make_task(seed=SEED)
    bucket = registry.generate(task, SEED).resources[0]
    # Same correct bucket, one property drifted: versioning Suspended where golden wants Enabled.
    drifted = dict(bucket.properties)
    drifted["VersioningConfiguration"] = {"Status": "Suspended"}
    deployed = _deployed(
        NormalizedResource(address=bucket.address, type=bucket.type, properties=drifted)
    )

    outcome = grade_deployment(registry, task, SEED, deployed)

    assert outcome.reward is Reward.number_0
    changed = {r.address: r for r in outcome.diff.resources}[bucket.address]
    assert changed.change is Change.modified


def test_missing_resource_grades_reward_0() -> None:
    registry = _registry()
    task = make_task(seed=SEED)
    # The agent deployed nothing the golden expects.
    outcome = grade_deployment(registry, task, SEED, _deployed())

    assert outcome.reward is Reward.number_0
    assert all(r.change is Change.removed for r in outcome.diff.resources)


def test_extra_resource_grades_reward_0() -> None:
    registry = _registry()
    task = make_task(seed=SEED)
    correct = deployed_from_golden(registry.generate(task, SEED))
    # A correct deploy plus an extra the golden doesn't expect ⇒ reward 0. (Catching extras in the
    # live account is the read path's closed-world job, #141/#53; here the extra is in the input.)
    extra = NormalizedResource(address="rogue", type="AWS::SQS::Queue", properties={})
    deployed = _deployed(*correct.resources, extra)

    outcome = grade_deployment(registry, task, SEED, deployed)

    assert outcome.reward is Reward.number_0
    assert {r.address: r for r in outcome.diff.resources}["rogue"].change is Change.added


def test_type_drift_grades_reward_0() -> None:
    registry = _registry()
    task = make_task(seed=SEED)
    bucket = registry.generate(task, SEED).resources[0]
    # Right address, wrong resource type — a same-address type mismatch is a drift, never reward 1.
    deployed = _deployed(
        NormalizedResource(address=bucket.address, type="AWS::SQS::Queue", properties={})
    )

    outcome = grade_deployment(registry, task, SEED, deployed)

    assert outcome.reward is Reward.number_0


def test_normalized_diff_tolerates_jcs_equal_encodings() -> None:
    # The "*normalized* diff" guarantee: a correct deploy matching by VALUE but differing in JSON
    # representation (int 90 read back as float 90.0; keys in a different order) still grades 1.
    registry = _registry()
    task = make_task(task_id=NORMALIZABLE_TASK_ID, seed=SEED)
    deployed = _deployed(
        NormalizedResource(
            address="config",
            type="AWS::S3::Bucket",
            properties={"RetentionDays": 90.0, "Tags": {"env": "test", "team": "core"}},
        )
    )

    outcome = grade_deployment(registry, task, SEED, deployed)

    assert outcome.reward is Reward.number_1
    assert all(r.change is Change.unchanged for r in outcome.diff.resources)
