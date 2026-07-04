# Learnings — pre-T0 competence-transfer round (#192)

date: 2026-07-03
sources: assay-ops#192 (run comment), private HF dataset `AssayInc/pre-t0-drift-corpus`
(runs/sft-r3-lm + runs/sft-r3-me + runs/delta-*-r3 + PINS.md), adapters
`AssayInc/pre-t0-qwen25-coder-7b-sft-r3-{lm,me}`
status: raw learning — distill into wiki (touches: data-foundry, eval-to-performance-proof,
environment-economics)

## What ran

The #186 follow-up, options 1 + 2 only (option 3 — RL — stays off per the §8 SFT-only rule):
**(1) length-matched distillation** — SFT on only the 29 complete ≤50-message teacher episodes
(the ml=50-clean subset already in the store), r2 config otherwise; **(2) multi-epoch dose** —
the unchanged 79-example `sft-r2` set at `num_train_epochs=5` (max of the issue's 3–5). Each got
the 4-arm ml=50 delta at the r2 pins (Qwen2.5-Coder-7B @ c03e6d3, one pinned vLLM 0.24.0 engine
serving base + both LoRAs, `force_tool_calls=true` every arm, 3 epochs/arm; the two deltas share
the base arms). 135 graded episodes, **0 quarantined / 0 errored**; base reproduced r2's trained
split exactly (12/36). ~$5 GPU total; no new teacher collection.

**Result (R1-framed, PRE-T0 DIRECTIONAL, never published):**

| experiment | held-out | trained |
|---|---|---|
| length-matched (29 ex, 1 epoch) | 6/9 → 9/9, **+33.3** | 12/36 → 13/36, +2.8 |
| multi-epoch (79 ex, 5 epochs) | 6/9 → 9/9, **+33.3** | 12/36 → 25/36, **+36.1** |

## Empirical learnings

1. **The r2 "form-not-function" negative decomposes into two fixable recipe defects —
   under-training and trajectory-length mismatch — not a capability wall at 7B/LoRA.** Fixing
   *either one* flips the held-out delta from −22.2 to +33.3. Off-policy LoRA cloning of a
   frontier teacher DOES transfer competence at this scale once the data is length-compatible or
   the dose is real.
2. **Dose and length-matching buy different things.** The multi-epoch model (train_loss
   1.52 → 0.844) is the strongest performer (+36.1 trained, +33.3 held-out) but keeps the
   teacher's pacing: every one of its 45 episodes ran to the 50-message ceiling, and all 11 of
   its trained-split failures died at the limit. The length-matched model runs base-like
   episodes (median 11 messages, zero limit-hits — the r2 pathology is gone) and matches the
   held-out flip, but 29 mostly-easier examples didn't move the hard trained tier (+2.8).
   The two fixes are complementary, not redundant.
3. **An episode can hit the interaction ceiling and still grade CORRECT** — the multi-epoch
   student lands the deployed fix mid-episode and then wanders until the budget dies. Deployed-
   state grading is budget-agnostic (learnings 2026-07-02 #2), which is exactly what makes the
   eval robust to pacing pathologies the transcript would hide: reward comes from the cloud
   read, not from the agent looking finished.
4. **The #176 pivot trigger (a) — "properly-dosed teacher-filtered SFT at N≈30–50 shows no
   held-out lift" — is now answered in the negative: the SFT demonstration vehicle is ALIVE.**
   A properly-dosed run on 79 verifier-filtered examples shows a large held-out lift on this
   slice. The pre-T0 story no longer leans only on the data machine + RL-ready reward; the
   cheap SFT leg demonstrably closes the loop.
5. **Small-n honesty:** 3 held-out tasks × 3 epochs, and both experiments saturate at 9/9 — the
   +33.3 is ceiling-bounded and the splits are noisy by design (the accepted pre-T0 posture).
   The trained-split +36.1 is memorization-inflated by design (the learn-at-all check). None of
   this clears the §6 proof bar (no ≥3 seeds, no clustered SEs, no OOD slice) and none of it is
   publishable (R1); it is a directional green light, not a lift claim.
6. **Unit economics again:** both experiments + 6 delta arms + smoke ran same-day for ~$5 GPU
   on HF Jobs (the teacher data was already bought — $10.07 total across #186), all on API
   infra. A falsification round on the training recipe costs an afternoon.

## Thesis read (2026-07-03)

- **The full pre-T0 loop is now positive end-to-end at toy scale:** verifier-filtered frontier
  trajectories (validated in #186) → cheap SFT → a student that beats its base on tasks it never
  saw, graded by the same zero-flake reward (0 quarantined across ~607 graded episodes over the
  three rounds). This is the ammo the seat pitch and the P2 gate were waiting on.
- **The P2 gate's "positive training-side signal" condition has a candidate signal** — the
  re-set is the founder's call (`docs/priorities.md`); P2 still awaits the seat.
- **The open training-recipe question is now composition, not viability:** length-matched data
  at a real dose (the obvious r4: multi-epoch on length-matched data, or collection at a
  student-calibrated budget with completion-forcing), and whether the pacing pathology matters
  once budgets are realistic.

## Next experiment (cheap, if the founder wants an r4 before the seat lands)

- **Compose the two fixes:** multi-epoch on the 29 length-matched examples (~$2), betting the
  trained-tier gap closes without the ceiling-burning pacing.
- **A budget diagnostic on the multi-epoch student** (ml=100 pair) would say whether its 11
  at-limit trained failures are budget-starved or genuinely lost — same shape as the r2
  diagnostic, ~$2.
