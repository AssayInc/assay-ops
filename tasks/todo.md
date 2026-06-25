# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Ephemeral per-session; durable outputs → PR / PROGRAM.md / issues.

---

## #75 E2-5 — Golden-target generator (reproducible ephemeral target, 2A) — IN PROGRESS (branch `feat/e2-5-golden-target`)

**Goal (AC).** `generate(task, seed)` → deterministic, content-addressed **golden target** (the expected
normalized resource set the account-B verifier grades deployed state against). **Engine, NOT corpus**
(#76 owns the private per-task golden definitions). Gates #31.
1. `generate(task, seed)` byte-identical across K runs (feeds the #46 determinism check).
2. Runs in account B / verifier domain — never consumes the agent's synth/plan/state.
3. (#31's integration test grades deployed state vs this output — separate issue; #75 must produce a
   diffable golden.)
4. Golden artifacts content-addressed (hash reproducible from the record).

**Grounding (issue is an AI-written input, reconciled vs floor + brain — done):**
- DECISIONS.md **2A** (reproducible ephemeral target, code+seed; reward = zero normalized diff),
  **T1 / sec1 / sec8** (account B; never runs agent synth/plan; reads state only), **I3** (JCS canonical bytes).
- Brain (eng-architecture, deterministic-verification): golden = declarative/programmatic regeneration
  (NOT running reference IaC); an expected resource set + intent-bearing properties; feeds the 6A diff IR;
  **engine (#75) vs private corpus (#76)** is explicit.

**Design decisions:**
- New package **`py/packages/verifier`** (`assayops_verifier`) — account-B verifier core; #30/#32 extend it.
- Golden **not a contract schema** (verifier-internal): hand-written Pydantic `GoldenTarget`/`GoldenResource`
  (`address`/`type`/`properties`), diff-IR-compatible vocabulary.
- `generate(task: TaskSpec, seed: str) -> GoldenTarget`: resolves a per-task **GoldenBuilder** (the "code")
  via a `GoldenRegistry` (corpus seam); **fail-closed** on unknown task (vector #15: never silently reward);
  engine sorts resources by address (canonical) + rejects dup addresses.
- **Seed** → deterministic hash-based ephemeral tokens (no clock/RNG) via `GoldenContext.token(...)`. The
  separate `seed` param lets the verifier regenerate a per-episode ephemeral variant (anti-memorization,
  vector #14) or the canonical golden (`seed = task.seed`). Intent-bearing names (not the AWS-assigned
  suffixes that #34 normalization strips).
- **Content address** `golden_digest(target) -> str`: reuse `assayops_contracts.jcs.canonical_digest`
  (DRY, single-sourced) → lowercase 64-hex. Byte-identical regen ⇒ identical address.
- **Cross-package wiring (first in repo):** consume `assayops_contracts` by source path
  (`pythonpath`/`mypy_path` + `follow_imports=silent`) — extends the virtual-member convention; contracts
  untouched. Escalate to packaging contracts only if `verify` proves it fragile.

**Flags (surface on PR/issue; don't code around):**
1. AC4 "hash recorded in the trajectory/reward record": the locked reward-record schema has **no**
   golden-digest field (`additionalProperties:false`; editing it = a #28 fixture-change). Satisfied instead
   by **regenerability** (trajectory_id→task_id→`task.seed`) + `graderVersion`; #75 ships the `golden_digest`
   primitive. A dedicated record field would be a separate flagged contract change.
2. #75 establishes `py/packages/verifier` ahead of E2-1/#30 (skeleton); golden is verifier-core, #30 adds
   the deployed-state read path to the same package.

**Steps (TDD — each AC → failing test → minimal green):**
- [ ] Scaffold `py/packages/verifier` (pyproject, package.json, src, tests) mirroring siblings.
- [ ] RED→GREEN: determinism / ephemeral-seed / content-address / fail-closed / normalization / account-B purity.
- [ ] `bun install` + `uv lock`/`uv sync`; verify `bun install --frozen-lockfile` (the CI gotcha).
- [ ] `bun run verify` green; update PROGRAM.md; focused PR `Closes #75`; `/review` (Claude + Codex xhigh).
