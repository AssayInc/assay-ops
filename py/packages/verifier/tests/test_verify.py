"""E2-1 (#30, the AC): the read-and-grade skeleton end-to-end + the structural moat.

``verify_deployment`` wires the boto3 Cloud Control read (#30) -> ``normalize`` (#35) ->
``grade_deployment`` (#31): a clean deploy grades reward 1, a drifted/missing one grades 0 -- all
from state read independently of the agent (DECISIONS.md section 1, T1). A read that cannot be
vouched for fails CLOSED (vector #15). The deployed state the read path produces is always
DEPLOYED_READ provenance, so the grade can never be handed agent-reported state (vectors
#1/#7/#10).

The deployed resource a CORRECT deploy reads back is the golden's resources, carrying the
``assayops:address`` tag bridge (#35) and a server-computed readOnly ``Arn`` the adapter drops.
Drift cases perturb that read; the in-scope ``type_names`` are read via Cloud Control.
"""

from __future__ import annotations

import pytest
from assayops_adapter_terraform import (
    UnreadableResourceError,
    UnsupportedResourceTypeError,
    normalize,
)
from assayops_contracts import Reward
from assayops_diff_ir import Provenance
from cloud_control_fakes import FakeCloudControlClient
from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_verifier import GoldenRegistry
from assayops_verifier.models import GoldenResource
from assayops_verifier.read import DeployedStateReader, verify_deployment

S3 = "AWS::S3::Bucket"
SEED = "episode-30"
PHYSICAL_ID = "assayops-physical-bucket"


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry


def _read_back(bucket: GoldenResource, **property_overrides: object) -> dict[str, object]:
    """The Cloud Control read-back of a deploy of ``bucket``: its golden properties + the
    ``assayops:address`` tag bridge + a server-computed readOnly ``Arn`` the adapter drops."""
    return {
        **bucket.properties,
        **property_overrides,
        "Tags": [{"Key": "assayops:address", "Value": bucket.address}],
        "Arn": f"arn:aws:s3:::{PHYSICAL_ID}",
    }


def test_clean_deployed_state_grades_reward_1() -> None:
    registry = _registry()
    task = make_task(seed=SEED)
    bucket = registry.generate(task, SEED).resources[0]
    client = FakeCloudControlClient({(S3, PHYSICAL_ID): _read_back(bucket)})

    outcome = verify_deployment(DeployedStateReader(client), registry, task, SEED, [S3])

    assert outcome.reward is Reward.number_1


def test_property_drifted_deployed_state_grades_reward_0() -> None:
    registry = _registry()
    task = make_task(seed=SEED)
    bucket = registry.generate(task, SEED).resources[0]
    # The deployed bucket has versioning Suspended where the golden wants Enabled -- a known drift.
    drifted = _read_back(bucket, VersioningConfiguration={"Status": "Suspended"})
    client = FakeCloudControlClient({(S3, PHYSICAL_ID): drifted})

    outcome = verify_deployment(DeployedStateReader(client), registry, task, SEED, [S3])

    assert outcome.reward is Reward.number_0


def test_missing_deployed_resource_grades_reward_0() -> None:
    registry = _registry()
    task = make_task(seed=SEED)
    # The agent deployed nothing; the read enumerates an empty account.
    client = FakeCloudControlClient()

    outcome = verify_deployment(DeployedStateReader(client), registry, task, SEED, [S3])

    assert outcome.reward is Reward.number_0


def test_a_genuinely_unreadable_deployed_resource_fails_closed() -> None:
    # A GENUINELY-unreadable resource (AccessDenied -- not a transient) is surfaced as
    # UnreadableResource; the adapter fails closed (UnreadableResourceError) rather than silently
    # grading the rest (vector #15). (A throttle would instead route through the 7A K-run -- see
    # test_read / test_verify_closed_world.)
    registry = _registry()
    task = make_task(seed=SEED)
    client = FakeCloudControlClient(access_denied={(S3, PHYSICAL_ID)})

    with pytest.raises(UnreadableResourceError):
        verify_deployment(DeployedStateReader(client), registry, task, SEED, [S3])


def test_an_unsupported_resource_type_fails_closed() -> None:
    # A deployed resource whose type has no registered bridge fails closed (never rewarded).
    registry = _registry()
    task = make_task(seed=SEED)
    client = FakeCloudControlClient({("AWS::SQS::Queue", "q1"): {"QueueName": "q1"}})

    with pytest.raises(UnsupportedResourceTypeError):
        verify_deployment(DeployedStateReader(client), registry, task, SEED, ["AWS::SQS::Queue"])


def test_the_graded_state_is_deployed_read_provenance_never_agent_reported() -> None:
    # The read path produces only DEPLOYED_READ provenance, so grade_deployment (which rejects any
    # other provenance, T1) can never be handed agent plan/state through #30 (vectors #1/#7/#10).
    registry = _registry()
    bucket = registry.generate(make_task(seed=SEED), SEED).resources[0]
    client = FakeCloudControlClient({(S3, PHYSICAL_ID): _read_back(bucket)})

    deployed = normalize(DeployedStateReader(client).read_type(S3))

    assert deployed.provenance is Provenance.DEPLOYED_READ


def test_verify_deployment_touches_read_operations_only() -> None:
    # The moat end-to-end through the grade (DECISIONS.md section 1/8, T1): vectors #1 (write to
    # the grader) and #10 (A->B assume) fail by construction -- the harness only ever reads.
    registry = _registry()
    task = make_task(seed=SEED)
    bucket = registry.generate(task, SEED).resources[0]
    client = FakeCloudControlClient({(S3, PHYSICAL_ID): _read_back(bucket)})

    verify_deployment(DeployedStateReader(client), registry, task, SEED, [S3])

    assert client.invoked_operations <= {"get_resource", "get_paginator", "list_resources"}
