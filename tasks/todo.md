# #197 (E12) — the #192 r4: composed fix + ml=100 diagnostic

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md + the PR + GitHub #197.

Founder-approved 2026-07-03 ("do it"): new issue + the two r4 legs; #196 merged first (#192 closed).
All numbers below are R1-framed: PRE-T0 DIRECTIONAL only, never published; trained/diagnostic
reads memorization-inflated by design.

- [x] #197 filed, boarded (Status/Lane/Epic), parented under epic E12, prio:P1
- [x] PR #196 squash-merged on the founder's go; #192 closed → board Done; remote branch deleted
- [x] sft-r4 trained (29 length-matched × 5 epochs, all else r2/r3; train_loss 1.118) → adapter
      …-sft-r4 (private)
- [x] One pinned vLLM v0.24.0 engine: base + sft-r4 + sft-me; fresh base arms
- [x] Composed 4-arm ml=50 delta: held-out 7/9 → 2/9 (−55.6), trained 12/36 → 3/36 (−25.0);
      45/45 sft episodes at the ceiling — the fixes don't compose on 29 examples
- [x] ml=100 trained diagnostic on the r3-me student: base 12/35 (1 quarantined — first ever,
      transient infra, correctly NaN-excluded per 7A) vs sft-me 30/36 → +49.0 — budget-starved,
      not lost
- [x] Fail-fast aborts (1 stray 32k-overflow episode each) → both sft arms re-run
      --continue-on-fail to FULL grids (0/45 overflows in re-runs; overflow now stochastic-rare)
- [x] All HF jobs cancelled (0 active); runs + PINS + tools synced to the private mirror
- [x] PINS.md sft-r4/delta-r4 sections with the read
- [x] docs/learnings/2026-07-03-pre-t0-competence-transfer-r4.md
- [x] Result + read posted on #197
- [x] PROGRAM.md top bullet + Recently Landed
- [ ] bun run verify green → focused PR (Closes #197); residency sweep before commit
- [ ] Codex gpt-5.5 xhigh review (stdin closed + liveness check) → SHIP; present merge-ready,
      DO NOT merge without the founder's go
