# Program State

Project state + handoff for humans, engineers, and AI agents. Read this before non-trivial work.
Keep it concise (see `CLAUDE.md`/`AGENTS.md` → **Program State**).

## Right Now

- **Phase 0 — Gate & scaffolding.** The repo skeleton ([`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md))
  and the frozen floor ([`DECISIONS.md`](./DECISIONS.md)) are in; the AI-operating layer lands with
  **E0-6 (#18)** (this file set). The **agent skill layer** is landing: the **skills.sh lock + consumer `.agents/skills/`
  wiring is bootstrapped** (PR #89 — `skills-lock.json` + `bun`/`turborepo`/`karpathy-guidelines` + the
  `assay-brain` recall skill, vendored and symlinked into `.claude/`+`.hermes/`; `assay-brain` was built in
  `AssayInc/skills`, **#73 + #86**, closed). Still open in **E0-10 (#85)**: the prefer-official cloud/IaC
  packs — AWS / Terraform / OpenEnv + `skill-creator`; the six homegrown domain skills are **#86**. Other ready E0 work: two-lane CI + branch
  protection (**E0-2, #19**), the LocalStack dev loop (**E0-3, #20**), repo hygiene (**E0-4, #21**), and the
  Project v2 board (**E0-5, #22**). Phase-1 build proper starts at the contract-schema spine (**E1**), the
  join key for the whole system.

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
  recall via the **`assay-brain`** skill, built in `AssayInc/skills` (**#73 + #86**, closed). As of PR #89
  it's **committed into this repo's skill layer** (`.agents/skills/assay-brain`, symlinked into
  `.claude/`+`.hermes/`, hash-pinned in `skills-lock.json`), so every agent here — Codex, CI, a fresh clone —
  gets it with zero setup. It also still ships as a **per-developer install** (`AssayInc/skills` →
  `./install.sh`, symlinked into `~/.claude/skills`) that makes recall work from *any* Assay repo; on a dev
  machine that global copy shadows the committed one (same content). Both resolve `../brain` with zero config
  and degrade gracefully when the brain is absent. Still open in **#85**: the prefer-official cloud/IaC packs
  (AWS / Terraform / OpenEnv + `skill-creator`); the six homegrown domain skills are **#86**. `CLAUDE.md`
  documents the layer as the design.
- **Read order for a new agent:** `CLAUDE.md`/`AGENTS.md` (operating layer) → `DECISIONS.md` (why/rules)
  → `docs/ARCHITECTURE.md` (how/where). The build spine is the `contracts/` schema (E1) — built first
  because it is the join key both lanes and a buying lab verify against.
