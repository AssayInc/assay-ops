# #192 (E12) — training-side competence-transfer experiments (options 1 + 2)

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md + the PR + GitHub #192.

Founder directive (2026-07-03): run options 1 + 2 ONLY; option 3 (RL) OFF (§8 SFT-only — needs an
explicit founder call). Everything private/directional (I11/R1). ~$5 GPU; cancel all HF jobs when done.

## Ground (done)
- [x] #192 + #186 bodies AND comments (closing read); learnings note; run recipe doc; runs/PINS.md;
      DECISIONS.md §8; priorities.md; PROGRAM.md; lessons.md
- [x] prio:P1 set on #192; board Status → In Progress
- [x] Pins confirmed: Qwen2.5-Coder-7B-Instruct @ c03e6d3, LoRA r=32/α=16, vLLM on HF Jobs
      (l4x1, hermes parser), delta = ml=50, 3 epochs/arm, force_tool_calls=true, held-out =
      the pinned 3-task split (one per type; ids live in the private PINS only — I11)
- [x] Round-1 (ml=50) teacher logs identified: smoke (1 ep) + 12×5 → the 29 clean-correct subset
- [x] r2 recipe recovered: tools/{etl_run_r2,sft_job_r2,render_delta_r2}.py + HF job specs
- [x] Trainer code unchanged since mirror sync (d9c31dd → HEAD dd6dc23: no py/ diff)

## Experiment 1 — length-matched SFT (sft-r3-lm)
- [x] ETL round-1 (ml=50) logs only → runs/sft-r3-lm: 29 examples / 0 incorrect /
      32 excluded-incomplete ✓ (exactly as predicted); tripwire silent; 11/12 tasks (one S3 task
      lacks a clean ≤50-msg episode; id in the private PINS)
- [x] Upload runs/sft-r3-lm to the private mirror
- [x] SFT at the r2 config (1 epoch, max_length 16384) → adapter …-sft-r3-lm (train_loss 1.52, 161k tok)

## Experiment 2 — multi-epoch dose (sft-r3-me)
- [x] SFT on the SAME runs/sft-r2/sft.jsonl (79 examples), num_train_epochs=5 (max of the issue's
      3–5: strongest falsification of "under-trained" given one run and n=9 held-out), all else r2 —
      → adapter …-sft-r3-me (train_loss 0.844 @ epoch 5, 50 steps); stack json → runs/sft-r3-me/
      NOTE: both r3 jobs resolved transformers 5.13.0 (r2: 5.12.1) — minimums frozen per run; recorded

## Delta (both experiments)
- [x] One vLLM engine (l4x1): pinned v0.24.0 (r2-observed version), base + both adapters
- [x] Smoke clean, then all 6 arms: 135 graded episodes, 0 quarantined/0 errored; logs in the
      private store only; NO eval-retry needed (every log status=success)
- [x] Reads: LM heldout +33.3 (6/9→9/9) / trained +2.8 (12/36→13/36);
      ME heldout +33.3 (9/9) / trained +36.1 (12/36→25/36). Dispositions: sft-lm median 11 msgs
      0 limit-hits (pacing fixed); sft-me median 50, all episodes at ceiling (dose transfers
      competence through the pacing); base reproduces r2 trained exactly (12/36)

## Wrap
- [x] Cancel ALL HF jobs (0 active); sync new runs/ + PINS.md + tools to the mirror
- [x] PINS.md: sft-r3 / delta r3 sections complete with the read
- [x] docs/learnings/2026-07-03-pre-t0-competence-transfer.md
- [x] Result + read posted on #192
- [x] priorities.md: P1-6 strike-through + #192/P2-gate/freeze-list state notes (no re-ordering —
      the re-set stays the founder's call)
- [x] PROGRAM.md top bullet + Recently Landed (ISSUES.md untouched — nothing new deferred)
- [ ] bun run verify green → focused PR (Closes #192)
- [ ] Codex gpt-5.5 xhigh review → SHIP; present merge-ready, DO NOT merge without the founder's go
