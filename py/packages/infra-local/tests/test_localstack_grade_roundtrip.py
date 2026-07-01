"""LocalStack adapter<->golden grade round-trip -- the corpus contract, pinned to a real read.

The hermetic ``adapter-terraform`` grade tests are green with BOTH sides synthetic, so they cannot
catch a golden whose shape diverges from what a real Cloud Control read returns. This smoke closes
that gap end-to-end through the verifier's PRODUCTION chain: deploy a tagged bucket on LocalStack ->
``DeployedStateReader.read_resource`` (the account-B read harness) -> adapter ``normalize``
(``default_registry``) -> ``grade_deployment`` (golden regenerated from a synthetic registry) ->
``reward 1``. It pins the two corpus-contract requirements every task author (the private corpus)
must honor:

1. **Deploy-tag bridge:** every graded resource deploys tagged ``assayops:address = <its logical
   address>`` -- the same logical address the task's golden builder emits (missing/duplicate/
   malformed fails closed in the adapter).
2. **Goldens declare server-defaulted posture:** a real ``AWS::S3::Bucket`` read returns posture
   blocks the deploy never set -- ``BucketEncryption`` (SSE-S3 is every bucket's base encryption
   since 2023-01-05), ``PublicAccessBlockConfiguration`` (on by default for new buckets),
   ``OwnershipControls`` (``BucketOwnerEnforced`` default), ``AbacStatus`` (``Disabled`` default;
   a writable property in the AWS::S3::Bucket schema, NOT readOnly) -- all AWS defaults per the S3
   user guide, and LocalStack mirrors them. The reward diff is symmetric, so a golden omitting a
   present block grades a CORRECT deploy ``reward 0`` (safe direction, broken signal): the golden
   makes intent-bearing defaults explicit (``NORMALIZATION.md``); dropping them on the deployed
   side instead would be the forge vector.

The golden properties are DECLARED constants (authored intent), never computed from the read --
computing them would make the round-trip a tautology that grades the read against itself. That also
makes this a regression canary on the pinned LocalStack image: if an image bump changes the served
posture/shape, the reward-1 test fails loudly and the contract note gets re-pinned deliberately.
Synthetic fixtures only -- the real per-task golden builders live in the private corpus store
(DECISIONS.md I11 residency), never in-repo.

Runs only via ``just smoke`` against a running LocalStack (the ``localstack-smoke.yml`` workflow),
never in the hermetic ``bun run verify`` gate.
"""

from __future__ import annotations

import pytest
from assayops_adapter_terraform import ADDRESS_TAG, DeployedResourceRead, normalize
from assayops_contracts import Change, Reward, TaskSpec, Tool
from assayops_diff_ir import NormalizedState
from assayops_verifier import GoldenContext, GoldenRegistry, GoldenResource, grade_deployment
from assayops_verifier.read import DeployedStateReader
from localstack_clients import client as _client

_BUCKET_TYPE = "AWS::S3::Bucket"
_BUCKET = "assayops-grade-roundtrip"
_ADDRESS = "graded_bucket"
_USER_TAG = {"Key": "team", "Value": "assay"}
_SEED = "seed-155"

# What the task author explicitly deploys (and would naively declare in the golden).
_AUTHORED_PROPERTIES: dict[str, object] = {
    "BucketName": _BUCKET,
    "Tags": [_USER_TAG],
    "VersioningConfiguration": {"Status": "Enabled"},
}

# What the server ADDS to a real read without the deploy ever setting it -- the posture the
# corpus contract requires every S3 golden to declare explicitly (values = the AWS new-bucket
# defaults, which the pinned LocalStack image mirrors).
_SERVER_DEFAULTED_POSTURE: dict[str, object] = {
    "AbacStatus": "Disabled",
    "BucketEncryption": {
        "ServerSideEncryptionConfiguration": [
            {
                "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                "BucketKeyEnabled": False,
            }
        ]
    },
    "OwnershipControls": {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]},
    "PublicAccessBlockConfiguration": {
        "BlockPublicAcls": True,
        "BlockPublicPolicy": True,
        "IgnorePublicAcls": True,
        "RestrictPublicBuckets": True,
    },
}

_CONTRACT_TASK_ID = "synthetic-roundtrip-contract"
_MINIMAL_TASK_ID = "synthetic-roundtrip-minimal"


def _contract_builder(_ctx: GoldenContext) -> list[GoldenResource]:
    # The #155-contract golden: authored intent PLUS the server-defaulted posture, explicit.
    return [
        GoldenResource(
            address=_ADDRESS,
            type=_BUCKET_TYPE,
            properties={**_AUTHORED_PROPERTIES, **_SERVER_DEFAULTED_POSTURE},
        )
    ]


def _minimal_builder(_ctx: GoldenContext) -> list[GoldenResource]:
    # The pre-contract trap: only what the author explicitly deployed. Correct against a synthetic
    # read; grades reward 0 against a REAL read (the posture gap this smoke exists to pin).
    return [GoldenResource(address=_ADDRESS, type=_BUCKET_TYPE, properties=_AUTHORED_PROPERTIES)]


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(_CONTRACT_TASK_ID, _contract_builder)
    registry.register(_MINIMAL_TASK_ID, _minimal_builder)
    return registry


def _task(task_id: str) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        title="Synthetic S3 grade round-trip",
        description="Deploy a tagged, versioned S3 bucket (engine-validation fixture).",
        tool=Tool.terraform,
        seed=_SEED,
    )


@pytest.fixture(scope="module")
def reader() -> DeployedStateReader:
    """The verifier's production read harness over a LocalStack Cloud Control client."""
    return DeployedStateReader(client=_client("cloudcontrol"))


@pytest.fixture(scope="module")
def deployed_bucket() -> str:
    """Deploy the graded bucket per the corpus deploy contract (idempotent puts, so re-runs and
    the module's two tests see identical state): ``assayops:address`` tag + a user tag +
    versioning Enabled. Encryption / public-access / ownership / ABAC are deliberately NOT set --
    the server defaults them, which is exactly the contract gap under test."""
    s3 = _client("s3")
    try:
        s3.create_bucket(Bucket=_BUCKET)
    except (s3.exceptions.BucketAlreadyOwnedByYou, s3.exceptions.BucketAlreadyExists):
        pass  # already deployed -- fine
    s3.put_bucket_tagging(
        Bucket=_BUCKET,
        Tagging={"TagSet": [{"Key": ADDRESS_TAG, "Value": _ADDRESS}, _USER_TAG]},
    )
    s3.put_bucket_versioning(Bucket=_BUCKET, VersioningConfiguration={"Status": "Enabled"})
    return _BUCKET


def _normalized_deployed_state(reader: DeployedStateReader, identifier: str) -> NormalizedState:
    read = reader.read_resource(_BUCKET_TYPE, identifier)
    assert isinstance(read, DeployedResourceRead), f"expected a settled read, got {read!r}"
    return normalize([read])


def test_roundtrip_grades_reward_1_against_the_posture_declaring_golden(
    reader: DeployedStateReader, deployed_bucket: str
) -> None:
    """The corpus-contract AC: real read -> adapter -> grade == reward 1 for a correct deploy."""
    deployed = _normalized_deployed_state(reader, deployed_bucket)
    outcome = grade_deployment(_registry(), _task(_CONTRACT_TASK_ID), _SEED, deployed)

    changed = [r for r in outcome.diff.resources if r.change is not Change.unchanged]
    assert outcome.reward is Reward.number_1, f"unexpected diff on a correct deploy: {changed!r}"


def test_golden_omitting_server_posture_grades_a_correct_deploy_0(
    reader: DeployedStateReader, deployed_bucket: str
) -> None:
    """The negative control -- the exact gap the contract exists to close (and the proof the
    reward-1 test is not vacuous): a golden declaring only the authored intent grades the SAME
    correct deploy reward 0, with the diff naming precisely the server-defaulted posture blocks."""
    deployed = _normalized_deployed_state(reader, deployed_bucket)
    outcome = grade_deployment(_registry(), _task(_MINIMAL_TASK_ID), _SEED, deployed)

    assert outcome.reward is Reward.number_0
    modified = [r for r in outcome.diff.resources if r.change is Change.modified]
    assert [r.address for r in modified] == [_ADDRESS]
    diffed_paths = {d.path for d in modified[0].propertyDiffs or []}
    assert diffed_paths == set(_SERVER_DEFAULTED_POSTURE)
