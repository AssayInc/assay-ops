"""The deployed-resources substrate — a spike stand-in for the verifier's independent read.

The A-side env "deploys" to this store (the agent's authorized job); the account-B verifier reads it
**read-only, by ``trajectory_id``** — the independent read channel, **not** the agent-reachable
observation. That decoupling is the point: the grade depends on what this substrate holds, never on
what the agent reports.

Scope (a spike stand-in, not the production read path): it is a **lossless echo** of the deploy
request, so it does **not** model deploy-vs-requested divergence — the real verifier reads actual
deployed cloud resources via boto3 Cloud Control (#80/E2), which can diverge from the request. It is
also **test-lifetime only** (an in-process dict cleared between tests); the real boto3 read has no
such accumulation. Access is lock-guarded so a read never observes an in-flight deploy.
"""

from __future__ import annotations

import threading
from typing import Any


class DeployedResources:
    """Ground-truth deployed state, keyed by ``trajectory_id`` (one episode's deploy namespace)."""

    def __init__(self) -> None:
        self._by_trajectory: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def deploy(self, trajectory_id: str, resource_type: str, properties: dict[str, Any]) -> None:
        with self._lock:
            self._by_trajectory.setdefault(trajectory_id, {})[resource_type] = dict(properties)

    def read(self, trajectory_id: str) -> dict[str, Any]:
        """A read-only, atomic snapshot of the resources deployed under ``trajectory_id``."""
        with self._lock:
            deployed = self._by_trajectory.get(trajectory_id, {})
            return {key: dict(value) for key, value in deployed.items()}

    def clear(self) -> None:
        with self._lock:
            self._by_trajectory.clear()


# Module-level singleton: the shared "cloud" both trust domains touch — A-side writes (deploys),
# account-B reads (grades). Per-trajectory_id keys keep concurrent episodes isolated.
CLOUD = DeployedResources()
