"""A — the A-side environment in isolation (no server).

Foundational unit tests: the env mints a ``trajectory_id`` join key at reset, tracks a toy
"deployed state", terminates on a commit action, and — the non-negotiable — returns a **zero
shaping reward** from every ``step()``/terminal, never a graded ``reward in {0, 1}``.
"""

from __future__ import annotations

from assayops_env_server.environment import DeployVerifyEnv
from assayops_env_server.models import DeployAction, DeployObservation, EnvState


def test_reset_mints_trajectory_id_and_returns_zero_shaping_reward() -> None:
    env = DeployVerifyEnv()
    obs = env.reset()
    assert isinstance(obs, DeployObservation)
    assert obs.trajectory_id  # non-empty join key
    assert obs.done is False
    assert obs.reward == 0.0  # zero shaping signal — the A-side never emits a graded reward
    assert obs.deployed_state == {}
    assert obs.step_count == 0
    state = env.state
    assert isinstance(state, EnvState)
    assert state.trajectory_id == obs.trajectory_id
    assert state.step_count == 0


def test_each_reset_generates_a_fresh_trajectory_id() -> None:
    env = DeployVerifyEnv()
    first = env.reset().trajectory_id
    second = env.reset().trajectory_id
    assert first != second


def test_reset_honors_an_externally_supplied_episode_id_as_the_trajectory_id() -> None:
    env = DeployVerifyEnv()
    obs = env.reset(episode_id="harness-minted-id")
    # The join key can originate out-of-band (trusted harness side), not the agent-reachable env.
    assert obs.trajectory_id == "harness-minted-id"
    assert env.state.trajectory_id == "harness-minted-id"


def test_step_applies_action_keeps_reward_zero_and_is_not_terminal() -> None:
    env = DeployVerifyEnv()
    env.reset()
    obs = env.step(
        DeployAction(resource_type="AWS::S3::Bucket", properties={"VersioningEnabled": True})
    )
    assert obs.reward == 0.0  # A-side NEVER emits a graded reward
    assert obs.done is False
    assert obs.step_count == 1
    assert obs.deployed_state == {"AWS::S3::Bucket": {"VersioningEnabled": True}}


def test_commit_action_terminates_with_a_zero_shaping_reward() -> None:
    env = DeployVerifyEnv()
    env.reset()
    env.step(DeployAction(resource_type="AWS::S3::Bucket", properties={"VersioningEnabled": True}))
    obs = env.step(DeployAction(resource_type="__commit__", properties={}))
    assert obs.done is True
    assert obs.reward == 0.0  # even the terminal reward is a zero shaping signal, never the grade
    # the deployed state the account-B verifier will later grade, read-only, out-of-band
    assert obs.deployed_state == {"AWS::S3::Bucket": {"VersioningEnabled": True}}


def test_terminal_is_latched_so_steps_after_commit_do_not_mutate_state() -> None:
    env = DeployVerifyEnv()
    env.reset()
    env.step(DeployAction(resource_type="AWS::S3::Bucket", properties={"VersioningEnabled": True}))
    committed = env.step(DeployAction(resource_type="__commit__", properties={}))
    # A stray step after the terminal must NOT deploy more, advance the step count, or un-terminate.
    after = env.step(DeployAction(resource_type="AWS::EC2::Instance", properties={"sneaky": True}))
    assert after.done is True
    assert after.step_count == committed.step_count
    assert after.deployed_state == {"AWS::S3::Bucket": {"VersioningEnabled": True}}
