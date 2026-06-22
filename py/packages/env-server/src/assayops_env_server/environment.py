"""The A-side deploy-verify OpenEnv ``Environment``.

A toy AssayOps episode: the agent issues deploy actions that accumulate a ``deployed_state``;
a ``__commit__`` action ends the episode. This module is the agent-reachable surface, so it
**never computes the graded reward** — every ``step()``/terminal reward is ``0.0`` (a zero
shaping signal). The graded ``reward in {0, 1}`` is produced account-B, read-only and out-of-band,
joined by ``trajectory_id`` (DECISIONS.md §8 + I5). There is deliberately **no rubric** attached
(OpenEnv's environment-owned-reward mechanism), because that is exactly what the boundary forbids.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

from assayops_env_server.models import (
    COMMIT_RESOURCE_TYPE,
    DeployAction,
    DeployObservation,
    EnvState,
)

# Safety bound: a well-behaved agent terminates with a commit action; this caps a runaway episode.
MAX_STEPS = 16


class DeployVerifyEnv(Environment):  # type: ignore[misc]
    # Each WebSocket session gets its own instance (the OpenEnv isolation mechanism); safe because
    # every instance owns only its own in-memory state and touches no shared resource.
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._trajectory_id = ""
        self._step_count = 0
        self._deployed_state: dict[str, Any] = {}

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **kwargs: Any,
    ) -> DeployObservation:
        self._trajectory_id = uuid4().hex
        self._step_count = 0
        self._deployed_state = {}
        return self._observe(done=False)

    def step(
        self,
        action: DeployAction,
        timeout_s: float | None = None,
        **kwargs: Any,
    ) -> DeployObservation:
        self._step_count += 1
        is_commit = action.resource_type == COMMIT_RESOURCE_TYPE
        if not is_commit:
            self._deployed_state[action.resource_type] = dict(action.properties)
        done = is_commit or self._step_count >= MAX_STEPS
        return self._observe(done=done)

    @property
    def state(self) -> EnvState:
        return EnvState(
            episode_id=self._trajectory_id,
            trajectory_id=self._trajectory_id,
            step_count=self._step_count,
        )

    def _observe(self, *, done: bool) -> DeployObservation:
        # reward is ALWAYS 0.0 — the A-side cannot and must not grade. A copy of deployed_state is
        # returned so the caller cannot mutate the env's internal state through the observation.
        return DeployObservation(
            done=done,
            reward=0.0,
            trajectory_id=self._trajectory_id,
            step_count=self._step_count,
            deployed_state=dict(self._deployed_state),
        )
