"""LocalStack boto3 smoke for the verifier's Cloud Control read path.

``infra-local`` proves the write-isolated verifier's read path (DECISIONS.md section 1) on a
local LocalStack instead of real AWS: the verifier reads DEPLOYED state read-only via AWS Cloud
Control ``get_resource`` / ``list_resources`` -- uniform and provisioning-agnostic (brain
``references/aws-cloud-control-api``). This seeds a known S3 bucket, then reads it back through
the EXACT read API the account-B verifier (E2) uses, proving LocalStack serves it (the
``local-aws-emulator-must-prove-read-api`` rule -- prove the read API, not "S3 works"). It grounds
the verifier read-coverage spike (#80); it is NOT the verifier itself. Re-homed from the original
TS smoke (E17: the verifier read path is boto3/Python, so the smoke uses the real verifier SDK).

Scope: Cloud Control ``get_resource`` + ``list_resources`` + the ``ResourceNotFoundException``
negative-assertion path. CloudFormation server-side drift detection is also part of the read path,
but LocalStack does NOT serve ``DetectStackDrift`` ("not currently supported by LocalStack",
verified) -- drift-read coverage is the #80/E2 job against real AWS.

Cold-start: botocore's own bounded retries (``Config(retries=...)``) cover transient connection /
5xx errors while a service warms after the gateway reports healthy -- the library's mechanism, no
hand-rolled loop (verified clean across cold ``just up`` cycles). Standard mode does NOT retry a
4xx like ``ResourceNotFoundException``, so the negative test fails fast on the modeled error. A
read-after-create 404 is a non-issue here -- LocalStack's S3 ``CreateBucket`` is synchronous (the
read sees the bucket immediately, verified); real-AWS eventual consistency is the #80/E2 job, like
drift. Runs only via ``just smoke`` against a running LocalStack (the ``localstack-smoke.yml``
workflow), never in the hermetic ``bun run verify`` gate -- the package exposes a ``smoke`` script,
not ``test``.
"""

from __future__ import annotations

import json

import pytest
from botocore.client import BaseClient
from localstack_clients import client as _client

_BUCKET = "assayops-read-smoke-bucket"
_MISSING = "assayops-read-smoke-absent-404"
_BUCKET_TYPE = "AWS::S3::Bucket"


@pytest.fixture(scope="module")
def cloud_control() -> BaseClient:
    """The Cloud Control client the verifier reads deployed state through (one per module)."""
    return _client("cloudcontrol")


@pytest.fixture(scope="module")
def deployed_bucket() -> str:
    """Deploy a known S3 bucket (idempotent) and return its identifier -- the read target."""
    s3 = _client("s3")
    try:
        s3.create_bucket(Bucket=_BUCKET)
    except (s3.exceptions.BucketAlreadyOwnedByYou, s3.exceptions.BucketAlreadyExists):
        pass  # already deployed -- fine
    return _BUCKET


def test_cloud_control_get_resource_reads_deployed_bucket(
    cloud_control: BaseClient, deployed_bucket: str
) -> None:
    """get_resource returns the live state of one deployed resource -- the atomic assertion."""
    description = cloud_control.get_resource(TypeName=_BUCKET_TYPE, Identifier=deployed_bucket)[
        "ResourceDescription"
    ]

    assert description["Identifier"] == deployed_bucket
    properties = json.loads(description["Properties"])
    assert isinstance(properties, dict)
    assert properties["BucketName"] == deployed_bucket


def test_cloud_control_list_resources_enumerates_deployed_bucket(
    cloud_control: BaseClient, deployed_bucket: str
) -> None:
    """list_resources enumerates all resources of a type -- the discovery primitive (paginated)."""
    paginator = cloud_control.get_paginator("list_resources")
    identifiers = [
        d["Identifier"]
        for page in paginator.paginate(TypeName=_BUCKET_TYPE)
        for d in page.get("ResourceDescriptions", [])
    ]

    assert deployed_bucket in identifiers


def test_cloud_control_get_resource_missing_is_resource_not_found(
    cloud_control: BaseClient, deployed_bucket: str
) -> None:
    """A missing resource raises ResourceNotFoundException (the negative-assertion path).

    ``deployed_bucket`` is requested so the contrast is real -- a known bucket exists, yet this
    distinct identifier does not -- and so this read is not the first (cold) call to the service.
    """
    with pytest.raises(cloud_control.exceptions.ResourceNotFoundException):
        cloud_control.get_resource(TypeName=_BUCKET_TYPE, Identifier=_MISSING)


# --- Terraform-adapter tag bridge (#35 / #80): Cloud Control must surface `assayops:address` ---

_ADDRESS_TAG = "assayops:address"
_ADDRESS_VALUE = "primary_bucket"
_TAGGED_BUCKET = "assayops-read-smoke-tagged"


@pytest.fixture(scope="module")
def tagged_bucket() -> str:
    """Deploy an S3 bucket tagged with `assayops:address` via the S3 API (the Terraform path)."""
    s3 = _client("s3")
    try:
        s3.create_bucket(Bucket=_TAGGED_BUCKET)
    except (s3.exceptions.BucketAlreadyOwnedByYou, s3.exceptions.BucketAlreadyExists):
        pass  # already deployed -- fine
    s3.put_bucket_tagging(
        Bucket=_TAGGED_BUCKET,
        Tagging={"TagSet": [{"Key": _ADDRESS_TAG, "Value": _ADDRESS_VALUE}]},
    )
    return _TAGGED_BUCKET


def test_cloud_control_get_resource_returns_the_assayops_address_tag(
    cloud_control: BaseClient, tagged_bucket: str
) -> None:
    """The #35 adapter bridge proof: Cloud Control GetResource exposes `assayops:address` at the
    AWS::S3::Bucket schema tagProperty (`Tags`) -- what the adapter's S3 registration relies on."""
    description = cloud_control.get_resource(TypeName=_BUCKET_TYPE, Identifier=tagged_bucket)[
        "ResourceDescription"
    ]
    properties = json.loads(description["Properties"])
    assert isinstance(properties, dict)
    tags = properties.get("Tags", [])
    assert {"Key": _ADDRESS_TAG, "Value": _ADDRESS_VALUE} in tags
