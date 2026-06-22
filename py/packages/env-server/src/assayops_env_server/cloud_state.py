"""The deployed-resources substrate — a spike stand-in for real AWS resources.

The A-side env "deploys" to this store (the agent's authorized job); the account-B verifier reads
it **read-only, by ``trajectory_id``** (the independent cross-account read). It holds **state, never
rewards** — the grade is computed account-B from this ground truth, not from the agent-reachable
observation. This is what makes the reward boundary non-tautological: the agent influences what is
deployed, but cannot make the verifier read anything other than the real deployed state, and cannot
forge the grade. The real verifier reads actual deployed cloud resources via boto3 Cloud Control
(out of spike scope — #80/E2); ``CLOUD`` is the minimal substitute that preserves the read channel.
"""

from __future__ import annotations

from typing import Any


class DeployedResources:
    """Ground-truth deployed state, keyed by ``trajectory_id`` (one episode's deploy namespace)."""

    def __init__(self) -> None:
        self._by_trajectory: dict[str, dict[str, Any]] = {}

    def deploy(self, trajectory_id: str, resource_type: str, properties: dict[str, Any]) -> None:
        self._by_trajectory.setdefault(trajectory_id, {})[resource_type] = dict(properties)

    def read(self, trajectory_id: str) -> dict[str, Any]:
        """A read-only snapshot of the resources deployed under ``trajectory_id``."""
        return {
            key: dict(value) for key, value in self._by_trajectory.get(trajectory_id, {}).items()
        }

    def clear(self) -> None:
        self._by_trajectory.clear()


# Module-level singleton: the shared "cloud" both trust domains touch — A-side writes (deploys),
# account-B reads (grades). Per-trajectory_id keys keep concurrent episodes isolated.
CLOUD = DeployedResources()
