# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## DECISIONS.md + ARCHITECTURE.md faithfulness pass (vs `../brain/raw/plans`)

**Goal:** close the gaps a 4-plan audit found between the committed reference docs and their source
plans. ADD missing load-bearing content + fix two consistency defects; trim the one bloat block. (Docs
own issues #74/#17, both merged — this is faithful maintenance, "plans win → fix the doc".)

### DECISIONS.md
- [x] **§3 — add a "Phases (T0-relative)" block** so the table's `Phase` column is legible (proof-first):
      Phase 0–4, the ~13–15-wk T0 clock, folding in N≈30–50 + cut-to-30 + proof-only fallback + the two
      hard gates (RL/eval owner; proof-clears-bar-before-pitch).
- [x] **§3 — add the Lane legend + A↔C conflict / "C after B" sequencing** (eng-arch §Parallelization).
- [x] **§4 I3 — pin the signing crypto** (`SHA-256 → KMS asymmetric ECDSA P-256, MessageType=DIGEST`) so
      ARCHITECTURE's existing pointer resolves (impl-plan §3).
- [x] **§7 — fix the E1/E2/E3 collision + add the two missing flywheel bets + D1=C gating** (roadmap):
      spell out the bets (lab-agnostic / ELT second act / publish verifier-isolation), mark them distinct
      from build-epics E1–E3, restore the safety+warm-path gate, record rejected alternatives.
- [x] **§8 — add two scope non-negotiables:** build-only-the-IP / reuse-the-rest list; RL is SFT-only /
      stretch, off the critical path (eng-arch §NOT-in-scope + §reuse).
- [x] **Sources — reword the roadmap row** so it describes the flywheel bets, not "E1/E2/E3".

### docs/ARCHITECTURE.md
- [x] **Spine section — add the JCS schema-modeling rules** (big ints/nonces/timestamps as strings;
      bounded doubles; reject NaN/Inf), the `just codegen` entry point, and the parity-gate mechanism
      (impl-plan §3/§5). Highest-value gap (byte-parity is a §8 non-negotiable).
- [x] **Compress the ~11-line "Layout note"** (`ts/` vs `apps/`) to ~3 lines, drop the 2 turborepo URLs
      (flagged by 3/4 auditors as the one clear bloat block).
- [x] **`tasks/` layout line — note the deferred families** (migration/incident/cost + Pulumi → after
      drift&debug; cheap via 6A).

### Verify
- [x] `bun run verify` green; faithful quotes vs plans; focused PR (separate from the merged #84).

### Review

- **Done:** 6 `DECISIONS.md` edits (Phases block; Lane legend + A↔C sequencing; I3 signing crypto; §7
  flywheel rewrite + E1/E2/E3 disambiguation; §8 build-vs-reuse + RL-training-deferred; Sources reword) + 2
  `docs/ARCHITECTURE.md` edits (spine schema-rules/`just codegen`/parity-gate; Layout-note compression).
- **Net:** DECISIONS 378→412 (+34, high-value); ARCHITECTURE 145→146 (spine grew, layout-note trimmed —
  net flat). `bun run verify` green.
- **Faithfulness:** every addition is quoted from a source plan (eng-arch §NOT-in-scope/§reuse/
  §Parallelization; proof-first §phases/gates/N; impl-plan §3 signing+schema; roadmap D1/E1/E2/E3). The
  two consistency defects are fixed (E1/E2/E3 collision; the previously-undefined `Phase` column).
- **Scope:** separate PR from the merged #84; the docs own #74/#17 — faithful maintenance ("plans win →
  fix the doc"), not re-litigation.
