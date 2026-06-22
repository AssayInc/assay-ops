"""Shared test fixtures: a real uvicorn server hosting the A-side env over HTTP + ``/ws``.

The env-server is started in a background thread on an ephemeral port so the spike's WebSocket
clients (and the TRL drive) connect over a real socket — the faithful integration path.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator

import httpx
import pytest
import uvicorn

from assayops_env_server.app import app
from assayops_env_server.cloud_state import CLOUD


@pytest.fixture(autouse=True)
def _isolate_cloud_state() -> Iterator[None]:
    # CLOUD is a module-global substrate; clear it around every test so episodes never bleed.
    CLOUD.clear()
    yield
    CLOUD.clear()


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


@pytest.fixture(scope="session")
def server_url() -> Iterator[str]:
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{base_url}/health", timeout=1.0).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:  # pragma: no cover - only hit if the server never starts
        raise RuntimeError("env-server did not become ready")

    yield base_url

    server.should_exit = True
    thread.join(timeout=10.0)
