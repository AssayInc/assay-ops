# Pre-T0 directional run — corpus → rollouts → SFT → the base-vs-SFT delta

The end-to-end recipe for the pre-T0 directional slice: ~15 Terraform drift tasks ×
Qwen2.5-Coder-7B, LocalStack-graded. The number this produces is **directional only — never
published or pitched as the proof** (`docs/priorities.md` P1/R1; the report artifact hard-codes
that framing). Per-package detail lives in `py/packages/evals/README.md` (the harness) and
`py/packages/trainer/README.md` (ETL + SFT); this page is the cross-package order of operations.

## The private corpus store

Tasks and goldens are **never committed to a code repo** (`DECISIONS.md` I11 — `load_corpus`
refuses a corpus inside any git repo). The slice's store:

- **Authoring copy:** a local directory outside every repo — `~/assay-private/corpus/pre-t0-slice/`
  (the corpus-directory contract in `py/packages/evals/README.md`), with the workbench image
  context beside it (`~/assay-private/corpus/workbench/`).
- **Durable mirror:** a **private** Hugging Face dataset repo (`hf upload-large-folder`-style sync;
  needs an org token). Mirror after authoring changes; the local directory is what runs.

The corpus pins its own `compose.yaml` (per-sample sandbox: `default` workbench +
the sample's own LocalStack at the same licensed image digest as `py/packages/infra-local`) and is
validated end-to-end at authoring time (admission via `load_corpus`, then per task:
drifted → reward 0, reference fix → reward 1, K-run reproducible, through the production
`verify()` closed-world path).

## Prerequisites

- Docker running; the workbench image built locally
  (`docker build -t assayops-workbench:pre-t0 ~/assay-private/corpus/workbench/`).
- `LOCALSTACK_AUTH_TOKEN` exported (from the repo-root `.env`) — each sample starts a licensed
  LocalStack container.
- A model endpoint per run (below); a CUDA GPU env only for the SFT step.

## 1. Rollout collection (trajectories for the SFT set)

Run the base model over the corpus with several rollouts per task; every sample is graded by the
deploy-verifier scorer (reward = the shipped `verify()`).

```sh
set -a; source .env; set +a
# The workspace packages are consumed by source path (no install) — the eval process needs them
# (trainer/src is for step 2's ETL; one export covers the session):
export PYTHONPATH="py/packages/evals/src:py/packages/trainer/src:py/packages/contracts/src:py/packages/diff-ir/src:py/packages/adapter-terraform/src:py/packages/replay/src:py/packages/verifier/src"
uv run --frozen inspect eval py/packages/evals/src/assayops_evals/task.py@drift_slice \
  -T corpus_dir="$HOME/assay-private/corpus/pre-t0-slice" \
  --model <base model> --epochs <rollouts-per-task> --max-sandboxes 3
```

`--max-sandboxes` caps concurrent per-sample LocalStack containers (each is a full LocalStack —
size to the machine). Rollouts here are **sampling for rejection-sampled SFT** — more epochs =
more chances at reward-1 trajectories on hard tasks.

**Endpoint quality matters:** a local q4-quantized 7B via ollama completes the loop but emitted
zero tool calls in the smoke rollout (prose plans only → no reward-1 trajectories to harvest).
Collect real rollouts on a serving stack with reliable tool-calling for the model (e.g. vLLM
serving the bf16 checkpoint on a GPU); keep ollama for plumbing smokes.

## 2. Held-out split, ETL, SFT

**Hold out at least one task per resource type** (they never enter the SFT set; the ETL fails
closed if a held-out task id appears in a training log — contamination, `DECISIONS.md` I11/§6).
The delta on held-out tasks is the directional read; the delta on trained tasks only shows the
loop learns at all. With n≈15 both are noisy — that is the accepted pre-T0 posture.

```sh
# ETL: graded logs -> sft.jsonl + manifest.json (only CORRECT = account-B-graded reward 1 enters)
uv run python -c "import asyncio; from pathlib import Path; from assayops_trainer import build_and_write; \
  asyncio.run(build_and_write(sorted(Path('logs').glob('*.eval')), Path('out/'), \
  held_out_ids=frozenset({'<task-id>', ...}), harness_git_sha='$(git rev-parse HEAD)'))"
```

SFT runs in a GPU env per `py/packages/trainer/README.md` (freeze exact hashes, pin
`model_revision` to a commit hash — I8). `training_seed` is a training seed, not a rollout seed;
vary it across SFT repeats if measuring seed sensitivity.

## 3. The delta

Serve the SFT adapter next to the base (e.g. vLLM with `--enable-lora`), then re-run step 1 once
per model — same corpus, same `--epochs` (the n×epochs grid) — and render the report:

```python
from assayops_evals import directional_delta, render_report
from inspect_ai.log import read_eval_log

print(render_report(directional_delta(read_eval_log("logs/base.eval"),
                                      read_eval_log("logs/sft.eval"))))
```

The report brackets quarantined/errored rollouts and hard-codes the PRE-T0 DIRECTIONAL framing.
Read it with the split in mind (held-out vs trained tasks), and record the one-paragraph
"does the approach show signal?" call with the run artifacts in the private store — logs,
`sft.jsonl`, `manifest.json`, and adapters stay private (I11; R1: no external claim).
