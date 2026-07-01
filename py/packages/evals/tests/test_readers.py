"""#176 leg 3: the per-sample LocalStack reader factory + endpoint discovery.

Each sample runs its OWN LocalStack service (per-sample isolation: the closed-world read
enumerates the whole substrate), publishing 4566 on an ephemeral host port. The scorer discovers
that endpoint from the sandbox connection's typed port mappings (never by parsing agent output)
and builds one account-B-style Cloud Control reader per required Region. Discovery is pure +
injectable, so these tests are hermetic (no Docker).
"""

from __future__ import annotations

import asyncio

import pytest
from assayops_verifier.read import DeployedStateReader
from assayops_verifier.read_scope import Listability, ReadScope, RegionScope, TypeCoverage
from inspect_ai.util import SandboxConnection

from assayops_evals.readers import (
    localstack_endpoint,
    localstack_reader_factory,
    readers_for_scope,
)

S3 = "AWS::S3::Bucket"
ROLE = "AWS::IAM::Role"


def _connection(ports: list[dict[str, object]] | None) -> SandboxConnection:
    return SandboxConnection.model_validate(
        {
            "type": "docker",
            "command": "docker exec -it inspect-abc-localstack-1 bash -l",
            "container": "inspect-abc-localstack-1",
            "ports": ports,
        }
    )


def _published(host_port: int = 55123, host_ip: str = "0.0.0.0") -> list[dict[str, object]]:
    return [
        {
            "container_port": 4566,
            "protocol": "tcp",
            "mappings": [{"host_ip": host_ip, "host_port": host_port}],
        }
    ]


def test_localstack_endpoint_resolves_the_published_port() -> None:
    endpoint = localstack_endpoint(_connection(_published(host_port=49321)))

    assert endpoint == "http://127.0.0.1:49321"


@pytest.mark.parametrize("wildcard", ["0.0.0.0", "", "::"])
def test_localstack_endpoint_dials_loopback_for_every_wildcard_bind(wildcard: str) -> None:
    # Docker reports a wildcard bind address (0.0.0.0 / '' / IPv6 '::') that can't be dialed
    # directly -- all must normalize to loopback, not just the 0.0.0.0 default the base test uses.
    endpoint = localstack_endpoint(_connection(_published(host_ip=wildcard)))

    assert endpoint == "http://127.0.0.1:55123"


def test_localstack_endpoint_keeps_a_concrete_host_ip() -> None:
    endpoint = localstack_endpoint(_connection(_published(host_ip="192.168.5.9")))

    assert endpoint == "http://192.168.5.9:55123"


def test_localstack_endpoint_fails_closed_on_a_non_tcp_gateway_mapping() -> None:
    udp = [
        {
            "container_port": 4566,
            "protocol": "udp",
            "mappings": [{"host_ip": "0.0.0.0", "host_port": 5}],
        }
    ]
    with pytest.raises(ValueError, match="4566"):
        localstack_endpoint(_connection(udp))


def test_localstack_endpoint_fails_closed_on_an_empty_host_mapping() -> None:
    # A gateway-port entry whose host mappings list is empty (published but not bound) must fall
    # through to the fail-closed error, never return a half-formed endpoint.
    unbound = [{"container_port": 4566, "protocol": "tcp", "mappings": []}]
    with pytest.raises(ValueError, match="4566"):
        localstack_endpoint(_connection(unbound))


def test_localstack_endpoint_fails_closed_without_a_mapping() -> None:
    with pytest.raises(ValueError, match="4566"):
        localstack_endpoint(_connection([]))


def test_localstack_endpoint_fails_closed_on_no_ports() -> None:
    with pytest.raises(ValueError, match="4566"):
        localstack_endpoint(_connection(None))


def _scope(*coverages: TypeCoverage, regions: tuple[str, ...] = ("us-east-1",)) -> ReadScope:
    return ReadScope(coverages=tuple(coverages), allowed_regions=regions)


def test_readers_for_scope_builds_one_reader_per_allowed_region() -> None:
    scope = _scope(
        TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE),
        regions=("us-east-1", "eu-west-1"),
    )

    readers = readers_for_scope(scope, "http://127.0.0.1:49321")

    assert set(readers) == {"us-east-1", "eu-west-1"}
    for region, reader in readers.items():
        assert isinstance(reader, DeployedStateReader)
        assert reader.client.meta.endpoint_url == "http://127.0.0.1:49321"
        assert reader.client.meta.region_name == region


def test_readers_for_scope_includes_the_global_control_region() -> None:
    # A GLOBAL type is enumerated at its control Region even when that Region is not an allowed
    # deploy Region -- without a reader there, verify() would fail closed on every episode. The
    # required set is exactly the union of the coverages' enumeration Regions (what
    # read_closed_world walks), so an allowed Region no coverage enumerates needs no reader.
    scope = _scope(
        TypeCoverage(ROLE, RegionScope.GLOBAL, Listability.DIRECTLY_LISTABLE),
        regions=("eu-west-1",),
    )

    readers = readers_for_scope(scope, "http://127.0.0.1:49321")

    assert set(readers) == {"us-east-1"}


def test_localstack_reader_factory_discovers_through_the_injected_connect() -> None:
    scope = _scope(TypeCoverage(S3, RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE))

    async def connect() -> SandboxConnection:
        return _connection(_published(host_port=45991))

    factory = localstack_reader_factory(scope, connect=connect)

    async def build() -> dict[str, DeployedStateReader]:
        return dict(await factory())

    readers = asyncio.run(build())

    assert set(readers) == {"us-east-1"}
    assert readers["us-east-1"].client.meta.endpoint_url == "http://127.0.0.1:45991"
