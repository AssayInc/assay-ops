"""The FastAPI application — ``create_app`` mounts the env over HTTP + ``/ws``.

Run locally with: ``uvicorn assayops_env_server.app:app`` (the web UI stays off unless
``ENABLE_WEB_INTERFACE`` is set, so the server runs lean).
"""

from __future__ import annotations

from openenv.core.env_server import create_app

from assayops_env_server.environment import DeployVerifyEnv
from assayops_env_server.models import DeployAction, DeployObservation

# Pass the CLASS (a no-arg factory) — each WebSocket session gets its own env instance, which is
# OpenEnv's session-isolation mechanism. max_concurrent_envs > 1 requires the env to declare
# SUPPORTS_CONCURRENT_SESSIONS = True (DeployVerifyEnv does).
app = create_app(
    DeployVerifyEnv,
    DeployAction,
    DeployObservation,
    env_name="assayops-deploy-verify",
    max_concurrent_envs=8,
)
