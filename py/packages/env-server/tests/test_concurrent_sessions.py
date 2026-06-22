"""C (AC#1) — concurrent sessions isolated over HTTP + ``/ws``.

Drives the real OpenEnv WebSocket ``EnvClient`` (the exact transport TRL uses) against a real
running server. Each WebSocket session gets its own env instance, so concurrent episodes must not
see each other's ``trajectory_id`` or ``deployed_state``.
"""

from __future__ import annotations

import asyncio

import httpx

from assayops_env_server.client import DeployVerifyEnvClient
from assayops_env_server.models import COMMIT_RESOURCE_TYPE, DeployAction


def test_http_surface_is_served(server_url: str) -> None:
    assert httpx.get(f"{server_url}/health", timeout=5.0).status_code == 200
    assert httpx.get(f"{server_url}/metadata", timeout=5.0).status_code == 200
    assert httpx.get(f"{server_url}/schema", timeout=5.0).status_code == 200


def test_concurrent_ws_sessions_are_isolated(server_url: str) -> None:
    tags = ("alpha", "beta", "gamma", "delta")

    async def run_session(tag: str) -> tuple[str, dict[str, object]]:
        async with DeployVerifyEnvClient(base_url=server_url) as env:
            await env.reset()
            await env.step(DeployAction(resource_type=f"Res::{tag}", properties={"tag": tag}))
            result = await env.step(DeployAction(resource_type=COMMIT_RESOURCE_TYPE))
            obs = result.observation
            return obs.trajectory_id, obs.deployed_state

    async def drive_all() -> list[tuple[str, dict[str, object]]]:
        return await asyncio.gather(*(run_session(t) for t in tags))

    results = asyncio.run(drive_all())

    trajectory_ids = [tid for tid, _ in results]
    assert len(set(trajectory_ids)) == len(tags)  # distinct join keys — no cross-session leakage
    for tag, (_, deployed_state) in zip(tags, results, strict=True):
        # each session sees ONLY its own resource — per-session env instance, no shared state
        assert deployed_state == {f"Res::{tag}": {"tag": tag}}
