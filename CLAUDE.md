# AssayOps — write-isolated verification infrastructure for cloud-infrastructure agents

`assay-ops` is the core monorepo: the proprietary IP — a **write-isolated verifier**, an OpenEnv
env-server, IaC adapters, and a tamper-evident reward ledger — in **TypeScript**, plus the **Python**
trainer/eval, bridged by **one codegen'd contract schema**. The product is verifiable RL environments
for Infrastructure-as-Code agents; the moat is a grader the agent being trained **cannot reach**.

> **Stance.** You build **verification infrastructure**: correctness and the trust boundary outrank speed and cleverness. A plausible-but-wrong verifier is worse than none — when unsure, **prove it or flag it**, never paper over it.

## Project Focus

- **The frozen floor is [`DECISIONS.md`](./DECISIONS.md)** — the trust model, the locked architecture
  (1C–T3), the implementation decisions (I1–I11), the 15-vector threat bar, and the eval-rigor bar.
  Read it before touching code. It is **settled: flag, don't silently deviate** — never re-litigate a
  decision there or quietly work around it. **Rules live there; this file is the operating layer.**
- **Strategy, research, and vision live in the sibling `brain` repo** (`../brain/`, `AssayInc/brain`),
  not here. Query it on demand via the **`assay-brain` skill** (#73) — it finds and answers from the
  brain (wiki / `raw/plans/` / articles / `VISION.md`) with citations, and degrades gracefully when the
  sibling isn't checked out. `DECISIONS.md` is the always-on floor; `assay-brain` is the rest of the
  iceberg. *(Until #73 lands, query `../brain/wiki` with the brain-side `wiki-query` skill or `qmd`.)*
- **Cleno is a template, not a clone** ([`DECISIONS.md` I9](./DECISIONS.md#4-implementation-decisions-i1i11)).
  AssayOps lifted Cleno's TS tooling skeleton and this AI-operating layer — never its fiscal domain.
  Don't "sync from Cleno"; port a specific convention deliberately if a need arises.

## Architecture

- **Where things live:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — the package map
  (`ts/packages/*`, `py/packages/*`, the `contracts/` spine) and how a graded episode flows
  (env-server → verifier → reward ledger → trainer). It points back to `DECISIONS.md` for the *why*;
  the trust model is **not** duplicated across the two.
- **The moat in one line:** the verifier runs in a **separate AWS account (B)** to which the agent has
  **zero credentials and zero network path**; it grades **deployed resource state read-only** against an
  independently regenerated golden, and **never runs the agent's `cdk synth` / `terraform plan`** (or any
  agent code) — so reward is execution-grounded and can't be forged. The full *why* is
  [`DECISIONS.md` §1](./DECISIONS.md#1-trust-model-the-moat-in-one-diagram--the-rule-that-defines-the-product).
- **Polyglot by design** ([I1/I2](./DECISIONS.md#4-implementation-decisions-i1i11)): **TypeScript** for
  the IP, **Python** for the trainer/eval, joined by one codegen'd contract schema (5A/I3) — the
  generated types are the single source of truth, never hand-maintained on both sides.

## Commands

```sh
bun install && uv sync     # set up both lanes (or: bun run setup)
bun run verify             # turbo run typecheck lint test — across the TS + Python lanes; THE gate
bun run build              # turbo run build
bun run typecheck | lint | test   # one stage of the gate across both lanes
```

`bun run verify` is the **single local gate** — run it (green) before claiming any work done. CI runs
the same gate on every PR (**E0-2, #19**).

## Agent Operating Loop

How agents and engineers work here, session after session.

**Session start**

1. Read `PROGRAM.md` — program state + handoff notes.
2. Read `tasks/lessons.md` — apply relevant lessons before starting.
3. If the task touches the trust boundary, the contract schema, fixtures, or the threat bar, re-read the
   relevant `DECISIONS.md` section first — it's settled; don't re-derive or re-litigate it.

**The trigger.** The per-session human input is **one line: "implement the next ready issue"** (or a
specific **`#N`**). There is **no paste-able HANDOFF prompt** — it would duplicate this auto-loaded
constitution (a DRY violation), and there is **no `HANDOFF.md`**. On the trigger:

- `gh`-query for the next **open, unblocked** issue. Work is tracked in **GitHub Issues + Projects v2**
  ([I4](./DECISIONS.md#4-implementation-decisions-i1i11)); an issue is **ready** when it is open and every
  issue it is **blocked-by** is closed — the dependency graph makes "ready" computable. Prefer
  `prio:P1` and the current phase (e.g. `gh issue list --state open --label prio:P1`, then check the
  blocked-by graph), respecting the locked epic/task mapping in
  [`DECISIONS.md` §3](./DECISIONS.md#3-locked-tasks-t1t13--epic-mapping).
- Or take the **`#N`** the human named.

**Task loop**

1. **Validate the issue against the current code** — accurate? unblocked? not already done? If it
   contradicts the repo or a locked decision, **comment on the issue and stop — don't code around it.**
2. **Don't re-litigate locked decisions** (`DECISIONS.md`). If the task seems to require deviating,
   **flag it; never silently deviate.**
3. **Plan first** for non-trivial work: write checkable items to `tasks/todo.md` before touching code.
4. **Test-first.** Turn each acceptance criterion into a **failing test**, then implement to green.
   **Reuse before adding** — search for an existing helper/module first.
5. **`bun run verify` green** — the whole gate, both lanes.
6. **Focused PR** that closes the issue (`Closes #N`); keep the diff to the AC, nothing more.
7. **Update `PROGRAM.md`** (Recently Landed) and **`ISSUES.md`** (durable follow-ups) in the same PR.

**Self-improvement**

- After **any** correction from the user, append a rule that prevents the same mistake to
  `tasks/lessons.md`. Review lessons at session start; prune ones that stop being true. This file is the
  shared, committed memory across all agents (Claude Code, Codex).

**Subagents & parallel work**

- Offload research, exploration, and parallel analysis to subagents to keep the main context clean — one
  focused task each.
- For parallel implementation, use git worktrees (`superpowers:using-git-worktrees`); each worktree
  carries its own `tasks/todo.md`.

**Maintaining this file**

- `AGENTS.md` is a **symlink** to `CLAUDE.md` — one constitution for every agent. **Never** create a
  separate per-agent instruction file, and never dedupe this file against Claude-only global config
  (Codex reads only `AGENTS.md`).
- When a session lands a durable **operating** decision (a convention, a command, a workflow rule),
  update the matching section here in the same PR. Architecture/trust **decisions** go in `DECISIONS.md`.
- Add only what agents **can't infer from the repo**.

## Program State

Read `PROGRAM.md` before non-trivial work — the project state + handoff file for humans and agents. Keep
it concise: add yourself to **Right Now** when taking meaningful work; add a **Recently Landed** entry
after merging a PR; push durable open problems to `ISSUES.md`; add **Handoff Notes** only when they help
the next agent.

## Working Guidelines (the quality bar)

The bar every change clears. (Biased toward caution over speed — use judgment on trivial tasks.)

- **Smallest change that meets the AC.** No speculative abstraction, no scope creep, no drive-by
  refactors. Every changed line traces directly to the issue.
- **DRY — one source of truth per fact.** Types ← the **contract schema** (codegen, never dual
  hand-maintained types); rules/decisions ← **`DECISIONS.md`**; scope ← **the issue**. Don't restate the
  trust model here or in `docs/ARCHITECTURE.md` — point to `DECISIONS.md`.
- **KISS / YAGNI.** Minimum code that solves the problem. "Would a senior engineer call this
  overcomplicated?" → simplify.
- **Evidence, not assertion.** "Done" = a pasted **green `bun run verify`**, never a claim. Always
  verify before completing.
- **Think before coding.** State assumptions explicitly; if multiple readings exist, surface them — don't
  pick silently. If something is unclear, stop and ask.
- **Match surrounding style**, and **compartmentalize** — focused modules, ~200–400 lines per file.

## Critical rules (non-negotiable)

The **trust-boundary non-negotiables** — the verifier never runs agent code; account A/B isolation with
no A→B path; reward records KMS-signed + S3 Object Lock (WORM), never a mutable DB row; one contract
schema → codegen both languages; the 15-vector red-team exit bar (R1: any open vector ⇒ **STOP**); T7
cost-bomb guardrails are P1-blocking; the §6 eval-rigor bar; gold/held-out corpus stays private;
publish-gated posture — are the **[`DECISIONS.md` §8 checklist](./DECISIONS.md#8-agent-non-negotiables-checklist)**.
Violating one is a **trust-boundary break, not a style nit**; if a task seems to require it, **stop and
flag it.** The **operating-layer** rules this file owns:

- **Locked fixtures are off-limits.** Edit **`contracts/vectors`** only in a `fixture-change` PR from
  **#28** (E1-3); edit **`tools/red-team`** only in a `fixture-change` PR from **#56** (E10-1). **All
  other PRs are barred.** This is the write-isolated-verifier thesis applied to the repo: the agent that
  writes code never edits the grader it is scored against.
- **Never push directly to `main`.** Open a PR; merge only after CI `verify` is green
  (`gh pr checks <n> --watch`). Branch protection is plan-gated to **E0-2 (#19)**; until it lands, this
  rule *is* the gate.
- **Never edit a fixture, golden file, or expected output to make a failing test pass.** Classify the
  divergence first — a real bug, or a human-approved rule change recorded in the same PR (see **Testing**).
- **Never add `Co-Authored-By` or other AI-attribution trailers** to commits — this overrides any skill
  template that includes one.
- **Never create files unless the task requires them.** No `HANDOFF.md` — its content folds into this file.
- **Check skills first** (see **Skill routing**); Superpowers skills are mandatory workflow guidance — do
  not skip them because a task seems simple.

## Testing

The verifiable loop's external truth is **`bun run verify`**, run by CI on every PR (E0-2, #19).

- **TS lane:** `bun test`. **Python lane:** `pytest`. Every *source* package wires `typecheck` / `lint` /
  `test` so `turbo run` never silently omits it (the config-only packages — `typescript-config`,
  `biome-config` — export config and have no gate tasks). Use `bun test --pass-with-no-tests` /
  `pytest` placeholders until a real suite exists.
- **Test-first:** each acceptance criterion → a failing test → implement to green.
- **Fixtures & golden files are locked** — the agent that writes the code never adjusts the grader:
  - **`contracts/vectors`** (JCS byte-parity goldens) change **only** via a `fixture-change` PR from
    **#28**; **`tools/red-team`** (the 15 attack vectors) **only** via a `fixture-change` PR from **#56**.
  - A divergence from a golden is a real bug **or** a human-approved rule change — classify it first;
    approved fixture changes are recorded in the owning `fixture-change` PR, never slipped in to make a
    test pass.
  - **Gold trajectories + held-out eval are private, never committed** to any code repo (contamination
    control + the moat) ([`DECISIONS.md` I11](./DECISIONS.md#4-implementation-decisions-i1i11)).

## Verification Checklist

Before completing any task:

- [ ] `bun run verify` passes — typecheck + lint + test, **both lanes** (the gate CI runs per PR).
- [ ] The change is scoped to the issue's AC; no unrelated or unnecessary files created.
- [ ] `PROGRAM.md` / `ISSUES.md` updated if program state changed.

## Toolchain (polyglot: Bun + UV, one Turbo graph)

**Bun + Turborepo** own the TS lane (`ts/**`); **UV** owns the Python lane (`py/**`); **Turborepo
orchestrates both** via thin `package.json` wrappers on the Python packages
([I2](./DECISIONS.md#4-implementation-decisions-i1i11)). Don't reach for Nx/Bazel/Pants, npm/yarn/pnpm,
or pip/poetry. **Pin everything** — `oven/bun:1.3.x`, `uv`, `openenv[core]`, model revisions by hash
([I8](./DECISIONS.md#4-implementation-decisions-i1i11)).

**TS lane (Bun).**

- Use `bun <file>` / `bun test` / `bun install` / `bun run <script>` — never the Node/npm/jest
  equivalents. Bun auto-loads `.env` (no `dotenv`). Prefer `Bun.serve`, `bun:sqlite`, `Bun.sql`, the
  built-in `WebSocket`, and `Bun.file` where they apply.
- **TypeScript:** `unknown` at boundaries (validated + narrowed), **never `any`**; no broad assertions
  outside an I/O boundary behind a runtime check; explicit domain types + discriminated unions;
  **factory functions over classes**. Keep generated/framework types at the edge.
- Add a TS package under `ts/packages/<name>/`, extending the shared `@assayops/typescript-config` +
  `@assayops/biome-config` (see [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) → *How to navigate*).

**Python lane (UV).**

- Use `uv sync` / `uv run <tool>`; UV owns deps + the shared `.venv`. Per package: `mypy` (typecheck),
  `ruff check` (lint), `pytest` (test), driven through the package's `package.json` wrapper so the one
  Turbo graph sees them.
- Add a Python package under `py/packages/<name>/` with a `pyproject.toml` **and** a thin `package.json`
  whose `typecheck`/`lint`/`test` scripts shell to `uv run` (see `docs/ARCHITECTURE.md`).

## Superpowers Workflow

Use Superpowers skills as the default process layer for engineering work:

- Start with `superpowers:using-superpowers` + any relevant project skill.
- `superpowers:writing-plans` when a plan is needed; `superpowers:test-driven-development` before
  production code; `superpowers:systematic-debugging` for bugs, failed tests, or CI failures.
- `superpowers:verification-before-completion` before claiming done; `superpowers:requesting-code-review`
  before merging; `superpowers:receiving-code-review` when applying feedback;
  `superpowers:using-git-worktrees` for isolated branch work.

If a named Superpowers skill is unavailable in the current environment, say so briefly, use the closest
project skill, and keep the same discipline.

## Skill routing

For any work, check first whether a skill helps. When a request matches one, invoke it.

- **`assay-brain` (#73)** — "what do we know / what did we decide about X" (the trust model's deeper *why*,
  RL-env / leaderboard analogs, competitor and market context, strategy and stack rationale). It queries
  the brain so you don't grep `../brain` by hand. *(Not built yet — until then use the brain-side
  `wiki-query` skill / `qmd`.)*
- **gstack** (recommended, not required; installs per-developer, not committed here): `/browse` for all
  web browsing (never `mcp__claude-in-chrome__*`); `/review` to review every PR; `/ship` to ship/PR;
  `/investigate` for bugs and failures; `/plan-eng-review` for architecture review; `/office-hours` for
  product/strategy questions.

**Skill preflight (fast-moving APIs).** Before writing code against OpenEnv, TRL, Inspect AI, the AWS
CDK/jsii, or the AWS SDK, load its skill/official docs **first** and follow them — never rely on cached
API knowledge. These are pinned, pre-1.0, or fast-moving ([I6/I8](./DECISIONS.md#4-implementation-decisions-i1i11)).
