# Lessons

Shared, committed memory for all agents working in this repo (see **Self-improvement loop** in
`CLAUDE.md`/`AGENTS.md`). After ANY correction from the user, append a lesson written as a rule that
prevents the same mistake. Review at session start; prune entries that stop being true.

Entry format:

```markdown
## YYYY-MM-DD — short-kebab-slug
- **Mistake:** what went wrong
- **Rule:** the rule that prevents it next time
- **Context:** files/commands involved (optional)
```

---

## 2026-06-18 — claude-md-serves-all-agents-no-dedupe
- **Mistake:** Trimmed the gstack skill list + routing out of `CLAUDE.md`, reasoning it duplicated
  `~/.claude/CLAUDE.md` and was context bloat.
- **Rule:** Never dedupe the project `CLAUDE.md`/`AGENTS.md` against Claude-only global config or plugin
  skills. `AGENTS.md` is read by non-Claude agents (Codex) that never load `~/.claude/CLAUDE.md`, so
  anything every agent needs — the full gstack skill list + routing, the `/browse`-only rule, operating
  rules — must live in this repo's file. Default to **completeness** for cross-agent content; only omit
  what is genuinely irrelevant to this repo (UI, machine-local gbrain config).
- **Context:** E0-6 (#18) `CLAUDE.md`; the user caught the missing gstack section. The committed skill
  *layer* (skills.sh / `skills-lock.json`) is separate and prefer-official (#85/#86) — that's not what was
  missing; the per-developer gstack workflow layer was.

---

### Durable lessons seeded at bootstrap

The lessons below were seeded at bootstrap (not yet earned from a correction here) — general doc-hygiene,
operating-layer, strict-TS, and debugging rules that apply to this repo. Prune any that stop being true.

## 2026-06-18 — reference-both-constitution-names
- **Mistake:** Shared docs referenced sections "in `CLAUDE.md`" only.
- **Rule:** When a shared/committed file points at the constitution, write `CLAUDE.md`/`AGENTS.md` — Codex
  knows it only as `AGENTS.md`. This repo is multi-agent; never write docs as if Claude is the only reader.
- **Context:** Pairs with [[claude-md-serves-all-agents-no-dedupe]] above.

## 2026-06-18 — committed-docs-are-standalone
- **Mistake:** Wrote "Option A / Option B" and chat rationale ("as we discussed", "I'd lean") into a
  committed runbook — framing that only meant something inside the chat that produced it.
- **Rule:** Committed docs (`DECISIONS.md`, `docs/`, `CLAUDE.md`, runbooks) are standalone — the reader
  has no conversation context. State the decision and the steps; cut option-menus, hedging, and
  already-rejected alternatives. Once a choice is made, write it as the practice, not a comparison.
- **Context:** Applies to all of assay-ops's committed docs (`DECISIONS.md`, `docs/`, runbooks).

## 2026-06-18 — reference-implementations-are-light-insight
- **Mistake:** Turned a reference repo's patterns into prescriptive "borrow / avoid" guidance in a
  committed doc.
- **Rule:** Analog products and reference implementations (RL-env companies, leaderboards, repos under
  `../brain`) are **light insight only** — they may not follow current official docs. Build from the
  **official skills/docs + `DECISIONS.md`** as the source of truth (prefer-official, #85); cite an analog
  only as "one possible shape, verify against official docs." Don't encode their patterns as rules.
- **Context:** Reinforces the prefer-official skill layer (#85/#86).

## 2026-06-18 — no-social-links-in-agent-docs
- **Mistake:** Cited an X/Twitter post as a markdown link in the constitution.
- **Rule:** Agent-facing docs (`CLAUDE.md`/`AGENTS.md`, `DECISIONS.md`, `tasks/`) don't carry login-walled
  or rot-prone external links (X, LinkedIn, etc.) — agents can't resolve them and they decay. Name the
  source in plain text; keep the real citation in the vendored artifact (skill, brain page) it attributes.
- **Context:** Why `CLAUDE.md` attributes the Karpathy guidelines in plain text, not a link.

## 2026-06-18 — gh-cli-first-for-pr-workflow
- **Mistake:** Reached for the GitHub connector/MCP for PR work even though the repo's working path is
  `gh`; got a 404 and an avoidable fallback step.
- **Rule:** For PR creation, inspection, check-watching, and body edits, use the **`gh` CLI** as the
  primary tool. Try connector/MCP GitHub tools only when a task explicitly asks or `gh` is unavailable.
- **Context:** Issues + PRs are gh-driveable.

## 2026-06-18 — contextual-typing-over-array-assertions
- **Mistake:** Refactored inline empty literals into a factory whose inferred return type dropped the
  value-type context, forcing `[] as T[]` — a bare assertion where none was needed.
- **Rule:** An empty collection literal gets its element type from an explicit annotation on its container
  (a `Map` value type, a variable type, or a function's declared return type), never an `as T[]`
  assertion. A factory with an inferred return type loses that context — annotate its return or keep the
  literal inline. Assertions belong only at I/O boundaries behind a runtime check (`CLAUDE.md` → Toolchain).
- **Context:** Strict-TS, never-`any` repo (`CLAUDE.md` → Toolchain).

## 2026-06-18 — update-program-state-before-landing
- **Mistake:** Merged a PR while `PROGRAM.md` still described the branch as an open follow-up, leaving the
  handoff stale immediately after landing.
- **Rule:** Before merging a state-changing PR, update `PROGRAM.md` **in the branch** — remove the landing
  `Right Now` entry and add the final `Recently Landed` entry with the PR number + merge commit. Don't
  rely on a main-only cleanup after merge.
- **Context:** The task loop's "update `PROGRAM.md` in the same PR" step.

## 2026-06-18 — skills-sync-hygiene
- **Mistake:** A skills.sh upstream sync silently dropped security-relevant excludes/validation from a
  vendored skill's `resources/*`; the lock file hashes only `SKILL.md`, so nothing flagged it.
- **Rule:** After any **skills.sh** install or sync (the committed skill layer arriving in #85/#86),
  `git diff` the skill's `resources/*` — especially executable scripts — before committing. Treat reduced
  excludes or validation in vendored scripts as a regression to restore and report upstream, never a
  neutral update.
- **Context:** Directly relevant to the incoming skill layer (E0-10/E0-11, #85/#86).

## 2026-06-18 — held-out-data-residency-includes-derived-uses
- **Mistake:** Sensitive ground-truth values get copied into in-repo tests/docs/PR bodies, reasoned as
  "precedent" — then need a git history rewrite to scrub.
- **Rule:** The residency rule for **gold trajectories + held-out eval** (private, never committed —
  `DECISIONS.md` I11; contamination control + the moat) covers **every in-repo surface** — tests, docs,
  comments, commit messages, PR bodies — and **derived values** that reconstruct held-out content. In-repo
  tests use synthetic fixtures; real/held-out data stays in the private store. Scrub **before** the first
  push — a history rewrite after publication is damage control, not prevention.
- **Context:** The data-hygiene expression of the §6 contamination check.

## 2026-06-18 — diagnose-unfamiliar-api-errors-before-theorizing
- **Mistake:** An unfamiliar vendor error string (e.g. a `400`) gets read literally, a wrong cause
  theorized, and the user sent on an external errand — when a differential probe would have located the
  real failure layer.
- **Rule:** Before theorizing from an unfamiliar API/cloud error string — and **especially** before
  sending the user on an external errand based on it — run a **differential diagnostic** (vary
  headers/inputs/permissions/region, compare responses) to locate the real failure layer. Don't
  over-interpret an error's literal text; confirm the mechanism with evidence.
- **Context:** AssayOps touches AWS / Cloud Control / LocalStack / OpenEnv across an account boundary —
  many unfamiliar error surfaces, and the verifier reads B-side state.

## 2026-06-18 — nested-workspace-claude-md-stays-minimal
- **Mistake:** A per-workspace `CLAUDE.md` restated root facts and narrated harness merge behavior.
- **Rule:** If a nested workspace `CLAUDE.md`/`AGENTS.md` is ever added (e.g. under `ts/`, `py/`, or a
  package), it carries **only** workspace-specific, non-inferable guidance. Never narrate harness behavior
  (Claude Code merges cwd→root; Codex merges `AGENTS.md` up-tree) and never restate cross-cutting facts
  that live in root — those belong in root's Architecture/Toolchain, stated once.
- **Context:** AssayOps is polyglot (`ts/` + `py/`) — nested constitutions are plausible; keep them minimal.
