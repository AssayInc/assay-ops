# assayops-evals

The Inspect-AI eval harness: the AssayOps **deploy-verifier as a custom `Scorer`** around the
shipped `assayops_verifier.verify` — the only reward-emitting entry — over a **private** task
corpus. Built pre-T0 as the directional-slice harness; it is also the E13 harness seam the
full-rigor proof later extends.

## Trust posture (read first)

- Grading runs **in the eval process, outside every sandbox**, through `verify()` only: closed-world
  Cloud Control reads → adapter normalization → the regenerated golden → `reward ∈ {0,1}`, K-run
  reproduced. Grading identity (task, seed, scope) is harness-owned sample metadata — never agent
  output.
- **Pre-T0 caveat:** with no account A/B split, each sample's LocalStack is reachable from the
  agent's container (it must deploy to it). A directional SFT number needs no more (no adversarial
  policy, no external claim) — the report artifact hard-codes the "PRE-T0 DIRECTIONAL — NOT the
  E13 proof" framing, and the number is **never published** (R1).
- **Residency (I11):** tasks + goldens live in a **private corpus directory**, never in this repo;
  `load_corpus` refuses an in-repo corpus. In-repo test fixtures are synthetic only.

## The private corpus contract

```
<corpus_dir>/
  corpus.py                 # REGISTRY: GoldenRegistry, READ_SCOPE: ReadScope,
                            # optional BRIDGE_REGISTRY: BridgeRegistry | None
  compose.yaml              # per-sample sandbox: 'default' agent workbench (terraform installed)
                            # + 'localstack' service publishing ports: ["4566"]
  tasks/<task_id>/
    task.json               # TaskSpec (task_id == directory name)
    setup.sh                # optional: deploy the baseline + inject the drift
    files/**                # optional: the agent's working files (Terraform dir)
```

`load_corpus` is the admission gate: every task's golden must regenerate and pass the
authoring-time per-property read gate, or the corpus is refused.

## Running the slice

```sh
# one model, n tasks x 3 rollouts, LocalStack-graded per sample. The workspace packages are
# consumed by source path (no install), so the eval process needs them on PYTHONPATH:
export PYTHONPATH="py/packages/evals/src:py/packages/contracts/src:py/packages/diff-ir/src:py/packages/adapter-terraform/src:py/packages/replay/src:py/packages/verifier/src"
uv run --frozen inspect eval py/packages/evals/src/assayops_evals/task.py \
  -T corpus_dir=/path/to/private-corpus --epochs 3 --model <base-or-sft-model>
```

Then the directional read, from the two logs:

```python
from assayops_evals import directional_delta, render_report
from inspect_ai.log import read_eval_log

print(render_report(directional_delta(read_eval_log(base_log), read_eval_log(sft_log))))
```

Quarantined rollouts (7A: flaky grade / persistent infra transient) are unscored — excluded from
the rate, never counted as failures.
