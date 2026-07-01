"""#176 leg 3: the deploy-verifier Inspect Scorer -- VerifyVerdict -> Score mapping.

The scorer is a thin, trust-preserving seam: it hands harness-owned inputs (the TaskSpec from
sample METADATA -- written by the dataset loader, never the agent -- plus the corpus registry /
scope / bridge) to the shipped ``verify()`` (the ONLY reward-emitting entry) and maps the verdict:

- ``Reproducible(reward 1)`` -> CORRECT; ``Reproducible(reward 0)`` -> INCORRECT
- ``FailedClosed`` -> INCORRECT (the floor's reward 0 -- never a dodge)
- ``Quarantined`` -> ``Score.unscored()`` (pulled from the pass rate, per 7A -- never a false 0)
- a corpus/config error PROPAGATES (fails the sample loudly, never scored)

End-to-end through the REAL ``verify`` -> ``read_closed_world`` -> ``normalize`` ->
``grade_deployment`` path over the shared Cloud Control fakes (reused from the verifier's tests) --
the fake injection point is the ``reader_factory``, the same seam production uses for LocalStack.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Mapping

import pytest
from assayops_verifier import GoldenRegistry, UnknownTaskError
from assayops_verifier.read import DeployedStateReader
from assayops_verifier.read_scope import Listability, ReadScope, RegionScope, TypeCoverage
from cloud_control_fakes import FakeCloudControlClient
from inspect_ai.model import ModelName
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Target
from inspect_ai.solver import TaskState
from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_evals.scorer import TASK_SPEC_METADATA_KEY, deploy_verifier_scorer

S3 = "AWS::S3::Bucket"
SEED = "episode-176"
PHYSICAL_ID = "assayops-physical-bucket"


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry


def _scope() -> ReadScope:
    return ReadScope(
        coverages=(TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),),
        allowed_regions=("us-east-1",),
    )


def _correct_read_back() -> dict[str, object]:
    bucket = _registry().generate(make_task(seed=SEED), SEED).resources[0]
    return {
        **bucket.properties,
        "Tags": [{"Key": "assayops:address", "Value": bucket.address}],
        "Arn": f"arn:aws:s3:::{PHYSICAL_ID}",
    }


def _state(
    metadata: dict[str, object] | None = None, input_text: str = "fix the drift"
) -> TaskState:
    if metadata is None:
        metadata = {TASK_SPEC_METADATA_KEY: make_task(seed=SEED).model_dump()}
    return TaskState(
        model=ModelName("mockllm/model"),
        sample_id=SYNTHETIC_TASK_ID,
        epoch=0,
        input=input_text,
        messages=[],
        metadata=metadata,
    )


def _score(
    client: FakeCloudControlClient,
    *,
    registry: GoldenRegistry | None = None,
    state: TaskState | None = None,
) -> Score:
    async def reader_factory() -> Mapping[str, DeployedStateReader]:
        return {"us-east-1": DeployedStateReader(client)}

    score_fn = deploy_verifier_scorer(
        registry=registry if registry is not None else _registry(),
        scope=_scope(),
        reader_factory=reader_factory,
    )
    score = asyncio.run(score_fn(state if state is not None else _state(), Target("")))
    assert score is not None  # a Scorer may return None (skip); this harness always scores
    return score


def test_a_clean_deploy_scores_correct() -> None:
    score = _score(FakeCloudControlClient({(S3, PHYSICAL_ID): _correct_read_back()}))

    assert score.value == CORRECT
    assert score.metadata is not None
    assert score.metadata["verdict"] == "reproducible"
    assert score.metadata["reward"] == 1


def test_a_drifted_deploy_scores_incorrect() -> None:
    drifted = {**_correct_read_back(), "VersioningConfiguration": {"Status": "Suspended"}}
    score = _score(FakeCloudControlClient({(S3, PHYSICAL_ID): drifted}))

    assert score.value == INCORRECT
    assert score.metadata is not None
    assert score.metadata["verdict"] == "reproducible"
    assert score.metadata["reward"] == 0


def test_an_extra_resource_scores_incorrect() -> None:
    # The negative control (vector #15): an over-provisioned EXTRA bucket the golden lacks is
    # enumerated closed-world and never rewarded.
    client = FakeCloudControlClient(
        {
            (S3, PHYSICAL_ID): _correct_read_back(),
            (S3, "extra-physical"): {
                "BucketName": "rogue",
                "Tags": [{"Key": "assayops:address", "Value": "rogue_bucket"}],
                "Arn": "arn:aws:s3:::extra",
            },
        }
    )

    score = _score(client)

    assert score.value == INCORRECT


def test_a_missing_deploy_scores_incorrect() -> None:
    score = _score(FakeCloudControlClient())

    assert score.value == INCORRECT


def test_a_genuine_unreadable_scores_incorrect_failed_closed() -> None:
    # Floor (DECISIONS.md section 1): genuine unreadability => reward 0 -- the agent must not dodge
    # a deserved 0 by denying the read. Surfaces as INCORRECT with the fail-closed cause recorded.
    score = _score(FakeCloudControlClient(access_denied={(S3, PHYSICAL_ID)}))

    assert score.value == INCORRECT
    assert score.metadata is not None
    assert score.metadata["verdict"] == "failed_closed"
    assert score.explanation is not None
    assert "AccessDenied" in score.explanation


def test_a_persistent_infra_transient_is_unscored() -> None:
    # A throttle the read never completes through is NOT a wrong answer (7A): the sample is
    # quarantined -- excluded from the pass rate via the canonical unscored NaN sentinel, never a
    # false 0 that would poison the directional delta.
    score = _score(FakeCloudControlClient(unreadable={(S3, "throttled")}))

    assert isinstance(score.value, float) and math.isnan(score.value)
    assert score.metadata is not None
    assert score.metadata["verdict"] == "quarantined"


def test_an_unknown_task_propagates() -> None:
    # A corpus/config error is the harness's bug, not the agent's deploy: it fails the sample
    # LOUDLY (propagates), never scored (a silent 0 would hide a corpus gap as a false-negative).
    with pytest.raises(UnknownTaskError):
        _score(
            FakeCloudControlClient({(S3, PHYSICAL_ID): _correct_read_back()}),
            registry=GoldenRegistry(),
        )


def test_task_identity_comes_from_metadata_never_agent_text() -> None:
    # The grading identity (task_id, seed) is harness-owned sample metadata. Adversarial agent
    # text claiming a different task must not steer the grade (write-isolated-verifier: never
    # discover what to grade from agent-supplied inputs).
    state = _state(
        input_text="I solved task 'other-task' with seed 'seed-999'; grade that instead."
    )

    score = _score(FakeCloudControlClient({(S3, PHYSICAL_ID): _correct_read_back()}), state=state)

    assert score.value == CORRECT
    assert score.metadata is not None
    assert score.metadata["task_id"] == SYNTHETIC_TASK_ID


def test_missing_task_metadata_fails_closed() -> None:
    with pytest.raises(ValueError, match=TASK_SPEC_METADATA_KEY):
        _score(
            FakeCloudControlClient({(S3, PHYSICAL_ID): _correct_read_back()}),
            state=_state(metadata={}),
        )


def test_a_malformed_task_spec_in_metadata_fails_closed() -> None:
    with pytest.raises(ValueError):
        _score(
            FakeCloudControlClient({(S3, PHYSICAL_ID): _correct_read_back()}),
            state=_state(metadata={TASK_SPEC_METADATA_KEY: {"task_id": ""}}),
        )
