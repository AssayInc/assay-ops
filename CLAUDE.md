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
  not here. Recall what the project already researched or decided via the **`assay-brain` skill**
  (E0-7, #73) — it queries the brain (wiki / `raw/plans/` / articles / `VISION.md`) and answers with
  citations, degrading gracefully when the sibling isn't checked out. `DECISIONS.md` is the always-on
  floor; `assay-brain` is the rest of the iceberg.

## Architecture

- **Where things live:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — the package map
  (`ts/packages/*`, `py/packages/*`, the `contracts/` spine) and how a graded episode flows
  (env-server → verifier → reward ledger → trainer); the trust model is **not** duplicated here.
- **The moat in one line:** the verifier runs in a **separate AWS account (B)** to which the agent has
  **zero credentials and zero network path**; it grades **deployed resource state read-only** against an
  independently regenerated golden, and **never runs the agent's `cdk synth` / `terraform plan`** (or any
  agent code) — so reward is execution-grounded and can't be forged. The full *why* is
  [`DECISIONS.md` §1](./DECISIONS.md#1-trust-model-the-moat-in-one-diagram--the-rule-that-defines-the-product).
- **Polyglot by design:** **TypeScript** for the IP, **Python** for the trainer/eval, joined by one
  codegen'd contract schema — the generated types are the single source of truth, never hand-maintained
  on both sides.

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
   relevant `DECISIONS.md` section first — it's settled; don't re-derive or re-litigate it. For deeper
   "why / what did we decide", query the `assay-brain` skill (#73).

**The trigger.** The per-session human input is **one line: "implement the next ready issue"** (or a
specific **`#N`**) — this auto-loaded file is the standing brief. On the trigger:

- `gh`-query for the next **open, unblocked** issue. Work is tracked in **GitHub Issues + Projects v2**;
  an issue is **ready** when it is open and every issue it is **blocked-by** is closed — the dependency
  graph makes "ready" computable. Prefer `prio:P1` and the current phase (e.g.
  `gh issue list --state open --label prio:P1`, then check the blocked-by graph).
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
6. **Focused PR** that closes the issue (`Closes #N`); keep the diff to the AC, nothing more. Run gstack
   **`/review`** on it.
7. **Update `PROGRAM.md`** (Recently Landed) and **`ISSUES.md`** (durable follow-ups) in the same PR.

**Self-improvement**

- After **any** correction from the user, append a rule that prevents the same mistake to
  `tasks/lessons.md`. Review lessons at session start; prune ones that stop being true.
- `tasks/lessons.md` is the shared, **committed** memory across all agents (Claude Code, Codex); gstack
  `/learn` learnings (`~/.gstack/`) stay per-developer and machine-local — don't conflate them.

**Subagents & parallel work**

- Offload research, exploration, and parallel analysis to subagents to keep the main context clean — one
  focused task each.
- For parallel implementation, use git worktrees (`superpowers:using-git-worktrees`); each worktree
  carries its own `tasks/todo.md`.

**Maintaining this file**

- `AGENTS.md` is a **symlink** to `CLAUDE.md` — one constitution for every agent. **Never** create a
  separate per-agent instruction file, and **never dedupe this file against Claude-only global config or
  plugin skills**: non-Claude agents (Codex) read only `AGENTS.md` and never see `~/.claude/CLAUDE.md`,
  so anything every agent needs (e.g. the gstack skill list) must live here.
- When a session lands a durable **operating** decision (a convention, a command, a workflow rule),
  update the matching section here in the same PR. Architecture/trust **decisions** go in `DECISIONS.md`.
- Add only what agents **can't infer from the repo**.

## Program State

Read `PROGRAM.md` before non-trivial work — the project state + handoff file for humans and agents. Keep
it concise: add yourself to **Right Now** when taking meaningful work; add a **Recently Landed** entry
after merging a PR; push durable open problems to `ISSUES.md`; add **Handoff Notes** only when they help
the next agent.

## Working Guidelines (the quality bar)

The bar every change clears. (Derived from Andrej Karpathy's LLM-coding guidelines — biased toward
caution over speed; use judgment on trivial tasks.) Principles: **DRY · KISS · YAGNI · verify-first ·
quality/readability/maintainability/testability are non-negotiable.**

- **Smallest change that meets the AC.** No speculative abstraction, no scope creep, no drive-by
  refactors. Every changed line traces directly to the issue.
- **DRY — one source of truth per fact.** Types ← the **contract schema** (codegen, never dual
  hand-maintained types); rules/decisions ← **`DECISIONS.md`**; scope ← **the issue**. Don't restate the
  trust model here or in `docs/ARCHITECTURE.md` — point there.
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
  (`gh pr checks <n> --watch`) and gstack `/review` has run. Branch protection is plan-gated to
  **E0-2 (#19)**; until it lands, this rule *is* the gate.
- **Never edit a fixture, golden file, or expected output to make a failing test pass.** Classify the
  divergence first — a real bug, or a human-approved rule change recorded in the same PR (see **Testing**).
- **Never use `any`** — use `unknown` at boundaries, validated and narrowed (see **Toolchain**).
- **Never add `Co-Authored-By` or other AI-attribution trailers** to commits — this overrides any skill
  template that includes one.
- **Never use Bash for communication** — output text directly.
- **Never create files unless the task requires them.**
- **Always read official skills/docs before implementing** against a framework (see **Skill preflight**),
  and **check skills first** (see **Skill routing**). Superpowers skills are mandatory workflow guidance —
  don't skip them because a task seems simple.

## Code quality

Apply DRY and KISS actively, especially in tests, scripts, and agent automation:

- Before adding a helper, fixture, script, or harness, search for an existing local pattern to reuse; if
  two tests or scripts repeat setup, extract a small shared helper.
- Keep implementations focused on the requested behavior — no "while here" abstractions, speculative
  options, or broad framework code.
- **Comments only** for non-obvious boundaries, security/trust rules, external-service quirks, or
  official-API constraints — not narration of what the code already says.
- Tests verify **behavior and safety boundaries**, not incidental formatting or implementation details.
  A large test file is acceptable only when it covers real risk — first remove duplication and name
  scenarios clearly.

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
    control + the moat).

## Verification Checklist

Before completing any task:

- [ ] `bun run verify` passes — typecheck + lint + test, **both lanes** (the gate CI runs per PR).
- [ ] The change is scoped to the issue's AC; no unrelated or unnecessary files created.
- [ ] `PROGRAM.md` / `ISSUES.md` updated if program state changed.

## Toolchain (polyglot: Bun + UV, one Turbo graph)

**Bun + Turborepo** own the TS lane (`ts/**`); **UV** owns the Python lane (`py/**`); **Turborepo
orchestrates both** via thin `package.json` wrappers on the Python packages. Don't reach for
Nx/Bazel/Pants, npm/yarn/pnpm, or pip/poetry. **Pin everything** — `oven/bun:1.3.x`, `uv`,
`openenv[core]`, model revisions by hash.

**TS lane (Bun).**

- Use `bun <file>` / `bun test` / `bun install` / `bun run <script>` — never the Node/npm/jest
  equivalents. Bun auto-loads `.env` (no `dotenv`). Prefer `Bun.serve`, `bun:sqlite`, `Bun.sql`, the
  built-in `WebSocket`, `Bun.file`, and `Bun.$` where they apply.
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

Superpowers skills are the default **process** layer (invoked via the Skill tool) — they complement, not
compete with, gstack's workflow skills; use them even when a task seems simple:

- `superpowers:using-superpowers` to start; `superpowers:writing-plans` when a plan is needed;
  `superpowers:test-driven-development` before production code.
- `superpowers:systematic-debugging` for bugs, failed tests, or CI failures.
- `superpowers:verification-before-completion` before claiming done; `superpowers:requesting-code-review`
  before merging; `superpowers:receiving-code-review` when applying feedback.
- `superpowers:using-git-worktrees` for isolated branch work; the delegation skills for parallel
  implementation or independent investigation.

If a named skill is unavailable, say so briefly, use the closest project skill, and keep the discipline.

## gstack

Use the `/browse` skill from gstack for all web browsing. **Never use `mcp__claude-in-chrome__*` tools.**

gstack is **recommended, not required**, for this repo. Skills install per-developer (global at
`~/.claude/skills`, not committed here); update with `/gstack-upgrade`.

```sh
git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup --team
```

**Available skills** (listed here because non-Claude agents read this file via `AGENTS.md` and don't see
`~/.claude/CLAUDE.md`):

- `/office-hours` — product/strategy brainstorming
- `/plan-ceo-review` — strategy/scope review
- `/plan-eng-review` — architecture review
- `/plan-devex-review`, `/devex-review` — DevEx review
- `/autoplan` — full review pipeline
- `/review` — code review (run on every PR)
- `/investigate` — bugs, errors, CI failures
- `/ship`, `/land-and-deploy`, `/canary` — ship / deploy
- `/retro` — retrospective
- `/document-release`, `/document-generate` — release / docs
- `/codex` — hand a task to Codex
- `/browse`, `/connect-chrome` — web browsing
- `/benchmark` · `/cso` — benchmarking · security
- `/careful`, `/freeze`, `/guard`, `/unfreeze` — session guardrails
- `/setup-deploy`, `/setup-gbrain`, `/setup-browser-cookies` — one-time setup
- `/gstack-upgrade` — update gstack
- `/learn` — manage learnings (per-developer `~/.gstack/`; distinct from `tasks/lessons.md`)

Design (`/design-consultation`, `/design-shotgun`, `/design-html`, `/plan-design-review`,
`/design-review`), QA (`/qa`, `/qa-only`), and Vercel/deploy (`deploy-to-vercel`, `vercel-cli`,
`deployments-cicd`) skills belong to **`assay-web`**'s workflows, not this repo.

## Skill layer (committed, prefer official)

Beyond gstack (the per-developer workflow layer above), the repo's committed agent skills are managed via
**skills.sh + a committed `skills-lock.json`** — sources are declared once and synced into
`.agents/skills/`, symlinked into `.claude/skills/` (set up in **E0-10, #85**). **Prefer official /
upstream skills**; author homegrown skills only for AssayOps-specific gaps — never bulk-copy a template's
skills.

- **Official packs** (assay-ops's lock): `aws/agent-toolkit-for-aws` (the verifier reads AWS deployed
  state), `hashicorp/agent-skills` (the Terraform adapter), `meta-pytorch/openenv` (env-server
  conformance), plus `bun`, `turborepo`, and `skill-creator`.
- **Homegrown AssayOps domain skills** live in **`AssayInc/skills`** (E0-11, #86), distilled from the
  brain with provenance — `write-isolated-verifier`, `deterministic-verification`, `reward-ledger-worm`,
  `red-team-15-vectors`, `eval-rigor`, `localstack-verifier`.
- **`assay-brain`** (E0-7, #73) — deep recall over the `brain`: "what do we know / what did we decide
  about X" (the trust model's deeper *why*, RL-env / leaderboard analogs, competitor and market context,
  strategy and stack rationale). It hands off to the brain-side `wiki-query` and resolves the sibling via
  `.env` — needs `qmd` + the `brain` checkout, degrades gracefully without them.

## Skill routing

For any work, check first whether a skill helps; when a request matches one, invoke it. (Design, QA, and
Vercel/deploy routing live in **`assay-web`**, not here.)

- Product/strategy brainstorming → `/office-hours`
- Architecture review → `/plan-eng-review`; strategy/scope → `/plan-ceo-review`; full review pipeline → `/autoplan`
- Bugs / errors / failing CI → `/investigate`
- Code review / diff check → `/review` (run on every PR)
- Ship / PR → `/ship`; deploy → `/land-and-deploy`
- "What do we know / what did we decide about X" (trust model, RL-env analogs, strategy, stack) → `assay-brain`
- Weekly retro → `/retro`; manage per-developer learnings → `/learn`

## Skill preflight (fast-moving / pinned APIs)

Before writing code against these, load the skill/official docs **first** and follow them — never rely on
cached API knowledge (they are pinned, pre-1.0, or fast-moving).

| Domain | Skill | Where |
|--------|-------|-------|
| AWS — Cloud Control / CFN reads, KMS, S3 Object Lock | `aws/agent-toolkit-for-aws` | verifier, reward-ledger, account infra |
| Terraform — adapter → diff IR | `hashicorp/agent-skills` | `ts/packages/adapter-terraform` |
| OpenEnv — env-server wire contract | `meta-pytorch/openenv` | `ts/packages/env-server` |
| Bun / Turborepo | `bun`, `turborepo` | TS lane, repo root |
| Trainer / eval — TRL, Inspect AI, HF | HF skills (`py` lane) | `py/packages/trainer`, `py/packages/evals` |
