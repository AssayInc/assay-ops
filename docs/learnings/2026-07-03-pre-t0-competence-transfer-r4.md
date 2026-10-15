# Learnings — pre-T0 competence-transfer r4 (#197): the composed fix fails, the dosed model is budget-starved

date: 2026-07-03 (same-day successor to `2026-07-03-pre-t0-competence-transfer.md`)
sources: assay-ops#197 (run comment), private HF dataset `AssayInc/pre-t0-drift-corpus`
(runs/sft-r4 + runs/delta-*-r4* + PINS.md), adapter `AssayInc/pre-t0-qwen25-coder-7b-sft-r4`
status: raw learning — distill into wiki (touches: data-foundry, eval-to-performance-proof,
deterministic-verification)

## What ran

The #192 round's two open questions, same pins (one vLLM v0.24.0 engine, `force_tool_calls=true`
every arm, 3 epochs/arm, K=3, fresh base arms): **(1) the composed fix** — SFT on the unchanged
29 length-matched teacher episodes at `num_train_epochs=5` (each fix had worked alone in r3) →
the 4-arm ml=50 delta; **(2) the budget diagnostic** — the r3 multi-epoch student's trained
split re-run at `message_limit=100` (both arms). ~$2 GPU. Two arms fail-fast-aborted on a stray
serving-window overflow and were re-run `--continue-on-fail` to full grids.

**Result (R1-framed, PRE-T0 DIRECTIONAL, never published):**

| read | base | sft | delta |
|---|---|---|---|
| composed × held-out (ml=50) | 7/9 | 2/9 | **−55.6** |
| composed × trained (ml=50) | 12/36 | 3/36 | **−25.0** |
| r3-multi-epoch × trained (ml=100 pair) | 12/35 (1 quarantined) | **30/36** | **+49.0** |

## Empirical learnings

1. **Dose interacts with data volume — the two r3 fixes do not compose on a tiny set.** Five
   epochs rescued the 79-example set (r3: +33.3/+36.1) but destroyed the 29-example one
   (train_loss 1.118, so it did converge — onto degenerate behavior): the composed student is
   ceiling-paced on every single episode (45/45 at the 50-message limit) and scores below base
   on both splits, despite training exclusively on short, complete episodes. Over-fitting a
   small imitation set doesn't reproduce the set's *behavior*; it degrades the policy wholesale.
   "More epochs" is only a fix when the data can absorb it.
2. **The r3 multi-epoch student was budget-starved, not lost.** At ml=100 its trained split goes
   25/36 → **30/36 (83.3%)** vs the same-budget base at 12/35 (34.3%). This is the exact
   opposite of the r2 under-trained model, where doubling the budget made things *worse* (−33.3)
   and the trained arm overflowed the serving window systemically. Same diagnostic shape, opposite
   verdict — the dose changed the answer. A pacing pathology on top of real competence costs
   budget; on top of no competence it costs everything.
3. **The serving-window overflow degraded from systemic (r2) to stochastic-rare (r4):** one
   confirmed 32k-overflow episode in each aborted first attempt, zero in the 45 full-grid re-run
   episodes. Still a real constraint — training-data and eval budgets must respect the student's
   serving window — but no longer the binding failure mode for the properly-dosed model.
4. **The quarantine gate fired for the first time in ~770 cumulative graded episodes** — a base
   episode whose grade wouldn't reproduce ("transient infra did not settle in 2 retries") was
   excluded as NaN and the report bracketed the conservative lower bound, exactly the 7A design
   (never a false 0, never a silent flake). The zero-flake record was never luck; the gate was
   just never needed until now.
5. **Controls keep reproducing:** base trained = 12/36 for the third consecutive round (and
   12/35-equivalent at ml=100 — the base doesn't use extra budget; median 11 messages).
6. **Fail-fast is the wrong default for measurement arms.** One overflow episode aborted two
   arms and cost a re-run; `--continue-on-fail` turns terminal per-episode errors into counted
   data. The fail-closed report still refuses partial grids, so honesty is preserved either way.

## Thesis read (2026-07-03, r4 addendum)

- **The best student so far is the r3 multi-epoch model** (held-out 9/9 at ml=50; trained 30/36
  at ml=100), and its remaining weakness is pacing, not competence. The composed shortcut is dead.
- **The recipe direction is now clear: scale the length-compatible data, not the knobs.** The
  validated collection machine makes that cheap (teacher yield ~83–98% through the verifier
  filter); collect more complete episodes at a student-calibrated budget instead of re-dosing
  tiny sets. Pacing-shaping (or just budget headroom) handles the rest.
- All directional, small-n, memorization-inflated on trained splits; nothing here touches the §6
  proof bar or the R1 no-publish line.

## Next (if the founder wants an r5; tracked: assay-ops#199, untriaged)

- **Scale the length-matched set:** another teacher collection round at a completion-friendly
  budget (e.g. ml=75–100 with only complete ≤50-message episodes admitted, or completion-forcing
  prompts), targeting 60–100 length-compatible examples, then 3–5 epochs. This is the first
  training-side leg where the data machine — not the trainer config — is the dial.
- Optional: an ml=100 *held-out* read on the r3-me model (its 9/9 at ml=50 leaves no failures to
  rescue, but the pacing cost is uncharacterized on unseen tasks).
