"""Typed OpenEnv models for the A-side deploy-verify environment.

``Action``/``Observation``/``State`` come from OpenEnv (Pydantic v2). The base ``Observation``
carries ``done``/``reward``/``metadata``; we add the AssayOps-shaped fields and, crucially, the
``trajectory_id`` join key that ties an episode to the account-B graded reward record.
"""

from __future__ import annotations

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field

# The agent emits this resource_type to finish ("commit") the deploy and terminate the episode.
COMMIT_RESOURCE_TYPE = "__commit__"


class DeployAction(Action):  # type: ignore[misc]
    """One agent step: declare a resource to deploy (or ``__commit__`` to finish)."""

    resource_type: str
    properties: dict[str, object] = Field(default_factory=dict)


class DeployObservation(Observation):  # type: ignore[misc]
    """What the agent sees. ``reward`` (inherited) is always a zero shaping signal here."""

    trajectory_id: str
    step_count: int
    deployed_state: dict[str, dict[str, object]] = Field(default_factory=dict)


class EnvState(State):  # type: ignore[misc]
    """Server-side episode state. ``trajectory_id`` is the cross-system join key."""

    trajectory_id: str = ""
