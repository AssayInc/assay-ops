"""The per-sample LocalStack reader factory -- endpoint discovery + Cloud Control clients.

Each sample's compose sandbox runs its OWN ``localstack`` service (per-sample isolation: the
closed-world read enumerates the WHOLE substrate, so two samples can never share one), publishing
the gateway port 4566 on an ephemeral host port. The scorer runs in the eval process -- outside
every sandbox -- and discovers that endpoint from the sandbox connection's TYPED port mappings
(harness infrastructure metadata; never parsed from agent output), then builds one read-only
Cloud Control reader per Region the read scope requires.

Client shape mirrors the ``infra-local`` LocalStack smoke (the skill-validated boto3 pattern):
endpoint-pinned, LocalStack's well-known static dummy credentials, bounded timeouts, and boto3
ADAPTIVE retries -- the SDK owns the within-read throttle/5xx retry; the 7A classifier + K-run own
the POLICY for anything that surfaces past it (#45/#141).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

import boto3
from assayops_verifier.read import DeployedStateReader
from assayops_verifier.read_scope import ReadScope
from botocore.client import BaseClient
from botocore.config import Config
from inspect_ai.util import SandboxConnection, sandbox

from assayops_evals.scorer import ReaderFactory

LOCALSTACK_SERVICE = "localstack"
_LOCALSTACK_GATEWAY_PORT = 4566

# Bounded, adaptive-retry client config (see the module docstring). LocalStack serves every
# Region from the one gateway endpoint, so per-Region clients differ only in region_name.
_CLIENT_CONFIG = Config(
    retries={"total_max_attempts": 5, "mode": "adaptive"},
    connect_timeout=5,
    read_timeout=30,
)

Connect = Callable[[], Awaitable[SandboxConnection]]


def localstack_reader_factory(
    scope: ReadScope,
    *,
    service: str = LOCALSTACK_SERVICE,
    connect: Connect | None = None,
) -> ReaderFactory:
    """The production ``ReaderFactory``: discover THIS sample's LocalStack, build its readers.

    ``connect`` is injectable for hermetic tests; the default asks the current sample's sandbox
    environment named ``service`` for its connection info.
    """

    async def factory() -> Mapping[str, DeployedStateReader]:
        if connect is not None:
            connection = await connect()
        else:
            connection = await sandbox(service).connection()
        return readers_for_scope(scope, localstack_endpoint(connection))

    return factory


def localstack_endpoint(
    connection: SandboxConnection, *, container_port: int = _LOCALSTACK_GATEWAY_PORT
) -> str:
    """Resolve the sample's published LocalStack endpoint from typed port mappings (fail closed).

    A wildcard bind address (``0.0.0.0`` / ``::``) is dialed via loopback; a concrete address is
    kept. No mapping for the gateway port is a sandbox-config error -- the corpus compose file
    must publish it (``ports: ["4566"]``) -- and fails closed rather than guessing an endpoint.
    """
    for mapping in connection.ports or []:
        if mapping.container_port == container_port and mapping.protocol == "tcp":
            for host in mapping.mappings:
                # S104 false positive: comparing a REPORTED bind address, not binding to one.
                wildcard = ("", "0.0.0.0", "::")  # noqa: S104
                host_ip = "127.0.0.1" if host.host_ip in wildcard else host.host_ip
                return f"http://{host_ip}:{host.host_port}"
    raise ValueError(
        f"the sandbox connection publishes no tcp mapping for the LocalStack gateway port "
        f"{container_port} -- the corpus compose.yaml must declare 'ports: [\"{container_port}\"]' "
        f"on the localstack service (got: {connection.ports!r})"
    )


def readers_for_scope(scope: ReadScope, endpoint_url: str) -> Mapping[str, DeployedStateReader]:
    """One read-only Cloud Control reader per Region the scope's closed-world walk requires.

    The required set is the union of every coverage's enumeration Regions (REGIONAL -> all allowed
    Regions; GLOBAL -> the control Region) -- a missing Region reader would fail every episode
    closed inside ``verify()``.
    """
    regions = sorted(
        {region for coverage in scope.coverages for region in scope.regions_for(coverage)}
    )
    return {
        region: DeployedStateReader(_cloud_control_client(endpoint_url, region))
        for region in regions
    }


def _cloud_control_client(endpoint_url: str, region: str) -> BaseClient:
    return boto3.client(
        "cloudcontrol",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id="test",  # LocalStack's well-known dummy creds (not a real secret)
        aws_secret_access_key="test",  # noqa: S106
        config=_CLIENT_CONFIG,
    )
