"""TRL OpenEnv integration drive (trl 1.6.0 contract), reward supplied out-of-band.

Reproduces TRL 1.6.0's ``GRPOTrainer`` rollout seam exactly (verified against the pinned source):
- ``rollout_func(prompts, trainer) -> dict`` returns the REQUIRED ``prompt_ids`` /
  ``completion_ids`` / ``logprobs`` columns, plus an EXTRA ``trajectory_id`` column (NOT
  ``env_reward``). TRL forwards every non-required column to ``reward_funcs`` as ``**reward_kwargs``
  (``trl/trainer/grpo_trainer.py`` v1.6.0 L1719-1726 / L2153) and never reads ``StepResult.reward``
  itself (``generate_rollout_completions`` returns no reward).
- ``reward_funcs(*, trajectory_id, **kwargs) -> list[float]`` fetches the account-B signed WORM
  record by ``trajectory_id`` and returns the GRADED reward — out-of-band, never the env's
  ``step()`` reward.

Generation (token ids / logprobs) is stubbed: TRL's ``generate_rollout_completions`` hard-imports
vLLM (GPU), but the reward boundary lives entirely in the rollout -> reward seam, which this
exercises CPU-only against a real OpenEnv env over WebSocket.
"""

from __future__ import annotations

import asyncio
from typing import Any

from account_b_mock import MockAccountBVerifierLedger

from assayops_env_server.client import DeployVerifyEnvClient
from assayops_env_server.models import COMMIT_RESOURCE_TYPE, DeployAction


def _policy_actions(prompt: str) -> list[DeployAction]:
    """Toy stand-in for the LLM policy: a prompt mentioning versioning deploys the golden target."""
    if "versioning" in prompt.lower():
        properties = {"VersioningEnabled": True}
    else:
        properties = {"VersioningEnabled": False}
    return [
        DeployAction(resource_type="AWS::S3::Bucket", properties=properties),
        DeployAction(resource_type=COMMIT_RESOURCE_TYPE),
    ]


class OpenEnvRolloutHarness:
    """The TRL drive seam + the (mock) account-B verifier sweep, joined by ``trajectory_id``."""

    def __init__(self, server_url: str, account_b: MockAccountBVerifierLedger) -> None:
        self._server_url = server_url
        self._account_b = account_b

    def rollout_func(self, prompts: list[str], trainer: Any = None) -> dict[str, Any]:
        async def drive(prompt: str) -> str:
            async with DeployVerifyEnvClient(base_url=self._server_url) as env:
                await env.reset()
                result: Any = None
                for action in _policy_actions(prompt):
                    result = await env.step(action)
                trajectory_id: str = result.observation.trajectory_id
                return trajectory_id

        async def drive_all() -> list[str]:
            return await asyncio.gather(*(drive(prompt) for prompt in prompts))

        trajectory_ids = asyncio.run(drive_all())

        # The account-B verifier reads each trajectory's GROUND-TRUTH deployed state (CLOUD) itself,
        # out-of-band, and writes a signed WORM record. It is never handed the agent's observation.
        for trajectory_id in trajectory_ids:
            self._account_b.grade_and_record(trajectory_id, nonce=f"nonce-{trajectory_id}")

        # Required columns are stubbed (generation is GPU-bound, orthogonal to the boundary); the
        # trajectory_id column carries the join key TRL forwards verbatim to reward_funcs.
        return {
            "prompt_ids": [[0] for _ in prompts],
            "completion_ids": [[0] for _ in prompts],
            "logprobs": [[0.0] for _ in prompts],
            "trajectory_id": trajectory_ids,
        }

    def reward_funcs(self, *, trajectory_id: list[str], **kwargs: Any) -> list[float]:
        rewards: list[float] = []
        for tid in trajectory_id:
            record = self._account_b.fetch(tid)
            assert record is not None, f"no account-B record for {tid}"
            assert self._account_b.verify(record), "account-B signature failed to verify"
            rewards.append(float(record.reward))
        return rewards
