# AssayOps — write-isolated verification infrastructure for cloud-infrastructure agents

`assay-ops` is the core monorepo: a **write-isolated verifier**, OpenEnv env-server, IaC adapters, and a
tamper-evident reward ledger (**TypeScript**) + the **Python** trainer/eval, bridged by **one codegen'd
contract schema**. The moat is a grader the trained agent **cannot reach**.

> **Stance.** You build **verification infrastructure**: correctness and the trust boundary outrank speed and cleverness. A plausible-but-wrong verifier is worse than none — when unsure, **prove it or flag it**, never paper over it.

## Project Focus

- **[`DECISIONS.md`](./DECISIONS.md) is the frozen floor** — trust model, locked architecture, threat bar,
  eval bar. Read it before touching code; it is **settled — flag, don't silently deviate**. Rules live
  there; this file is the operating layer.
- **Strategy / research / vision** live in the sibling `brain` repo (`../brain/`) — recall via the
  **`assay-brain` skill** (#73).

## Architecture

- **Package map + episode flow:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) (`ts/packages/*`,
  `py/packages/*`, the `contracts/` spine).
- **The moat:** the verifier runs in a **separate AWS account** with **zero agent creds/network**, grades
  **deployed state read-only**, and **never runs the agent's `cdk synth` / `terraform plan`** — so reward
  can't be forged. Why: [`DECISIONS.md` §1](./DECISIONS.md#1-trust-model-the-moat-in-one-diagram--the-rule-that-defines-the-product).

## Commands

```sh
bun install && uv sync     # set up both lanes (or: bun run setup)
bun run verify             # turbo run typecheck lint test (TS + Python) — THE gate
bun run build
```

`bun run verify` is the single local gate — green before claiming done. CI runs it on every PR (E0-2).

## Agent Operating Loop

**Session start.** Read `PROGRAM.md` (state + handoff) and `tasks/lessons.md` (apply past lessons).

**The trigger** is one line — **"implement the next ready issue"** (or a specific **`#N`**); this file is
the standing brief. `gh`-query the next **open, unblocked** issue (tracked in GitHub Issues + Projects v2;
*ready* = open with every blocker closed), preferring `prio:P1`.

**Task loop.**
1. **Validate** the issue against the code — accurate, unblocked, not already done? A contradiction or a
   locked decision in the way → **comment on the issue; don't code around it**.
2. **Plan** non-trivial work to `tasks/todo.md` before coding.
3. **Test-first** — each acceptance criterion → a failing test → implement to green. **Reuse before adding.**
4. **`bun run verify` green**, then a **focused PR** (`Closes #N`, diff scoped to the AC); run `/review`.
5. **Update `PROGRAM.md` / `ISSUES.md`** in the same PR.

**Self-improvement.** After any user correction, append a preventing rule to `tasks/lessons.md` — the
shared committed memory (distinct from per-developer gstack `/learn`).

**Subagents.** Offload research/exploration to keep context clean — one task each. Parallel work → git
worktrees (`superpowers:using-git-worktrees`).

**Maintaining this file.** `AGENTS.md` symlinks here — one constitution for every agent; never fork a
per-agent file or dedupe against Claude-only global config (Codex reads only `AGENTS.md`). Land durable
*operating* decisions here in the same PR; architecture/trust decisions go in `DECISIONS.md`. Add only
what agents can't infer from the repo.

## Working Guidelines (the quality bar)

DRY · KISS · YAGNI · verify-first. (After Karpathy's LLM-coding guidelines.)

- **Smallest change that meets the AC** — no speculative abstraction, scope creep, or drive-by refactors;
  every changed line traces to the issue.
- **DRY, one source of truth:** types ← the contract schema (codegen, never dual hand-maintained); rules ←
  `DECISIONS.md`; scope ← the issue.
- **Evidence, not assertion** — "done" = a pasted green `bun run verify`.
- **Think first** — state assumptions; surface multiple readings instead of choosing silently; if unclear,
  ask.
- **Reuse before adding** a helper/fixture/script; comments only for non-obvious boundaries, security/trust
  rules, or external-API constraints — never narration. Match surrounding style; keep modules focused.

## Critical rules

The **trust-boundary non-negotiables** are the **[`DECISIONS.md` §8 checklist](./DECISIONS.md#8-agent-non-negotiables-checklist)**
(verifier never runs agent code, account A/B isolation, WORM reward records, one-schema codegen, the
15-vector exit bar, T7 guardrails, eval rigor, private corpus, publish-gated). Violating one is a trust
break, not a style nit — **stop and flag**. Operating rules:

- **Locked grader:** never edit `contracts/vectors` or `tools/red-team` outside their owning
  `fixture-change` PR (owners in `DECISIONS.md` §8) — the agent that writes code never edits what scores it.
- **Never edit a fixture / golden to make a test pass** — classify the divergence (real bug vs. approved
  rule change) first.
- **Never push to `main`** — open a PR; merge only on green CI `verify` + `/review` (branch protection is E0-2).
- **Never** use `any` (use validated `unknown`), add AI-attribution trailers to commits, use Bash for
  communication, or create files the task doesn't need.

## Testing

- **TS lane** `bun test`, **Python lane** `pytest`; every source package wires `typecheck`/`lint`/`test`.
- **Test-first.** Goldens are locked (see Critical rules). **Gold trajectories + held-out eval are private,
  never committed** (contamination + moat).

## Toolchain (Bun + UV, one Turbo graph)

**Bun + Turborepo** own `ts/**`; **UV** owns `py/**`; Turbo drives both. Don't reach for
Nx/Bazel/npm/yarn/pnpm/pip/poetry. **Pin everything.** Adding a package:
[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) → *How to navigate*.

- **TS:** `bun <file|test|install|run>`, not Node/npm/jest; `unknown` at boundaries, **never `any`**;
  **factory functions over classes**; assertions only at an I/O boundary behind a runtime check.
- **Python:** `uv run` for `mypy` / `ruff` / `pytest`, via each package's thin `package.json` wrapper.

## Superpowers Workflow

Superpowers skills are the default **process** layer (via the Skill tool), complementing gstack:
`using-superpowers` to start · `writing-plans` · `test-driven-development` before code ·
`systematic-debugging` for failures · `verification-before-completion` · `requesting-code-review` before
merge · `receiving-code-review` on feedback · `using-git-worktrees`. If one is unavailable, say so and use
the closest project skill.

## gstack

Use `/browse` for web browsing — **never `mcp__claude-in-chrome__*`**. gstack is **recommended, not
required**; per-developer install (`garrytan/gstack` → `./setup --team`, not committed). Listed here
because non-Claude agents read `AGENTS.md`, not `~/.claude/CLAUDE.md`:

- **Plan / review:** `/office-hours` (product/strategy) · `/plan-eng-review` (architecture) ·
  `/plan-ceo-review` (scope) · `/autoplan` (review pipeline) · `/review` (every PR) · `/investigate` (bugs/CI)
- **Ship / ops:** `/ship` · `/land-and-deploy` · `/retro` · `/document-release` · `/codex` · `/benchmark` ·
  `/learn` (per-developer) · `/gstack-upgrade` · `/careful` `/freeze` `/guard` `/unfreeze`

Design, QA, and Vercel/deploy skills belong to `assay-web`, not this repo.

## Skills (committed layer)

- **skills.sh + `skills-lock.json`, prefer-official** (E0-10/#85): `aws/agent-toolkit-for-aws`,
  `hashicorp/agent-skills`, `meta-pytorch/openenv`, `bun`, `turborepo`, `skill-creator`. Homegrown AssayOps
  skills → `AssayInc/skills` (#86). **`assay-brain`** (#73) = brain recall.
- **Preflight:** before coding against AWS / Terraform / OpenEnv / TRL / Inspect AI, load its skill or
  official docs first — never cached API knowledge.
