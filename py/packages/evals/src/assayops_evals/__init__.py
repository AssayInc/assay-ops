"""AssayOps Inspect-AI eval harness (E13/T11 seam; built pre-T0 for the #176 directional slice).

The deploy-verifier runs as an Inspect ``Scorer`` around the shipped account-B ``verify()`` --
the ONLY reward-emitting entry (DECISIONS.md section 1, T1) -- over a PRIVATE task corpus (I11:
tasks + goldens live in a private store, never committed; in-repo tests use synthetic fixtures
only).

PRE-T0 TRUST CAVEAT (R1). The directional slice runs with no account A/B split: the agent's
sandbox and its per-sample LocalStack share a Docker network, so the graded substrate is
agent-reachable. That is licensed by docs/priorities.md P1 for a directional SFT number ONLY (no
adversarial policy, no external claim) -- the number is NEVER published or pitched as the proof
(the report artifact hard-codes that framing). The lab-facing proof (E13, DECISIONS.md section 6)
requires the full trust stack.
"""

from __future__ import annotations

from assayops_evals.corpus import (
    LOCALSTACK_GATEWAY_PORT,
    LOCALSTACK_SERVICE,
    Corpus,
    CorpusError,
    CorpusTask,
    load_corpus,
)
from assayops_evals.readers import (
    localstack_endpoint,
    localstack_reader_factory,
    readers_for_scope,
)
from assayops_evals.report import (
    DirectionalDelta,
    ModelSlice,
    directional_delta,
    render_report,
)
from assayops_evals.scorer import (
    DEPLOY_VERIFIER_SCORER_NAME,
    TASK_SPEC_METADATA_KEY,
    ReaderFactory,
    deploy_verifier_scorer,
)
from assayops_evals.task import drift_slice, samples_of

__all__ = [
    "DEPLOY_VERIFIER_SCORER_NAME",
    "LOCALSTACK_GATEWAY_PORT",
    "LOCALSTACK_SERVICE",
    "TASK_SPEC_METADATA_KEY",
    "Corpus",
    "CorpusError",
    "CorpusTask",
    "DirectionalDelta",
    "ModelSlice",
    "ReaderFactory",
    "deploy_verifier_scorer",
    "directional_delta",
    "drift_slice",
    "load_corpus",
    "localstack_endpoint",
    "localstack_reader_factory",
    "readers_for_scope",
    "render_report",
    "samples_of",
]
