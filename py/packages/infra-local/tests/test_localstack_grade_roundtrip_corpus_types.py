"""Per-type grade round-trips for the #176 corpus types beyond S3: IAM Role + KMS Key.

The founder per-type gate (see ``test_localstack_grade_roundtrip.py`` for the full contract
rationale): a type enters the adapter's ``default_registry`` -- and the corpus -- only after a
real LocalStack Cloud Control read proves (1) ``GetResource`` returns the ``assayops:address``
tag for it and (2) the golden shape a task author must declare, INCLUDING the server-defaulted
posture the deploy never set. The golden properties are DECLARED constants (authored intent),
never computed from the read; the reward-0 negative control proves the reward-1 test is not
vacuous and names exactly the posture gap. Values asserted here are what the pinned LocalStack
image serves (the ``KeyPolicy`` embeds LocalStack's fixed 000000000000 account id -- fine for the
LocalStack-graded slice by construction; real-AWS shape parity re-pins with the real-cloud read
path, #61).

Runs only via ``just smoke`` against a running LocalStack, never in the hermetic gate.
"""

from __future__ import annotations

import json

import pytest
from assayops_adapter_terraform import (
    ADDRESS_TAG,
    AddressBridgeError,
    DeployedResourceRead,
    normalize,
)
from assayops_contracts import Change, Reward, TaskSpec, Tool
from assayops_diff_ir import NormalizedState
from assayops_verifier import GoldenContext, GoldenRegistry, GoldenResource, grade_deployment
from assayops_verifier.read import DeployedStateReader
from localstack_clients import client as _client

_SEED = "seed-176-corpus-types"
_USER_TAG = {"Key": "team", "Value": "assay"}

# --- AWS::IAM::Role -------------------------------------------------------------------------

_ROLE_TYPE = "AWS::IAM::Role"
_ROLE_NAME = "assayops-roundtrip-role"
_ROLE_ADDRESS = "graded_role"
_TRUST_POLICY: dict[str, object] = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

# What the task author explicitly deploys for a role.
_ROLE_AUTHORED: dict[str, object] = {
    "RoleName": _ROLE_NAME,
    "AssumeRolePolicyDocument": _TRUST_POLICY,
    "Tags": [_USER_TAG],
}

# What the server ADDS to a real read without the deploy ever setting it (Arn/RoleId are
# readOnlyProperties, dropped by the bridge -- not posture).
_ROLE_SERVER_POSTURE: dict[str, object] = {
    "ManagedPolicyArns": [],
    "MaxSessionDuration": 3600,
    "Path": "/",
    "Policies": [],
}

# --- AWS::KMS::Key --------------------------------------------------------------------------

_KEY_TYPE = "AWS::KMS::Key"
_KEY_ADDRESS = "graded_key"

# A key author sets nothing but tags in the minimal deploy; EVERYTHING else below is
# server-defaulted posture a golden must declare (Arn/KeyId are readOnly, dropped).
_KEY_SERVER_POSTURE: dict[str, object] = {
    "Description": "",
    "EnableKeyRotation": False,
    "Enabled": True,
    "KeyPolicy": {
        "Id": "key-default-1",
        "Statement": [
            {
                "Action": "kms:*",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::000000000000:root"},
                "Resource": "*",
                "Sid": "Enable IAM User Permissions",
            }
        ],
        "Version": "2012-10-17",
    },
    "KeySpec": "SYMMETRIC_DEFAULT",
    "KeyUsage": "ENCRYPT_DECRYPT",
    "MultiRegion": False,
    "Origin": "AWS_KMS",
}
_KEY_AUTHORED: dict[str, object] = {"Tags": [_USER_TAG]}

_ROLE_CONTRACT_TASK = "synthetic-role-contract"
_ROLE_MINIMAL_TASK = "synthetic-role-minimal"
_KEY_CONTRACT_TASK = "synthetic-key-contract"
_KEY_MINIMAL_TASK = "synthetic-key-minimal"


def _registry() -> GoldenRegistry:
    def role_contract(_ctx: GoldenContext) -> list[GoldenResource]:
        return [
            GoldenResource(
                address=_ROLE_ADDRESS,
                type=_ROLE_TYPE,
                properties={**_ROLE_AUTHORED, **_ROLE_SERVER_POSTURE},
            )
        ]

    def role_minimal(_ctx: GoldenContext) -> list[GoldenResource]:
        return [GoldenResource(address=_ROLE_ADDRESS, type=_ROLE_TYPE, properties=_ROLE_AUTHORED)]

    def key_contract(_ctx: GoldenContext) -> list[GoldenResource]:
        return [
            GoldenResource(
                address=_KEY_ADDRESS,
                type=_KEY_TYPE,
                properties={**_KEY_AUTHORED, **_KEY_SERVER_POSTURE},
            )
        ]

    def key_minimal(_ctx: GoldenContext) -> list[GoldenResource]:
        return [GoldenResource(address=_KEY_ADDRESS, type=_KEY_TYPE, properties=_KEY_AUTHORED)]

    registry = GoldenRegistry()
    registry.register(_ROLE_CONTRACT_TASK, role_contract)
    registry.register(_ROLE_MINIMAL_TASK, role_minimal)
    registry.register(_KEY_CONTRACT_TASK, key_contract)
    registry.register(_KEY_MINIMAL_TASK, key_minimal)
    return registry


def _task(task_id: str) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        title="Synthetic corpus-type grade round-trip",
        description="Engine-validation fixture for the per-type corpus gate.",
        tool=Tool.terraform,
        seed=_SEED,
    )


@pytest.fixture(scope="module")
def reader() -> DeployedStateReader:
    return DeployedStateReader(client=_client("cloudcontrol"))


def _normalized(reader: DeployedStateReader, type_name: str, identifier: str) -> NormalizedState:
    read = reader.read_resource(type_name, identifier)
    assert isinstance(read, DeployedResourceRead), f"expected a settled read, got {read!r}"
    return normalize([read])


def _fresh_role(name: str, tags: list[dict[str, str]]) -> str:
    """Delete-and-recreate the role so a run never sees stale local mutations."""
    iam = _client("iam")
    try:
        iam.delete_role(RoleName=name)
    except iam.exceptions.NoSuchEntityException:
        pass
    iam.create_role(
        RoleName=name,
        AssumeRolePolicyDocument=json.dumps(_TRUST_POLICY),
        Tags=tags,
    )
    return name


@pytest.fixture(scope="module")
def deployed_role() -> str:
    """The corpus deploy contract for a role: address tag + a user tag; everything else is left
    to the server (MaxSessionDuration/Path/ManagedPolicyArns/Policies -- the posture under
    test)."""
    return _fresh_role(_ROLE_NAME, [{"Key": ADDRESS_TAG, "Value": _ROLE_ADDRESS}, _USER_TAG])


@pytest.fixture(scope="module")
def deployed_key() -> str:
    """A fresh key per run (KMS keys cannot be deleted synchronously -- scheduling deletion is
    async -- so recreation IS the freshness guarantee; the read is get-scoped by KeyId)."""
    kms = _client("kms")
    created = kms.create_key(
        Tags=[
            {"TagKey": ADDRESS_TAG, "TagValue": _KEY_ADDRESS},
            {"TagKey": _USER_TAG["Key"], "TagValue": _USER_TAG["Value"]},
        ]
    )
    key_id: str = created["KeyMetadata"]["KeyId"]
    return key_id


def test_role_roundtrip_grades_reward_1_against_the_posture_declaring_golden(
    reader: DeployedStateReader, deployed_role: str
) -> None:
    deployed = _normalized(reader, _ROLE_TYPE, deployed_role)
    outcome = grade_deployment(_registry(), _task(_ROLE_CONTRACT_TASK), _SEED, deployed)

    changed = [r for r in outcome.diff.resources if r.change is not Change.unchanged]
    assert outcome.reward is Reward.number_1, f"unexpected diff on a correct deploy: {changed!r}"


def test_role_golden_omitting_server_posture_grades_a_correct_deploy_0(
    reader: DeployedStateReader, deployed_role: str
) -> None:
    deployed = _normalized(reader, _ROLE_TYPE, deployed_role)
    outcome = grade_deployment(_registry(), _task(_ROLE_MINIMAL_TASK), _SEED, deployed)

    assert outcome.reward is Reward.number_0, (
        "the minimal role golden matched the real read -- the substrate stopped serving the "
        "server-defaulted role posture (image bump?)"
    )
    modified = [r for r in outcome.diff.resources if r.change is Change.modified]
    assert [r.address for r in modified] == [_ROLE_ADDRESS]
    diffed_paths = {d.path for d in modified[0].propertyDiffs or []}
    assert diffed_paths == set(_ROLE_SERVER_POSTURE)


def test_key_roundtrip_grades_reward_1_against_the_posture_declaring_golden(
    reader: DeployedStateReader, deployed_key: str
) -> None:
    deployed = _normalized(reader, _KEY_TYPE, deployed_key)
    outcome = grade_deployment(_registry(), _task(_KEY_CONTRACT_TASK), _SEED, deployed)

    changed = [r for r in outcome.diff.resources if r.change is not Change.unchanged]
    assert outcome.reward is Reward.number_1, f"unexpected diff on a correct deploy: {changed!r}"


def test_key_golden_omitting_server_posture_grades_a_correct_deploy_0(
    reader: DeployedStateReader, deployed_key: str
) -> None:
    deployed = _normalized(reader, _KEY_TYPE, deployed_key)
    outcome = grade_deployment(_registry(), _task(_KEY_MINIMAL_TASK), _SEED, deployed)

    assert outcome.reward is Reward.number_0, (
        "the minimal key golden matched the real read -- the substrate stopped serving the "
        "server-defaulted key posture (image bump?)"
    )
    modified = [r for r in outcome.diff.resources if r.change is Change.modified]
    assert [r.address for r in modified] == [_KEY_ADDRESS]
    diffed_paths = {d.path for d in modified[0].propertyDiffs or []}
    assert diffed_paths == set(_KEY_SERVER_POSTURE)


def test_an_untagged_role_fails_closed_on_a_real_read(reader: DeployedStateReader) -> None:
    name = _fresh_role("assayops-roundtrip-role-untagged", [_USER_TAG])
    read = reader.read_resource(_ROLE_TYPE, name)
    assert isinstance(read, DeployedResourceRead), f"expected a settled read, got {read!r}"
    with pytest.raises(AddressBridgeError):
        normalize([read])


def test_an_untagged_key_fails_closed_on_a_real_read(reader: DeployedStateReader) -> None:
    kms = _client("kms")
    key_id = kms.create_key()["KeyMetadata"]["KeyId"]
    read = reader.read_resource(_KEY_TYPE, key_id)
    assert isinstance(read, DeployedResourceRead), f"expected a settled read, got {read!r}"
    with pytest.raises(AddressBridgeError):
        normalize([read])
