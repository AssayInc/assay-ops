"""A faithful, recording fake of the boto3 cloudcontrol client -- read operations only.

Mirrors the real Cloud Control read shapes (primary-doc-verified, and proven against LocalStack by
``infra-local``): ``get_resource`` returns a ``ResourceDescription`` with an ``Identifier`` and a
JSON-string ``Properties``; a ``list_resources`` page returns ``ResourceDescriptions`` (each the
same) plus an optional ``NextToken``. The fake raises real botocore ``ClientError``-family
exceptions: a modeled ``ResourceNotFoundException`` for an absent resource, a throttling
``ClientError`` for an unreadable one.

It records every operation invoked so a test can prove the read harness performs READ operations
only -- the moat (DECISIONS.md section 1/8, T1): the verifier never writes, mutates, or runs agent
code. Any operation not defined here is recorded and fails loudly, so a regression that adds a
write or STS-assume call is caught.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator

from botocore.exceptions import ClientError, EndpointConnectionError


# botocore is untyped (ClientError is Any), so mypy cannot statically verify the subclass; this IS
# a ClientError subclass at runtime, mirroring boto3's modeled cloudcontrol
# ResourceNotFoundException.
class FakeResourceNotFoundException(ClientError):  # type: ignore[misc]
    """Mirror of boto3's modeled cloudcontrol ResourceNotFoundException (a ClientError subclass)."""


class _Exceptions:
    ResourceNotFoundException = FakeResourceNotFoundException


def _error(error_class: type[ClientError], code: str, operation: str) -> ClientError:
    return error_class({"Error": {"Code": code, "Message": f"{code} (fake)"}}, operation)


class FakeCloudControlClient:
    """A recording, read-only fake of the boto3 cloudcontrol client.

    ``resources`` maps ``(type_name, identifier)`` to a property dict (the parsed ``Properties``).
    Other id sets are listable but fail on get: ``unreadable`` (throttling ``ClientError`` -- a
    TRANSIENT under #141), ``network_error`` (``EndpointConnectionError`` -- TRANSIENT),
    ``access_denied`` (``AccessDeniedException`` -- a GENUINE failure, fail closed), ``malformed``
    (non-JSON ``Properties`` -- genuine), ``vanished`` (``ResourceNotFoundException`` -- a list/get
    race, EVENTUAL_CONSISTENCY). ``list_throttle`` / ``list_error`` (type-name sets) make
    ``list_resources`` raise a throttling / genuine ``ClientError`` for that type. ``page_size``
    paginates.
    """

    def __init__(
        self,
        resources: dict[tuple[str, str], dict[str, object]] | None = None,
        *,
        unreadable: set[tuple[str, str]] | None = None,
        access_denied: set[tuple[str, str]] | None = None,
        malformed: set[tuple[str, str]] | None = None,
        network_error: set[tuple[str, str]] | None = None,
        vanished: set[tuple[str, str]] | None = None,
        list_throttle: set[str] | None = None,
        list_error: set[str] | None = None,
        page_size: int | None = None,
    ) -> None:
        self.invoked: list[tuple[str, dict[str, object]]] = []
        self._resources = dict(resources or {})
        self._unreadable = set(unreadable or set())
        self._access_denied = set(access_denied or set())
        self._malformed = set(malformed or set())
        self._network_error = set(network_error or set())
        self._vanished = set(vanished or set())
        self._list_throttle = set(list_throttle or set())
        self._list_error = set(list_error or set())
        self._page_size = page_size
        self.exceptions = _Exceptions

    @property
    def invoked_operations(self) -> set[str]:
        return {operation for operation, _ in self.invoked}

    def get_resource(self, *, TypeName: str, Identifier: str) -> dict[str, object]:  # noqa: N803
        self.invoked.append(("get_resource", {"TypeName": TypeName, "Identifier": Identifier}))
        key = (TypeName, Identifier)
        if key in self._unreadable:
            raise _error(ClientError, "ThrottlingException", "GetResource")
        if key in self._access_denied:
            raise _error(ClientError, "AccessDeniedException", "GetResource")
        if key in self._network_error:
            raise EndpointConnectionError(endpoint_url="https://cloudcontrol.local")
        if key in self._malformed:
            # A response whose Properties is not valid JSON -- the harness must fail closed on it.
            return {
                "TypeName": TypeName,
                "ResourceDescription": {"Identifier": Identifier, "Properties": "<<not json>>"},
            }
        if key not in self._resources:
            raise _error(FakeResourceNotFoundException, "ResourceNotFoundException", "GetResource")
        return {
            "TypeName": TypeName,
            "ResourceDescription": {
                "Identifier": Identifier,
                "Properties": json.dumps(self._resources[key]),
            },
        }

    def get_paginator(self, operation_name: str) -> _FakePaginator:
        self.invoked.append(("get_paginator", {"operation_name": operation_name}))
        if operation_name != "list_resources":
            raise AssertionError(f"only list_resources is paginated, got {operation_name!r}")
        return _FakePaginator(self)

    def _list_resources_pages(self, *, TypeName: str) -> Iterator[dict[str, object]]:  # noqa: N803
        self.invoked.append(("list_resources", {"TypeName": TypeName}))
        if TypeName in self._list_throttle:
            raise _error(ClientError, "ThrottlingException", "ListResources")
        if TypeName in self._list_error:
            raise _error(ClientError, "InvalidRequestException", "ListResources")
        listable = (
            set(self._resources)
            | self._unreadable
            | self._access_denied
            | self._malformed
            | self._network_error
            | self._vanished
        )
        identifiers = sorted(ident for (tn, ident) in listable if tn == TypeName)
        descriptions: list[dict[str, object]] = [
            {
                "Identifier": ident,
                "Properties": json.dumps(self._resources.get((TypeName, ident), {})),
            }
            for ident in identifiers
        ]
        size = self._page_size or max(len(descriptions), 1)
        chunks = [descriptions[i : i + size] for i in range(0, len(descriptions), size)] or [[]]
        for index, chunk in enumerate(chunks):
            page: dict[str, object] = {"TypeName": TypeName, "ResourceDescriptions": chunk}
            if index < len(chunks) - 1:
                page["NextToken"] = f"token-{index + 1}"
            yield page

    def __getattr__(self, name: str) -> Callable[..., object]:
        if name.startswith("__"):
            raise AttributeError(name)

        def _forbidden(*args: object, **kwargs: object) -> object:
            self.invoked.append((name, {"args": args, "kwargs": kwargs}))
            raise AssertionError(f"read harness invoked a non-read client operation: {name!r}")

        return _forbidden


class _FakePaginator:
    def __init__(self, client: FakeCloudControlClient) -> None:
        self._client = client

    def paginate(self, *, TypeName: str) -> Iterator[dict[str, object]]:  # noqa: N803
        yield from self._client._list_resources_pages(TypeName=TypeName)
