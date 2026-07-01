"""Shared LocalStack client factory for the infra-local smokes.

Cost-free LocalStack dev loop: no real AWS, static dummy credentials, the localhost gateway. One
client recipe for every smoke module so the boundary config (bounded botocore retries, path-style
S3 addressing) stays single-sourced.
"""

from __future__ import annotations

import os

import boto3
from botocore.client import BaseClient
from botocore.config import Config

ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = "us-east-1"

# Let botocore handle transient retries (bounded): standard mode retries connection / 5xx errors
# while a service warms, but NOT a 4xx like ResourceNotFoundException (so a negative test fails
# fast on the modeled error). Bounded timeouts stop a hung LocalStack blowing the test budget.
CONFIG = Config(
    retries={"total_max_attempts": 5, "mode": "standard"},
    connect_timeout=5,
    read_timeout=10,
    # LocalStack needs path-style S3 addressing (the original TS smoke's forcePathStyle).
    s3={"addressing_style": "path"},
)


def client(service: str) -> BaseClient:
    """A boto3 client pinned at the LocalStack gateway with static dummy credentials."""
    return boto3.client(
        service,
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id="test",  # LocalStack's well-known dummy creds (not a real secret)
        aws_secret_access_key="test",  # noqa: S106
        config=CONFIG,
    )
