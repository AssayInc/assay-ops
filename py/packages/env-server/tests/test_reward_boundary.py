"""E (AC#4) — the non-waivable reward boundary (DECISIONS.md §8 + I5).

Four angles on the single rule "the A-side env-server never computes the graded reward":
1. capability: the A-side package declares no signing dependency and no reference to account-B;
2. behavior: no env step ever returns a graded reward, under fuzzed action sequences;
3. signature: a record the agent could fabricate does not verify under account-B's key;
4. ledger: account-B's store is WORM (append-only).
"""

from __future__ import annotations

import ast
import asyncio
import pathlib
import random
from types import ModuleType
from typing import Any

from account_b_mock import GradedRewardRecord, MockAccountBVerifierLedger, _canonical_unsigned
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

import assayops_env_server
from assayops_env_server.client import DeployVerifyEnvClient
from assayops_env_server.cloud_state import CLOUD
from assayops_env_server.models import COMMIT_RESOURCE_TYPE, DeployAction, DeployObservation


def _imported_roots(package: ModuleType) -> set[str]:
    """Top-level module names imported by every source file in ``package``."""
    assert package.__file__ is not None
    roots: set[str] = set()
    for path in pathlib.Path(package.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                roots.add(node.module.split(".")[0])
    return roots


def test_a_side_package_declares_no_grading_or_signing_capability() -> None:
    roots = _imported_roots(assayops_env_server)
    assert "cryptography" not in roots  # no signing capability in the agent-reachable code
    assert "account_b_mock" not in roots  # no reference to the account-B services
    assert "openenv" in roots  # sanity: it IS the OpenEnv env-server it claims to be


def test_env_never_emits_a_graded_reward_under_fuzzed_actions(server_url: str) -> None:
    rng = random.Random(1234)
    resource_pool = [
        "AWS::S3::Bucket",
        "AWS::IAM::Role",
        "AWS::EC2::Instance",
        COMMIT_RESOURCE_TYPE,
    ]

    async def fuzz_one_episode() -> list[Any]:
        rewards: list[Any] = []
        async with DeployVerifyEnvClient(base_url=server_url) as env:
            rewards.append((await env.reset()).observation.reward)
            for _ in range(rng.randint(1, 6)):
                action = DeployAction(
                    resource_type=rng.choice(resource_pool), properties={"v": rng.random()}
                )
                result = await env.step(action)
                rewards.append(result.observation.reward)
                if result.done:
                    break
        return rewards

    async def fuzz_many() -> list[list[Any]]:
        return await asyncio.gather(*(fuzz_one_episode() for _ in range(8)))

    all_rewards = [reward for episode in asyncio.run(fuzz_many()) for reward in episode]
    assert all_rewards  # the fuzz actually ran
    # the A-side reward is ALWAYS the zero shaping signal — never a graded reward
    assert all(reward == 0.0 for reward in all_rewards)


def test_a_forged_reward_record_does_not_verify_under_account_b_key() -> None:
    account_b = MockAccountBVerifierLedger()
    # An agent could fabricate a "reward = 1" record and sign it with its OWN key...
    attacker_key = ec.generate_private_key(ec.SECP256R1())
    fields: dict[str, Any] = {
        "trajectory_id": "traj-forge",
        "attempt": 0,
        "reward": 1,
        "reportDigest": "0" * 64,
        "graderVersion": "forged",
        "gradedAt": "1",
        "nonce": "n",
    }
    forged_signature = attacker_key.sign(_canonical_unsigned(fields), ec.ECDSA(hashes.SHA256()))
    forged = GradedRewardRecord(**fields, signature=forged_signature.hex())
    # ...but it does not verify under account-B's public key — the agent holds no signing key.
    assert account_b.verify(forged) is False


def test_a_tampered_signed_record_does_not_verify() -> None:
    CLOUD.deploy("traj-tamper", "AWS::S3::Bucket", {"VersioningEnabled": False})
    account_b = MockAccountBVerifierLedger()
    genuine = account_b.grade_and_record("traj-tamper", nonce="n")  # reward 0, correctly signed
    assert genuine.reward == 0
    assert account_b.verify(genuine)
    # Flip reward 0 -> 1 on the signed record; the signature no longer covers these bytes.
    tampered = genuine.model_copy(update={"reward": 1})
    assert account_b.verify(tampered) is False


def test_a_malformed_signature_fails_verification_without_raising() -> None:
    CLOUD.deploy("traj-bad", "AWS::S3::Bucket", {"VersioningEnabled": True})
    account_b = MockAccountBVerifierLedger()
    record = account_b.grade_and_record("traj-bad", nonce="n")
    malformed = record.model_copy(update={"signature": "not-hex-zz"})
    # The agent controls the bytes submitted, so malformed must mean "does not verify", never raise.
    assert account_b.verify(malformed) is False


def test_account_b_grades_ground_truth_and_ignores_a_fabricated_observation() -> None:
    # Ground truth: a golden bucket is deployed under this trajectory.
    CLOUD.deploy("traj-divergent", "AWS::S3::Bucket", {"VersioningEnabled": True})
    # The agent fabricates an observation claiming an EMPTY (failing) state for the same trajectory.
    fabricated = DeployObservation(
        done=True, reward=0.0, trajectory_id="traj-divergent", step_count=1, deployed_state={}
    )
    assert fabricated.deployed_state == {}  # the agent's claim — which B never consults
    account_b = MockAccountBVerifierLedger()
    record = account_b.grade_and_record("traj-divergent", nonce="n")
    # B grades the GROUND TRUTH (golden → 1), ignoring the agent's fabricated observation — the old
    # tautology (grading the agent-reported state) cannot re-enter.
    assert record.reward == 1


def test_reward_ledger_is_worm_append_only_and_prior_attempts_are_immutable() -> None:
    account_b = MockAccountBVerifierLedger()
    CLOUD.deploy("traj-worm", "AWS::S3::Bucket", {"VersioningEnabled": True})
    first = account_b.grade_and_record("traj-worm", nonce="n0", attempt=0)
    assert first.reward == 1

    # The same (trajectory_id, attempt) cannot be overwritten.
    overwrite_rejected = False
    try:
        account_b.grade_and_record("traj-worm", nonce="n0b", attempt=0)
    except ValueError:
        overwrite_rejected = True
    assert overwrite_rejected

    # The ground truth changes (the resource is reconfigured); a re-grade is a NEW attempt that
    # reflects it — append-only, never a mutation of the first. (Which attempt the trainer trusts is
    # a verifier/consumer policy — E4/T8, out of spike scope.)
    CLOUD.deploy("traj-worm", "AWS::S3::Bucket", {"VersioningEnabled": False})
    second = account_b.grade_and_record("traj-worm", nonce="n1", attempt=1)
    assert second.attempt == 1
    assert second.reward == 0
    assert account_b.verify(first)  # the first signed record is intact after the append
