# Learnings — pre-T0 directional slice (#176, all legs)

date: 2026-07-02
sources: assay-ops#176 (grounding + run comments), assay-ops PR #185, private HF dataset
`AssayInc/pre-t0-drift-corpus` (runs/ + PINS.md), adapter `AssayInc/pre-t0-qwen25-coder-7b-sft`
status: raw learning — distill into wiki (touches: deterministic-verification,
eval-to-performance-proof, data-foundry, cloud-iac-wedge, environment-economics)

## What ran

15 private Terraform drift tasks (S3/IAM-role/KMS-key, LocalStack-graded) → base-model rollouts
(vLLM on HF Jobs) → rejection-sampled SFT set → TRL+LoRA SFT (Qwen2.5-Coder-7B-Instruct, pinned
rev) → base-vs-SFT delta on held-out + trained splits. Result: **held-out +0.0 pts (6/9 both),
trained −2.8 (13/36 → 12/36)** — flat at this dose, by design underpowered.

## Empirical learnings

1. **The deterministic reward held at run scale.** ~200 graded episodes: 0 quarantined, 0 errored,
   every grade K=3-reproducible through the closed-world verify path. The thesis's verification
   leg is now a measurement, not an argument.
2. **Unit economics are trivial.** Full loop (collection + SFT + 4 delta arms) ≈ $4 GPU + pennies
   of LocalStack. HF Jobs `--expose` serves vLLM (token-gated URL), so the entire GPU pipeline
   (serving + training) runs on HF Jobs alone — no owned infra.
3. **Task-difficulty design predicts model behavior exactly.** Base results were bimodal:
   state-present apply-fixable tasks 5/5 each; every read-and-reconcile task 0/5. The
   "state-absent" tier (delete local tfstate after baseline deploy) defeats a blind
   `terraform apply` policy (73% → 40% ceiling). Environments that discriminate are authorable
   by one person + agents in a day.
4. **Qwen2.5-Coder-7B cannot emit well-formed tool calls under `tool_choice=auto`** (invents a
   malformed call dialect; template is fine — model behavior, reproduced on vLLM bf16 + ollama).
   Server-side grammar forcing (`tool_choice=required`) fixes it completely. Small open models
   need harness compensation before any infra-agent signal is measurable at all.
5. **Rejection sampling from a weak student is yield-starved on hard tasks** (top-up round: 1/40).
   The SFT flywheel does not bootstrap from the small model alone — the training signal must come
   from a **stronger teacher sampled through OUR verifier as the filter**. That is the product
   mechanism ("gold trajectories"), now concrete: the verifier converts any policy's outputs into
   trustworthy training data.
6. **Flat-at-homeopathic-dose is uninformative on the lift claim**: 21 mostly-easy examples,
   61.8k tokens, 1 epoch, format channel harness-neutralized, noise floor ±16 pts at n=9. Do not
   read it as falsification; do not ship underpowered numbers as signal (eval-rigor held).

## Thesis read (2026-07-02)

- Verification edge: **strengthened** (empirically demonstrated). Judgment-beats-labor:
  **supported** (corpus authoring economics + discrimination). Demand leg: **untouched**
  (external; still hypothesis until a design-partner lab). Moat/gameability: **untested**
  (pre-T0 skipped it deliberately; vector 15 still open).
- Refinement, not pivot: the foundry's lift story runs through **teacher-filtered verified
  trajectories**, not student self-distillation.
- Pivot triggers (none fired): (a) properly-dosed teacher-filtered SFT at N≈30–50 shows no
  held-out lift; (b) frontier models close the infra long-horizon gap before we reach a lab;
  (c) the reward fails the red-team bar (gameable reward = no product).

## Next experiment (cheap, days)

Teacher-distillation round: sample a frontier model through the same harness, verifier-filter to
reward-1 trajectories, SFT the 7B on that set, re-run the delta. ~$50–150 API + ~$5 GPU. Tests
the actual product mechanism; either first real lift or a genuinely important negative.
