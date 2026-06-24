# AssayOps — write-isolated verification infrastructure for cloud-infrastructure agents

`assay-ops` is the core monorepo: a **Python** proof-critical core — **write-isolated verifier**, OpenEnv
env-server, IaC adapters, tamper-evident reward ledger, **and** the trainer/eval — with **TypeScript**
kept for the public/web surface (`@assayops/contracts`, `assay-web`), bridged by **one codegen'd contract
schema**. The moat is a grader the trained agent **cannot reach**.

> **Stance.** You build **verification infrastructure**: correctness and the trust boundary outrank speed and cleverness. A plausible-but-wrong verifier is worse than none — when unsure, **prove it or flag it**, never paper over it.

## Project Focus

- **[`DECISIONS.md`](./DECISIONS.md) is the frozen floor** — trust model, locked architecture, threat bar,
  eval bar. Read it before touching code; it is **settled — flag, don't silently deviate**. Rules live
  there; this file is the operating layer.
- **Strategy / research / vision** live in the sibling `brain` repo (`../brain/`) — recall via the
  **`assay-brain` skill**.

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

`bun run verify` is the single local gate — green before claiming done. CI runs it on every PR.

## Agent Operating Loop

**Session start.** Read `PROGRAM.md` (state + handoff) and `tasks/lessons.md` (apply past lessons).

**The trigger** is one line — **"implement the next ready issue"** (or a specific **`#N`**); this file is
the standing brief. `gh`-query the next **open, unblocked** issue (tracked in GitHub Issues + Projects v2;
*ready* = open with every blocker closed), preferring `prio:P1`.

**Task loop.**
1. **Validate + ground.** Before coding, check the issue against the code **and** the frozen floor: read the
   relevant **`DECISIONS.md`** sections and recall **assay-brain** (the plans + rationale). The issue was
   authored by another AI agent — it can be wrong, stale, or missing a locked detail, so **don't trust it
   blindly**; ground every requirement in `DECISIONS.md` + brain + the issue, and reconcile the three.
   Accurate, unblocked, not already done? A contradiction or a locked decision in the way → **comment on the
   issue; don't code around it**.
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
15-vector exit bar, guardrails, eval rigor, private corpus, publish-gated). Violating one is a trust
break, not a style nit — **stop and flag**. Operating rules:

- **Locked grader:** never edit `contracts/vectors` or `tools/red-team` outside their owning
  `fixture-change` PR (owners in `DECISIONS.md` §8) — the agent that writes code never edits what scores it.
- **Never edit a fixture / golden to make a test pass** — classify the divergence (real bug vs. approved
  rule change) first.
- **Never push to `main`** — open a PR; merge only on green CI `verify` + `/review` (branch protection not yet enforced — `ISSUES.md`).
- **Never** use `any` (use validated `unknown`), add AI-attribution trailers to commits, use Bash for
  communication, or create files the task doesn't need.

## Testing

- **TS lane** `bun test`, **Python lane** `pytest`; every source package wires `typecheck`/`lint`/`test`.
- **Test-first.** Goldens are locked (see Critical rules). **Gold trajectories + held-out eval are private,
  never committed** (contamination + moat).

## Toolchain (UV + Bun, one Turbo graph)

**UV** owns `py/**` (the proof-critical core); **Bun + Turborepo** own `ts/**` (the consumer/web surface);
Turbo drives both. Don't reach for Nx/Bazel/npm/yarn/pnpm/pip/poetry. **Pin everything.** Adding a package:
[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) → *How to navigate*.

- **Python (the proof-critical core):** `uv run` for `mypy` / `ruff` / `pytest`, via each package's thin
  `package.json` wrapper. `object` + a runtime narrow (Pydantic / `isinstance`) at boundaries, **never `Any`**
  — `object` is Python's `unknown`; bare `Any` is contagious like TS `any`. Open JSON payloads (env
  observations, deployed state) get a Pydantic model or `dict[str, object]`, not `dict[str, Any]`. Enforced by
  mypy `disallow_any_explicit` + ruff `ANN401` (relaxed for codegen output + tests). Structured logging via
  **structlog** (the pino analog) — **never bare `print`**.
- **TS (the consumer/web surface):** `bun <file|test|install|run>`, not Node/npm/jest; `unknown` at
  boundaries, **never `any`**; **factory functions over classes**; assertions only at an I/O boundary behind a
  runtime check; structured logging via **`@assayops/logger`** (pino) — **never `console.log`**.

## Superpowers Workflow

Superpowers skills are the default **process** layer (via the Skill tool), complementing gstack:
`using-superpowers` to start · `writing-plans` · `test-driven-development` before code ·
`systematic-debugging` for failures · `verification-before-completion` · `requesting-code-review` before
merge · `receiving-code-review` on feedback · `using-git-worktrees`. If one is unavailable, say so and use
the closest project skill.

## gstack

Use the `/browse` skill from gstack for all web browsing — **never `mcp__claude-in-chrome__*` tools**.
gstack is a per-developer install (`garrytan/gstack` → `./setup --team`, not committed); the full skill set
is listed here because non-Claude agents read `AGENTS.md` (this file), not `~/.claude/CLAUDE.md`.

Available skills:

- `/office-hours` — product/strategy office hours
- `/plan-ceo-review` — CEO/founder-mode plan review
- `/plan-eng-review` — eng-manager-mode plan review
- `/plan-design-review` — designer's-eye plan review
- `/design-consultation` — research + propose a complete design system
- `/design-shotgun` — generate and compare multiple design variants
- `/design-html` — production-quality HTML/CSS finalization
- `/review` — pre-landing PR review
- `/ship` — ship workflow (tests, diff, version bump, PR)
- `/land-and-deploy` — land and deploy
- `/canary` — post-deploy canary monitoring
- `/benchmark` — performance-regression detection
- `/browse` — fast headless browser for QA + dogfooding
- `/connect-chrome` — launch GStack Browser (AI-controlled Chromium)
- `/qa` — QA a web app and fix the bugs found
- `/qa-only` — report-only QA
- `/design-review` — designer's-eye visual QA + fixes
- `/setup-browser-cookies` — import real-browser cookies into the browse session
- `/setup-deploy` — configure deploy settings for `/land-and-deploy`
- `/setup-gbrain` — set up gbrain (CLI, brain, MCP, per-repo policy)
- `/retro` — weekly engineering retrospective
- `/investigate` — systematic debugging + root-cause analysis
- `/document-release` — post-ship documentation update
- `/document-generate` — generate missing docs from scratch
- `/codex` — OpenAI Codex CLI wrapper
- `/cso` — Chief Security Officer mode
- `/autoplan` — auto-review pipeline (CEO/design/eng/DX)
- `/plan-devex-review` — interactive developer-experience plan review
- `/devex-review` — live developer-experience audit
- `/careful` — destructive-command guardrails
- `/freeze` — restrict edits to a directory for the session
- `/guard` — full safety mode (warnings + scoped edits)
- `/unfreeze` — clear the freeze boundary
- `/gstack-upgrade` — upgrade gstack
- `/learn` — manage project learnings

## Skills (committed layer)

Vendored skills live in `.agents/skills/` (symlinked into `.claude/`+`.hermes/`), pinned by `skills-lock.json`
and auto-loaded by name/description — the lock is the source of truth for what's installed.

- **Adding a skill:** `npx skills add <repo> --skill <name>` with default agent targeting (**never `-a '*'`** —
  it litters the repo); take only the on-target skills from a multi-skill repo, not the whole pack.
- **Source bar:** prefer official/first-party; a well-adopted, maintained community skill is an acceptable
  fallback only where none official exists. Homegrown AssayOps skills → `AssayInc/skills`; **`assay-brain`** = brain recall.

## Skill preflight (ground in official docs FIRST)

Before writing code against **any external library, API, or framework** — including a "stable" one you think
you know (a validator like `ajv`, a logger like `pino`, an SDK) — load its **skill (or the official docs)
FIRST** and follow them. Verify **config, idioms, and test tooling** against the primary source, **never
cached knowledge**. Hand-rolling what a library already provides (redaction, validation) is a defect magnet.
*(A repeated correction — see `tasks/lessons.md`.)* The table below maps the project's fast-moving domains to
their vendored skills; the rule applies beyond it.

| Domain | Skill(s) | Surface |
|--------|----------|---------|
| AWS | **`aws-sdk-python-usage`** (boto3) · `aws-cloudformation` · `aws-cdk` · `aws-iam` | verifier reads deployed state read-only via **boto3** Cloud Control `get_resource`/`list_resources` + CFN drift; ledger KMS/S3 (boto3); CDK adapter + drift tasks. `aws-sdk-js-v3-usage` is **demoted to the TS consumer/web surface** (`assay-web` / dashboards), not the verifier read path. |
| Terraform | `terraform-style-guide` · `terraform-test` | the Terraform → diff-IR adapter |
| OpenEnv | `openenv-cli` · `generate-openenv-env` | the OpenEnv-compatible env-server |
| TRL / HF Hub | `trl-training` · `hf-cli` | the SFT + LoRA trainer |
| Inspect AI | `map-inspect-packages` · `reading-logs` · `babysitting-evals` | the eval harness (deploy-verifier as `Scorer`) |
| LocalStack | `localstack` · `localstack-deploy` · `localstack-iam` · `localstack-state` · `localstack-logs` | the local dev loop |
| Python lane (language-level) | `python-type-safety` · `python-testing-patterns` · `async-python-patterns` · `python-design-patterns` · `ruff` · `uv` | the `Any`/typing policy + `mypy --strict`; pytest + TDD; the asyncio env-server + concurrent sessions; composition/factories; lint+format; the uv workspace. (`python-performance-optimization` is situational — the verifier is I/O-bound on cloud reads, not CPU-bound.) |
| Python lane (runtime robustness) | `python-resilience` · `python-error-handling` · `python-configuration` · `python-observability` | the verifier's transient-vs-genuine-failure rule (`deterministic-verification`) + boto3 adaptive retries; parsing untrusted IaC/boto3 responses at the verifier/adapter boundary; typed settings + secrets (`pydantic-settings`) for the ledger/account creds; the **structlog** logging decision + eval/verifier metrics. |
| Pydantic v2 (contract spine) | `pydantic-v2` | the contract models — validation/serialization, **`model_dump(mode='json')` → JCS canonicalize before signing** (`model_dump_json` isn't canonical), `frozen`/`extra='forbid'`/`strict` hardening, the `pydantic.mypy` `disallow_any_explicit` gotcha. Homegrown (no official core-modeling skill). |
