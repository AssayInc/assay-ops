# Learnings — pre-T0 teacher-distillation round (#186)

date: 2026-07-02
sources: assay-ops#186 (run comment), private HF dataset `AssayInc/pre-t0-drift-corpus`
(runs/collect-teacher-r1 + runs/sft-r2 + runs/delta-*-r2* + PINS.md), adapter
`AssayInc/pre-t0-qwen25-coder-7b-sft-r2`
status: raw learning — distill into wiki (touches: data-foundry, eval-to-performance-proof,
deterministic-verification, environment-economics)

## What ran

The #176 successor: claude-sonnet-5 sampled through the SAME `drift_slice` harness
(`force_tool_calls=true` on every arm) over the 12 training tasks → verifier-filtered ETL
(reward-1, complete rollouts only) → `sft-r2` (79 examples, 3.8× the r1 dose) → TRL SFT+LoRA at
the r1 pins → the 4-arm delta. Result: **held-out −22.2 pts (base 7/9 → sft 5/9), trained −2.8
(12/36 → 11/36)** — a real negative, not flat. A `message_limit=100` diagnostic pair confirms it
is not an eval-budget artifact (held-out −33.3 there). ~272 graded episodes this round; 0
quarantined; the only errored samples are 3 context-overflow hard-errors in the one
un-renderable diagnostic arm (below).

## Empirical learnings

1. **Verifier-filtered teacher collection works as a data machine — the mechanism under test
   held.** Teacher yield on the hard tier where the student was 1/40: ~83% at the student's
   message budget, 98.3% (59/60) once the budget matched the teacher; $10.07 teacher API
   (cache-dominated) + ~$5 GPU for the whole round; held-out tripwire silent; every admitted
   example is an account-B-style graded reward 1. "Any policy's outputs → trustworthy training
   data" is now demonstrated end-to-end on the collection side.
2. **Episode interaction budgets are model-relative harness calibration.** The 7B needs ~13
   messages; the teacher needed ~2× the 50-message budget (32/61 round-1 episodes graded CORRECT
   but cut mid-transcript → rightly ETL-excluded as incomplete rollouts). Collection budgets must
   be tuned per policy; grading is budget-agnostic either way.
3. **Off-policy behavior cloning transferred the teacher's form, not its function.** The
   student's median episode went 13 → 50–73 messages (teacher-style read-and-reconcile loops)
   while its pass rate FELL on tasks the base already solves. With double the eval budget it
   wanders longer and still hits the ceiling (4/9 held-out), and on the trained split its
   episodes overflow its own 32k serving context (vLLM 400 at 32,769 input tokens) — the learned
   trajectory length is incompatible with the student's own serving window, not just the eval
   budget. At 7B + LoRA r=32 + 79 examples + 1 epoch, imitation actively hurt. Style is easy to
   distill; competence is not.
4. **Buy the diagnostic before writing the read.** The "student just needs the teacher's budget"
   rescue was refutable for ~$2 GPU and an hour (the ml=100 pair) — it converted an ambiguous
   negative into a sharp one. The fail-closed report earned its keep twice: it refused to render
   the incomplete overflow arm rather than print a rate from a partial run.
5. **Unit economics keep holding.** Full teacher round — collection (2 rounds), ETL, SFT, 13
   delta/diagnostic arms — in one day for < $20 total, all on API + HF Jobs (no owned infra).

## Thesis read (2026-07-02)

- **The foundry's collection mechanism is validated** — verifier-filtered gold trajectories from
  a frontier teacher are cheap, high-yield, and tamper-checked. Strengthens the wedge.
- **The training recipe is now the open problem, not the data.** The negative scopes to
  single-epoch off-policy LoRA cloning on a 7B — untested: trajectory-length-matched data,
  multi-epoch dose, on-policy correction, RL against the verifier reward (the E13 path), a
  larger student (the 30B was always the P2 plan).
- **Pivot trigger (a) from the #176 note is NOT formally fired** ("properly-dosed teacher-filtered
  SFT at N≈30–50 shows no held-out lift" — this is still the 12-task corpus), but the burden has
  shifted: dose alone did not help (3.8× the data with better provenance made it worse, not
  flat), so the next training-side leg must explain why it would differ.

## Next experiment (cheap, days — founder's pick)

- **Trajectory-length-matched distillation:** train only on the 29 complete ≤50-message teacher
  episodes (already in the store), re-run the ml=50 delta — isolates pacing mismatch from
  capability gap for ~30 min GPU.
- **Multi-epoch dose** on the same 79 (a `TrainerConfig` parameter; same cost).
- If both stay negative, the SFT demonstration vehicle is dead at this scale and the pre-T0
  story leans on what did validate: the verified-data machine + the RL-ready deterministic
  reward — which is the lab-facing pitch anyway.
