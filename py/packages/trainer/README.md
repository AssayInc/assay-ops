# `assayops_trainer` — trajectory→SFT ETL + TRL SFT+LoRA harness (#176 leg 2)

The **trainer leg** of the pre-T0 directional slice (#176). It turns leg-3's graded Inspect
`EvalLog`s into a rejection-sampled SFT set, then SFT+LoRA-trains Qwen2.5-Coder-7B on it (I6).

> **Pre-T0, R1-scoped.** A model trained here is a **directional signal only** — LocalStack-graded,
> **never published, never the E13 proof** (R1; `docs/priorities.md` P1). The manifest bakes that
> framing in so the artifact can't be innocently reused.

## Trust posture (what this leg does and does not assume)

- **Trains on the account-B graded reward, never the env `step()`** (§8 reward-boundary, non-waivable).
  An example enters the set **only** when leg-3's `deploy_verifier_scorer` `Score` is `CORRECT`
  (reward 1 = the account-B `verify()` grade). This is **rejection sampling** on the deploy reward.
- **"#78-shaped minus KMS."** Pre-T0 there is no ledger, so `reward==1` is read straight from the
  log's scorer key and the join key is the eval **sample id** (the stand-in for `trajectory_id`).
  When the WORM ledger lands (#38/#78) the join becomes `trajectory_id ⨝ KMS-signed reward record`
  **with signature verification** — the step this leg omits because no ledger exists yet.
- **Contamination fails closed.** A held-out task id appearing in the training logs raises
  (never silently trained on — eval-rigor / I11).
- **Seeds are not conflated** — `TrainerConfig.training_seed` is a *training* seed; rollout/inference
  seeds live in the eval harness (leg 3).

## What's tested in the hermetic gate vs. what needs a GPU

The **ETL, records, message/tool conversion, and config policy** are fully unit-tested in
`bun run verify` (no ML deps). The **actual SFT run** (`run_sft`) needs a CUDA GPU + the pinned model
and the heavy stack in `train-requirements.txt` — kept out of the gate; `run_sft` raises a clear
pointer to that file when the stack is absent.

## Run recipe

```sh
# 1. Collect graded rollouts by running leg-3's drift_slice eval (writes *.eval logs).
#    (rejection-sampling rollouts of the training tasks; see py/packages/evals.)

# 2. ETL: graded logs -> sft.jsonl (messages+tools) + manifest.json (provenance, R1-framed).
python -c "import asyncio; from pathlib import Path; from assayops_trainer import build_and_write; \
  asyncio.run(build_and_write([Path('logs/base.eval')], Path('out/'), harness_git_sha='<sha>'))"

# 3. SFT+LoRA train (GPU env with the pinned stack + a pinned model revision — I8):
uv pip install -r py/packages/trainer/train-requirements.txt
python -c "from pathlib import Path; from assayops_trainer import TrainerConfig, run_sft; \
  run_sft(TrainerConfig(model_revision='<commit-hash>'), Path('out/sft.jsonl'))"
```

`assistant_only_loss=True` masks tool observations at train time (TRL's mechanism, not a hand-rolled
mask) — it needs a tokenizer chat template that emits an assistant-token mask (trl ≥ 0.13); verify
the chosen Qwen2.5-Coder revision's template supports it before a run.
