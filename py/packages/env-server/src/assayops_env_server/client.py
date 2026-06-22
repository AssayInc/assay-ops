"""The OpenEnv WebSocket client for the deploy-verify env.

Subclasses ``EnvClient`` and supplies the three serialization hooks. This is the same
``EnvClient`` transport TRL's OpenEnv integration drives, so the spike exercises the real path.
"""

from __future__ import annotations

from typing import Any

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from assayops_env_server.models import DeployAction, DeployObservation, EnvState


class DeployVerifyEnvClient(
    EnvClient[DeployAction, DeployObservation, EnvState],  # type: ignore[misc]
):
    def _step_payload(self, action: DeployAction) -> dict[str, Any]:
        payload: dict[str, Any] = action.model_dump()
        return payload

    def _parse_result(self, payload: dict[str, Any]) -> StepResult[DeployObservation]:
        observation_fields = payload.get("observation", {})
        observation = DeployObservation(
            done=payload.get("done", False),
            reward=payload.get("reward"),
            **observation_fields,
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict[str, Any]) -> EnvState:
        return EnvState(**payload)
