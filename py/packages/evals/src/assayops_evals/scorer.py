"""The deploy-verifier as an Inspect ``Scorer`` (I6/T11) -- the harness's one reward seam.

A thin, trust-preserving wrapper: every grading input is HARNESS-OWNED -- the ``TaskSpec`` comes
from sample metadata written by the dataset loader (``TASK_SPEC_METADATA_KEY``), the golden
registry / read scope / bridge registry from the private corpus, the readers from the injected
factory -- never from agent output (write-isolated-verifier: never discover what to grade from
agent-supplied inputs; the agent can write neither sample metadata nor this process's memory). The
grade itself is the shipped account-B ``verify()`` -- the ONLY reward-emitting entry (#141) -- run
in a worker thread so its blocking boto3 reads don't stall Inspect's event loop.

Verdict -> Score (the 7A semantics, DECISIONS.md section 1):

- ``Reproducible`` -- a settled, K-reproduced grade -> CORRECT (reward 1) / INCORRECT (reward 0).
- ``FailedClosed`` -- reward 0, fail closed (genuine unreadability / a broken address tag) ->
  INCORRECT with the cause in ``explanation`` (surfaced, never masked).
- ``Quarantined`` -- flaky grade or persistent infra transient -> ``Score.unscored()`` (the NaN
  sentinel metrics and epoch reducers skip): pulled from the pass rate, never a false 0 that would
  poison the directional delta.
- A corpus / config / verifier error PROPAGATES and fails the sample loudly -- it is the harness's
  bug, not the agent's deploy; scoring it would hide a corpus gap (vector #15).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from functools import partial

from anyio.to_thread import run_sync
from assayops_adapter_terraform import BridgeRegistry
from assayops_contracts import Reward, TaskSpec
from assayops_replay import DEFAULT_RUNS, Quarantined, Reproducible
from assayops_verifier import GoldenRegistry
from assayops_verifier.read import DeployedStateReader
from assayops_verifier.read_scope import ReadScope
from assayops_verifier.verify import FailedClosed, VerifyVerdict, verify
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState

# The sample-metadata key the dataset loader writes the validated TaskSpec under. Metadata is
# authored by the harness at dataset-build time and is not reachable from the agent's sandbox.
TASK_SPEC_METADATA_KEY = "assayops_task_spec"

# The name the @scorer decorator registers this scorer under -- the key its Score lands under in
# every eval log. Defined HERE, beside the function it names, so a rename is caught in one place
# (the report reads logs by this key). MUST equal the function name; a registry test locks it.
DEPLOY_VERIFIER_SCORER_NAME = "deploy_verifier_scorer"

# Builds the per-Region account-B Cloud Control reader map for the CURRENT sample -- production
# discovers the sample's LocalStack endpoint here; tests inject fakes. Async because discovery
# talks to the sample's sandbox.
ReaderFactory = Callable[[], Awaitable[Mapping[str, DeployedStateReader]]]


@scorer(metrics=[accuracy(), stderr()])
def deploy_verifier_scorer(
    *,
    registry: GoldenRegistry,
    scope: ReadScope,
    reader_factory: ReaderFactory,
    bridge_registry: BridgeRegistry | None = None,
    runs: int = DEFAULT_RUNS,
) -> Scorer:
    """The deploy-verifier Scorer over harness-owned grading inputs (see the module docstring)."""

    async def score(state: TaskState, target: Target) -> Score:
        task = _task_spec_of(state)
        readers = await reader_factory()
        # verify() is synchronous (blocking boto3 reads through the K-run); a worker thread keeps
        # the event loop free for the other samples' model calls and sandbox execs.
        # abandon_on_cancel=True: verify() is READ-ONLY (Cloud Control reads + in-process grading,
        # no writes/state), so when Inspect's scoring time limit cancels this task, the read thread
        # can be abandoned safely -- otherwise a wedged LocalStack (K x adaptive retries x 30s read
        # timeout) would hold the slot far past the budget. A discarded read forges nothing.
        verdict = await run_sync(
            partial(
                verify,
                readers,
                registry,
                task,
                task.seed,
                scope,
                bridge_registry=bridge_registry,
                runs=runs,
            ),
            abandon_on_cancel=True,
        )
        return _score_of(verdict, task)

    return score


def _task_spec_of(state: TaskState) -> TaskSpec:
    """The harness-owned grading identity, re-validated fail-closed from sample metadata."""
    raw = (state.metadata or {}).get(TASK_SPEC_METADATA_KEY)
    if raw is None:
        raise ValueError(
            f"sample metadata has no {TASK_SPEC_METADATA_KEY!r} entry -- the dataset loader must "
            "write the validated TaskSpec there; the grading identity is never inferred from "
            "agent output"
        )
    return TaskSpec.model_validate(raw)


def _score_of(verdict: VerifyVerdict, task: TaskSpec) -> Score:
    if isinstance(verdict, Reproducible):
        rewarded = verdict.reward is Reward.number_1
        return Score(
            value=CORRECT if rewarded else INCORRECT,
            explanation=(
                f"deploy-verifier reward {verdict.reward.value} "
                f"(reproduced across {verdict.runs} runs)"
            ),
            metadata={
                "verdict": "reproducible",
                "reward": verdict.reward.value,
                "runs": verdict.runs,
                "task_id": task.task_id,
            },
        )
    if isinstance(verdict, FailedClosed):
        return Score(
            value=INCORRECT,
            explanation=verdict.reason,
            metadata={"verdict": "failed_closed", "reward": 0, "task_id": task.task_id},
        )
    return _unscored_quarantine(verdict, task)


def _unscored_quarantine(verdict: Quarantined, task: TaskSpec) -> Score:
    return Score.unscored(
        explanation=verdict.reason,
        metadata={
            "verdict": "quarantined",
            "runs": verdict.runs,
            "distinct_outcomes": verdict.distinct_outcomes,
            "task_id": task.task_id,
        },
    )
