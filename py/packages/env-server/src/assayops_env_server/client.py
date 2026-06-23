"""The OpenEnv WebSocket client for the deploy-verify env.

Subclasses ``EnvClient`` and supplies the three serialization hooks. This is the same
``EnvClient`` transport TRL's OpenEnv integration drives, so the spike exercises the real path.
"""

from __future__ import annotations

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from assayops_env_server.models import DeployAction, DeployObservation, EnvState


class DeployVerifyEnvClient(
    EnvClient[DeployAction, DeployObservation, EnvState],  # type: ignore[misc]
):
    def _step_payload(self, action: DeployAction) -> dict[str, object]:
        payload: dict[str, object] = action.model_dump()
        return payload

    def _parse_result(self, payload: dict[str, object]) -> StepResult[DeployObservation]:
        # Wire payload is untyped JSON; narrow the nested object before unpacking it (Pydantic then
        # validates). `object` is Python's `unknown` — it must be narrowed, never spread blind.
        raw_observation = payload.get("observation", {})
        observation_fields: dict[str, object] = (
            raw_observation if isinstance(raw_observation, dict) else {}
        )
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

    def _parse_state(self, payload: dict[str, object]) -> EnvState:
        return EnvState(**payload)
