# #176 leg 2 — Trainer: trajectory→SFT ETL + TRL SFT+LoRA harness

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md + the PR + GitHub #176.
> **For Claude:** REQUIRED SUB-SKILL: superpowers:test-driven-development per task; verification-before-completion before claiming done.

**Goal:** The trainer leg of the pre-T0 slice (#176 leg 2): a **trajectory→SFT ETL** that turns leg-3's
graded `EvalLog`s into a rejection-sampled SFT set (messages+tools, provenance, dedup, reproducible
manifest), plus a **TRL `SFTTrainer` + LoRA harness** for Qwen2.5-Coder-7B — so the SFT run has data + a runner.

**Branch:** `176-leg2-trainer` (off main). Umbrella #176 leg 2. Focused PR (`Advances #176`, never Closes).

## Grounding (reconciled — no floor contradiction)
- **I6** — TRL `SFTTrainer` + LoRA on **Qwen2.5-Coder-7B** dense baseline; eval via Inspect (leg 3, landed).
- **I8** — pin the model **revision by commit hash** (config enforces a required `model_revision`); heavy ML deps pinned in `train-requirements.txt`, kept OUT of the hermetic `bun run verify` gate.
- **§8 OpenEnv reward-boundary invariant (non-waivable)** — the trainer trains on the **account-B graded reward**, never the env `step()`. Pre-T0 has no ledger/KMS, so `reward==1` = the **deploy-verifier `Score`** in leg-3's `EvalLog` (that Score *is* `verify()` = the account-B grade). Join key = eval **sample id** (pre-T0 stand-in for `trajectory_id`). Ledger (#38/#78) later makes it `trajectory_id ⨝ KMS-signed WORM record` + signature verification — the step this leg omits ("#78-shaped minus KMS").
- **eval-rigor** — config `seed` is a **training seed** (labeled, ≠ rollout/inference seed); **held-out contamination fails closed** (a held-out task id in the training logs → raise, never trained on).
- **SFT-only** (DECISIONS: no RL/GRPO loop before the proof).

## Package: `py/packages/trainer` → `assayops_trainer`
Runtime deps: `inspect-ai` (read logs + `messages_to_openai`), `pydantic`. NO verifier/boto3/torch at runtime.

## TDD steps (each: failing test → minimal impl → green)
- [ ] 1. `records.py` — `Provenance`, `SFTExample` (frozen, `extra="forbid"`).
- [ ] 2. `messages.py` — `sample_to_openai_messages` (via `messages_to_openai`) + `sample_tools` (`ToolInfo`→OpenAI from the sample's model events, dedup by name).
- [ ] 3. `etl.py` — `build_sft_dataset`: filter reward==1 (`CORRECT`); skip `INCORRECT`/quarantined-NaN/errored (counted); **held-out fail-closed**; dedup by `(model, task_id, epoch, run_id)`; deterministic sort; unexpected score value → raise.
- [ ] 4. writers — `write_sft_jsonl` (clean `{messages, tools}`), `write_manifest` (provenance + counts + git sha; alignment asserted), `build_and_write` (`read_eval_log` orchestration).
- [ ] 5. `config.py` — `TrainerConfig` (I6/I8/eval-rigor); `to_sft_config_kwargs` / `to_lora_config_kwargs` / `to_yaml_dict` (pure).
- [ ] 6. `sft.py` — `run_sft`: lazy-import trl/peft/datasets → `SFTConfig`+`LoraConfig`+`SFTTrainer`; clear `ImportError` → `train-requirements.txt`. Real train behind `importorskip`.
- [ ] 7. wiring — `pyproject.toml` (mypy strict + `disallow_any_explicit`; `ignore_missing_imports` trl/peft/…), `package.json`, `turbo.json`, `train-requirements.txt`, `README.md`.
- [ ] 8. `bun run verify` green → focused PR (advances #176) → update PROGRAM.md / ISSUES.md → `/review`.
