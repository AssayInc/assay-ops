"""D (AC#2) — delayed/terminal reward shape.

The A-side env returns ``reward == 0.0`` at every step *including the terminal step*. The graded
``reward in {0, 1}`` is produced by the (mock) account-B verifier **out-of-band, after the episode,
joined by ``trajectory_id``** — never computed inside ``step()``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from account_b_mock import MockAccountBVerifierLedger

from assayops_env_server.client import DeployVerifyEnvClient
from assayops_env_server.models import COMMIT_RESOURCE_TYPE, DeployAction


def test_terminal_reward_is_zero_and_grade_comes_from_account_b_out_of_band(
    server_url: str,
) -> None:
    async def run_episode() -> tuple[str, dict[str, Any]]:
        async with DeployVerifyEnvClient(base_url=server_url) as env:
            reset = await env.reset()
            assert reset.observation.reward == 0.0
            mid = await env.step(
                DeployAction(
                    resource_type="AWS::S3::Bucket", properties={"VersioningEnabled": True}
                )
            )
            assert mid.observation.reward == 0.0
            terminal = await env.step(DeployAction(resource_type=COMMIT_RESOURCE_TYPE))
            assert terminal.done is True
            assert (
                terminal.observation.reward == 0.0
            )  # terminal reward = zero shaping, not the grade
            return terminal.observation.trajectory_id, terminal.observation.deployed_state

    trajectory_id, deployed_state = asyncio.run(run_episode())

    account_b = MockAccountBVerifierLedger()
    # Delayed: when the episode ends, the agent-reachable side has no grade.
    assert account_b.fetch(trajectory_id) is None
    # Account-B computes the GRADED reward from the deployed state, out-of-band, and signs it.
    record = account_b.grade_and_record(trajectory_id, deployed_state, nonce="episode-d")
    assert record.trajectory_id == trajectory_id
    assert record.reward == 1  # golden satisfied → graded reward 1, computed B-side (not by step())
    assert account_b.verify(record)  # signed by account-B's key (KMS analog)
    fetched = account_b.fetch(trajectory_id)
    assert fetched is not None and fetched.reward == 1  # retrievable later, joined by trajectory_id


def test_account_b_grades_zero_when_the_golden_is_unsatisfied() -> None:
    account_b = MockAccountBVerifierLedger()
    record = account_b.grade_and_record(
        "traj-unsatisfied", {"AWS::S3::Bucket": {"VersioningEnabled": False}}, nonce="n"
    )
    assert record.reward == 0
