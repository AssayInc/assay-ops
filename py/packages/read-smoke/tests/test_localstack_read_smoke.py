"""LocalStack boto3 smoke for the verifier's Cloud Control read path.

The Python/boto3 counterpart to ``infra-local``'s TS ``smoke.test.ts`` (DECISIONS.md
section 1): the write-isolated verifier reads DEPLOYED state read-only via AWS Cloud
Control ``get_resource`` / ``list_resources`` — uniform and provisioning-agnostic (brain
``references/aws-cloud-control-api``). This seeds a known S3 bucket, then reads it back
through the EXACT read API the real account-B verifier (E2) uses, proving LocalStack
serves it (the ``local-aws-emulator-must-prove-read-api`` rule — prove the read API, not
"S3 works"). It is the read-path seed that grounds the verifier read-coverage spike (#80);
it is NOT the verifier itself.

Scope: Cloud Control ``get_resource`` + ``list_resources`` + the ``ResourceNotFoundException``
negative-assertion path. CloudFormation server-side drift detection is also part of the
read path (DECISIONS.md section 1), but LocalStack does NOT serve ``DetectStackDrift``
("not currently supported by LocalStack", verified) — drift-read coverage is the #80/E2
job against real AWS.

Runs only via ``just smoke-py`` against a running LocalStack (the ``localstack-smoke.yml``
workflow), never in the hermetic ``bun run verify`` gate — the package exposes a ``smoke``
script, not ``test`` (mirrors ``infra-local``).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable

import boto3
import pytest
from botocore.client import BaseClient
from botocore.config import Config

# Cost-free LocalStack dev loop: no real AWS, static dummy credentials, the localhost gateway.
_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
_REGION = "us-east-1"
_BUCKET = "assayops-read-smoke-bucket"
_MISSING = "assayops-read-smoke-absent-404"
_BUCKET_TYPE = "AWS::S3::Bucket"

# Drive retry timing from this module, not the SDK: one attempt + bounded timeouts, so a hung
# (vs refused) LocalStack cannot stack the SDK's default retries against the test budget. Mirrors
# infra-local/smoke.test.ts.
_CONFIG = Config(
    retries={"total_max_attempts": 1},
    connect_timeout=5,
    read_timeout=5,
    # LocalStack needs path-style S3 addressing (the TS smoke's forcePathStyle).
    s3={"addressing_style": "path"},
)


def _client(service: str) -> BaseClient:
    """A boto3 client pinned at the LocalStack gateway with static dummy credentials."""
    return boto3.client(
        service,
        endpoint_url=_ENDPOINT,
        region_name=_REGION,
        aws_access_key_id="test",  # LocalStack's well-known dummy creds (not a real secret)
        aws_secret_access_key="test",  # noqa: S106
        config=_CONFIG,
    )


def _with_retry[T](operation: Callable[[], T], *, attempts: int = 6) -> T:
    """Retry a cold-start flake a few times, then ALWAYS rethrow the last error.

    LocalStack can briefly fail while it warms a service after the gateway reports healthy.
    Always rethrows so a genuine failure still fails the smoke — never a false pass.
    """
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as error:  # noqa: BLE001 — a smoke retries any transient cold-start error
            last_error = error
            if attempt < attempts - 1:
                time.sleep(1)
    assert last_error is not None
    raise last_error


def _seed_bucket(bucket: str) -> None:
    """Deploy a known S3 bucket (idempotent against an already-warm stack)."""
    s3 = _client("s3")

    def _create() -> None:
        try:
            s3.create_bucket(Bucket=bucket)
        except (s3.exceptions.BucketAlreadyOwnedByYou, s3.exceptions.BucketAlreadyExists):
            pass  # already deployed — fine

    _with_retry(_create)


def test_cloud_control_get_resource_reads_deployed_bucket() -> None:
    """get_resource returns the live state of one deployed resource — the atomic assertion."""
    _seed_bucket(_BUCKET)
    cloud_control = _client("cloudcontrol")

    description = _with_retry(
        lambda: cloud_control.get_resource(TypeName=_BUCKET_TYPE, Identifier=_BUCKET)[
            "ResourceDescription"
        ]
    )

    assert description["Identifier"] == _BUCKET
    properties = json.loads(description["Properties"])
    assert isinstance(properties, dict)
    assert properties["BucketName"] == _BUCKET


def test_cloud_control_list_resources_enumerates_deployed_bucket() -> None:
    """list_resources enumerates all resources of a type — the discovery primitive (paginated)."""
    _seed_bucket(_BUCKET)
    cloud_control = _client("cloudcontrol")

    def _list_identifiers() -> list[str]:
        paginator = cloud_control.get_paginator("list_resources")
        identifiers: list[str] = []
        for page in paginator.paginate(TypeName=_BUCKET_TYPE):
            identifiers.extend(d["Identifier"] for d in page.get("ResourceDescriptions", []))
        return identifiers

    assert _BUCKET in _with_retry(_list_identifiers)


def test_cloud_control_get_resource_missing_is_resource_not_found() -> None:
    """A missing resource raises ResourceNotFoundException (the negative-assertion path)."""
    _seed_bucket(_BUCKET)
    cloud_control = _client("cloudcontrol")

    # Warm the service on a known-present resource, so the missing-id read below raises the expected
    # ResourceNotFoundException deterministically rather than a cold-start transient.
    _with_retry(lambda: cloud_control.get_resource(TypeName=_BUCKET_TYPE, Identifier=_BUCKET))

    with pytest.raises(cloud_control.exceptions.ResourceNotFoundException):
        cloud_control.get_resource(TypeName=_BUCKET_TYPE, Identifier=_MISSING)
