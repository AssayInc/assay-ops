"""The A-side deploy-verify OpenEnv ``Environment``.

A toy AssayOps episode: the agent issues deploy actions that "deploy" resources to the cloud-state
substrate (``cloud_state.CLOUD``); a ``__commit__`` action ends the episode. This module is the
agent-reachable surface, so it **never computes the graded reward** — every ``step()``/terminal
reward is ``0.0`` (a zero shaping signal). The graded ``reward in {0, 1}`` is produced account-B,
read-only and out-of-band, joined by ``trajectory_id`` (DECISIONS.md §8 + I5). There is deliberately
**no rubric** attached (OpenEnv's environment-owned-reward mechanism), because that is exactly what
the boundary forbids.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

from assayops_env_server.cloud_state import CLOUD
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
    # every instance owns only its own trajectory_id namespace in CLOUD and shares no mutable state.
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._start_episode()

    def _start_episode(self) -> None:
        # Mint here (not lazily) so the env is always in a valid state — a step before reset still
        # has a real trajectory_id rather than an empty one.
        self._trajectory_id = uuid4().hex
        self._step_count = 0
        self._done = False

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **kwargs: Any,
    ) -> DeployObservation:
        self._start_episode()
        return self._observe()

    def step(
        self,
        action: DeployAction,
        timeout_s: float | None = None,
        **kwargs: Any,
    ) -> DeployObservation:
        if self._done:
            # Terminal is latched: once committed, no further deploys until reset.
            return self._observe()
        self._step_count += 1
        if action.resource_type == COMMIT_RESOURCE_TYPE:
            self._done = True
        else:
            CLOUD.deploy(self._trajectory_id, action.resource_type, action.properties)
            if self._step_count >= MAX_STEPS:
                self._done = True
        return self._observe()

    @property
    def state(self) -> EnvState:
        return EnvState(
            episode_id=self._trajectory_id,
            trajectory_id=self._trajectory_id,
            step_count=self._step_count,
        )

    def _observe(self) -> DeployObservation:
        # reward is ALWAYS 0.0 — the A-side cannot and must not grade. deployed_state is the agent's
        # view of what it deployed (a read-only snapshot); the account-B grade reads CLOUD directly.
        return DeployObservation(
            done=self._done,
            reward=0.0,
            trajectory_id=self._trajectory_id,
            step_count=self._step_count,
            deployed_state=CLOUD.read(self._trajectory_id),
        )
