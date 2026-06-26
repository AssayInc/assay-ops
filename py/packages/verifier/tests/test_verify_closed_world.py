"""E2-6 (#141) scope 1: the closed-world verify entry + verdict -- read -> grade via the 7A K-run.

Covers the ``VerifyVerdict`` mapping: a settled grade -> ``Reproducible`` (reward 1 clean / reward 0
drift / reward 0 on an enumerated extra); a persistent EVENTUAL_CONSISTENCY race -> ``FailedClosed``
(reward 0, never dropped); a persistent INFRA transient -> ``Quarantined``; a genuine unreadable ->
propagates (fail closed). The negative control (the AC): an *extra* or *unreadable* B-side resource
the golden lacks -> reward 0 / fail closed, NEVER reward 1.
"""

from __future__ import annotations

import pytest
from assayops_adapter_terraform import UnreadableResourceError
from assayops_contracts import Reward
from assayops_replay import Quarantined, Reproducible
from cloud_control_fakes import FakeCloudControlClient
from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_verifier import GoldenRegistry
from assayops_verifier.models import GoldenResource
from assayops_verifier.read import DeployedStateReader
from assayops_verifier.read_scope import Listability, ReadScope, RegionScope, TypeCoverage
from assayops_verifier.verify import FailedClosed, verify

S3 = "AWS::S3::Bucket"
SEED = "episode-141"
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


def _read_back(bucket: GoldenResource, **overrides: object) -> dict[str, object]:
    return {
        **bucket.properties,
        **overrides,
        "Tags": [{"Key": "assayops:address", "Value": bucket.address}],
        "Arn": f"arn:aws:s3:::{PHYSICAL_ID}",
    }


def _golden_bucket() -> GoldenResource:
    return _registry().generate(make_task(seed=SEED), SEED).resources[0]


def _verify(client: FakeCloudControlClient, *, runs: int = 3) -> object:
    return verify(
        {"us-east-1": DeployedStateReader(client)},
        _registry(),
        make_task(seed=SEED),
        SEED,
        _scope(),
        runs=runs,
    )


def test_clean_deploy_is_reproducible_reward_1() -> None:
    verdict = _verify(FakeCloudControlClient({(S3, PHYSICAL_ID): _read_back(_golden_bucket())}))

    assert isinstance(verdict, Reproducible)
    assert verdict.reward is Reward.number_1


def test_drift_is_reproducible_reward_0() -> None:
    drifted = _read_back(_golden_bucket(), VersioningConfiguration={"Status": "Suspended"})
    verdict = _verify(FakeCloudControlClient({(S3, PHYSICAL_ID): drifted}))

    assert isinstance(verdict, Reproducible)
    assert verdict.reward is Reward.number_0


def test_an_extra_enumerated_resource_grades_reward_0() -> None:
    # THE NEGATIVE CONTROL: the agent over-provisioned an EXTRA bucket the golden does not have. The
    # closed-world enumeration reads it, so the core flags it `added` -> reward 0, never 1 (#15).
    client = FakeCloudControlClient(
        {
            (S3, PHYSICAL_ID): _read_back(_golden_bucket()),
            (S3, "extra-physical"): {
                "BucketName": "rogue",
                "Tags": [{"Key": "assayops:address", "Value": "rogue_bucket"}],
                "Arn": "arn:aws:s3:::extra",
            },
        }
    )
    verdict = _verify(client)

    assert isinstance(verdict, Reproducible)
    assert verdict.reward is Reward.number_0


def test_a_genuinely_unreadable_resource_fails_closed() -> None:
    # AccessDenied is genuine -> propagates (fail closed), never reward 1 nor a silent 0.
    client = FakeCloudControlClient(access_denied={(S3, PHYSICAL_ID)})

    with pytest.raises(UnreadableResourceError):
        _verify(client)


def test_a_persistent_eventual_consistency_race_fails_closed_reward_0() -> None:
    # A listed-but-unreadable resource that never settles (the race persists across the K-run)
    # -> FailedClosed(reward 0): can't verify the set, so never a false 1 -- but NOT dropped (#15).
    verdict = _verify(FakeCloudControlClient(vanished={(S3, "ghost")}))

    assert isinstance(verdict, FailedClosed)
    assert verdict.reward is Reward.number_0


def test_a_persistent_infra_transient_is_quarantined() -> None:
    # A throttle that never completes is NOT a wrong answer -> Quarantined (pulled from scoring) --
    # never reward 0 (that would be the false-negative the deterministic-verification skill names).
    verdict = _verify(FakeCloudControlClient(unreadable={(S3, "throttled")}))

    assert isinstance(verdict, Quarantined)


def test_verify_touches_read_operations_only() -> None:
    # The moat end-to-end through the closed-world K-run verify (DECISIONS.md section 1/8, T1):
    # across all K grade runs and every Region's reader, ONLY Cloud Control read ops are invoked --
    # so vector #1 (write to grader) and vector #10 (A->B assume) fail by construction. The fake
    # raises on any non-read op, so this asserts the harness's ACTUAL behavior, not the fake's.
    east = FakeCloudControlClient({(S3, PHYSICAL_ID): _read_back(_golden_bucket())})
    west = FakeCloudControlClient()
    verify(
        {"us-east-1": DeployedStateReader(east), "eu-west-1": DeployedStateReader(west)},
        _registry(),
        make_task(seed=SEED),
        SEED,
        ReadScope(
            coverages=(TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),),
            allowed_regions=("us-east-1", "eu-west-1"),
        ),
    )

    read_only = {"get_resource", "get_paginator", "list_resources"}
    assert east.invoked_operations <= read_only
    assert west.invoked_operations <= read_only


def test_grade_is_reproducible_across_k_runs() -> None:
    # The determinism gate: a clean deploy graded K=5 times agrees -> Reproducible with the runs.
    verdict = _verify(
        FakeCloudControlClient({(S3, PHYSICAL_ID): _read_back(_golden_bucket())}), runs=5
    )

    assert isinstance(verdict, Reproducible)
    assert verdict.runs == 5
    assert verdict.reward is Reward.number_1
