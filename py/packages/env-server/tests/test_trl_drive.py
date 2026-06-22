"""F (AC#3) — TRL drives the OpenEnv env via the integration path; reward comes out-of-band.

Exercises TRL 1.6.0's GRPOTrainer rollout seam against a real OpenEnv env over WebSocket:
``rollout_func`` returns the required ``prompt_ids``/``completion_ids``/``logprobs`` columns plus a
``trajectory_id`` column (NOT a reward); TRL forwards that column to ``reward_funcs``, which fetches
the GRADED reward from the (mock) account-B ledger out-of-band. The reward TRL optimizes is
therefore the account-B ``{0, 1}`` — never the env's ``step()`` reward (which stays ``0.0``).
"""

from __future__ import annotations

import inspect

import pytest
from account_b_mock import MockAccountBVerifierLedger
from trl_drive import OpenEnvRolloutHarness


def test_trl_rollout_seam_supplies_the_graded_reward_out_of_band(server_url: str) -> None:
    account_b = MockAccountBVerifierLedger()
    harness = OpenEnvRolloutHarness(server_url, account_b)
    prompts = ["please enable versioning on the bucket", "make a plain bucket"]

    rollout = harness.rollout_func(prompts, trainer=None)
    # TRL contract: the required columns are present...
    assert {"prompt_ids", "completion_ids", "logprobs"} <= set(rollout)
    # ...and the reward is NOT among them — TRL never reads the env's step() reward.
    assert "env_reward" not in rollout
    assert "reward" not in rollout
    # the join-key column TRL forwards verbatim to reward_funcs
    assert "trajectory_id" in rollout

    # The reward TRL optimizes = reward_funcs over the forwarded columns (out-of-band fetch by id).
    rewards = harness.reward_funcs(trajectory_id=rollout["trajectory_id"])
    assert rewards == [1.0, 0.0]  # graded {0,1} from account-B...
    assert rewards[0] != 0.0  # ...which differs from the env's zero shaping reward


def test_pinned_trl_grpotrainer_exposes_the_rollout_func_seam() -> None:
    # Optional: only runs when trl is installed (heavy: torch/vllm); binds to the real symbol.
    trl = pytest.importorskip("trl")
    params = inspect.signature(trl.GRPOTrainer.__init__).parameters
    assert "rollout_func" in params
