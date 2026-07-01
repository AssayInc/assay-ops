"""The drift-slice Inspect ``Task`` -- corpus -> Samples -> agent -> deploy-verifier Scorer.

The pre-T0 #176 episode runner: each admitted corpus task becomes one Sample whose sandbox (the
corpus compose file: the agent's 'default' workbench + the sample's OWN LocalStack) is where the
agent deploys; the deploy-verifier scorer then grades the deployed state from OUTSIDE the sandbox.
The dataset mapping is the trust seam: Sample metadata carries the validated TaskSpec (the grading
identity the scorer re-validates), files/setup come from the admitted corpus task -- all
harness-authored at dataset-build time, none of it agent-writable.

Run it against a PRIVATE corpus directory (I11):

    inspect eval assayops_evals/task.py -T corpus_dir=/path/to/private-corpus --model <model>

"epochs" are INFERENCE/rollout repeats of each task (the n~15 x 3 directional grid) -- not
training seeds (eval-rigor: never conflate the two).
"""

from __future__ import annotations

from pathlib import Path

from assayops_replay import DEFAULT_RUNS
from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.tool import bash, text_editor

from assayops_evals.corpus import Corpus, load_corpus
from assayops_evals.readers import localstack_reader_factory
from assayops_evals.scorer import TASK_SPEC_METADATA_KEY, deploy_verifier_scorer

# Ceilings for one drift-fix episode: enough for read config -> edit -> apply -> re-check loops,
# bounded so a wedged agent or apply can't stall the run (tune per corpus at run time).
_DEFAULT_MESSAGE_LIMIT = 50
_DEFAULT_TIME_LIMIT_SECONDS = 1800
_TOOL_TIMEOUT_SECONDS = 300


def samples_of(corpus: Corpus) -> list[Sample]:
    """One Sample per admitted corpus task (see the module docstring for the trust seam)."""
    return [
        Sample(
            id=corpus_task.spec.task_id,
            input=corpus_task.spec.description,
            metadata={TASK_SPEC_METADATA_KEY: corpus_task.spec.model_dump()},
            files={target: str(source) for target, source in corpus_task.files.items()} or None,
            setup=str(corpus_task.setup_script) if corpus_task.setup_script else None,
        )
        for corpus_task in corpus.tasks
    ]


@task
def drift_slice(
    corpus_dir: str,
    epochs: int = 3,
    message_limit: int = _DEFAULT_MESSAGE_LIMIT,
    time_limit: int = _DEFAULT_TIME_LIMIT_SECONDS,
    runs: int = DEFAULT_RUNS,
) -> Task:
    """The #176 directional-slice eval: n tasks x ``epochs`` rollouts, LocalStack-graded.

    The agent works agentically (react + bash/text_editor) inside the sample's sandbox; the
    scorer grades through the shipped ``verify()`` (K=``runs``) against the sample's OWN
    LocalStack. The resulting number is PRE-T0 DIRECTIONAL ONLY -- never published, never the E13
    proof (R1; see the package docstring).

    The I11 residency guard is NOT overridable here -- the ``load_corpus``
    ``allow_in_repo_for_tests`` seam is a library-test-only kwarg, deliberately kept off this
    ``@task`` signature so Inspect's ``-T`` flag surface cannot disable the guard from the CLI.
    """
    corpus = load_corpus(Path(corpus_dir))
    return Task(
        dataset=samples_of(corpus),
        solver=react(
            tools=[
                bash(timeout=_TOOL_TIMEOUT_SECONDS),
                text_editor(timeout=_TOOL_TIMEOUT_SECONDS),
            ]
        ),
        scorer=deploy_verifier_scorer(
            registry=corpus.registry,
            scope=corpus.scope,
            reader_factory=localstack_reader_factory(corpus.scope),
            bridge_registry=corpus.bridge_registry,
            runs=runs,
        ),
        sandbox=("docker", str(corpus.compose_file)),
        epochs=epochs,
        message_limit=message_limit,
        time_limit=time_limit,
    )
