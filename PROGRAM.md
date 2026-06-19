# Program State

Project state + handoff for humans, engineers, and AI agents. Read this before non-trivial work.
Keep it concise (see `CLAUDE.md`/`AGENTS.md` → **Program State**).

## Right Now

- **Phase 0 — Gate & scaffolding.** The repo skeleton ([`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md))
  and the frozen floor ([`DECISIONS.md`](./DECISIONS.md)) are in; the AI-operating layer lands with
  **E0-6 (#18)** (this file set). Next ready E0 work: the **agent skill layer** — skills.sh lock
  (**E0-10, #85**), `AssayInc/skills` + homegrown domain skills (**E0-11, #86**), and the `assay-brain`
  deep-recall skill (**E0-7, #73**) — plus two-lane CI + branch protection (**E0-2, #19**), the
  LocalStack dev loop (**E0-3, #20**), repo hygiene (**E0-4, #21**), and the Project v2 board
  (**E0-5, #22**). Phase-1 build proper starts at the contract-schema spine (**E1**), the join key for
  the whole system.

## Recently Landed

- **E0-6 (#18): AI-operating layer.** `CLAUDE.md` (the single auto-loaded constitution) + `AGENTS.md`
  symlink, `PROGRAM.md`, `ISSUES.md`, `tasks/{todo,lessons}.md`; the **`verify`-gate + locked-fixtures
  loop**, the "implement the next ready issue" trigger, and the quality bar — adapted to the polyglot,
  verification-infra domain. No `HANDOFF.md` (folded into `CLAUDE.md`); no `ci.yml` (that is E0-2/#19).
  _(fill PR # / merge commit on landing.)_
- **E0-8 (#74): `DECISIONS.md`** — the frozen floor (trust model, locked decisions 1C–T3, I1–I11, the
  15-vector threat bar, eval rigor) ported from the `brain` plans so the repo stands alone. (PR #82.)
- **E0-1 (#17): bootstrap polyglot monorepo skeleton** — Bun + Turborepo TS lane (`ts/**`), UV Python
  lane (`py/**`), shared `typescript-config`/`biome-config`, `contracts/` shells, the `verify` task
  graph, committed lockfiles. (PR #83, `c871960`.)

## Handoff Notes

- **CI is E0-2 (#19), not yet landed.** `bun run verify` is the gate and is green locally; the two-lane
  GitHub Actions workflow that runs it per PR (turbo + uv, cache-keyed) and branch protection on `main`
  arrive with E0-2. Until then, the **PR + verify-green + `/review`** convention in `CLAUDE.md` is the
  merge gate. E0-1 deliberately shipped no CI; E0-6 documents the invariant, E0-2 implements it.
- **Brain sibling + skill layer.** Strategy/research/vision live in `../brain/` (`AssayInc/brain`);
  recall via the `assay-brain` skill (E0-7, #73), part of the committed skill layer (skills.sh +
  `skills-lock.json`, **prefer-official**) set up in **E0-10 (#85)**,
  with homegrown domain skills in `AssayInc/skills` (**E0-11, #86**). Until that layer lands,
  `.agents/skills/` is absent — query `../brain/wiki` directly via the brain-side `wiki-query` skill /
  `qmd`. `CLAUDE.md` documents the layer as the design (per E0-10/E0-11/E0-7); this note tracks the
  build status.
- **Read order for a new agent:** `CLAUDE.md`/`AGENTS.md` (operating layer) → `DECISIONS.md` (why/rules)
  → `docs/ARCHITECTURE.md` (how/where). The build spine is the `contracts/` schema (E1) — built first
  because it is the join key both lanes and a buying lab verify against.
