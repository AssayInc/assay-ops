# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## E0-10 (#85) — assay-ops skills layer: the prefer-official cloud/IaC packs — DONE (PR #91)

**Goal (met):** added the **official** skill packs to the committed skills.sh layer (lock +
`.agents/skills/` → `.claude/`+`.hermes/` symlinks) and closed #85. The lock mechanism + `assay-brain`
landed in PR #89; the prefer-official packs in PR #91. Follow-on: the five homegrown domain skills are now
vendored too (E0-11 / #86, PR #92).

**Selection (25 skills; each maps to a coding surface — prefer-official, reviewed per-repo, not bulk-added):**
- `skill-creator` ← `anthropics/skills` — author homegrown skills (#86)
- `aws-cdk`, `aws-sdk-js-v3-usage`, `aws-cloudformation`, `aws-iam` ← `aws/agent-toolkit-for-aws`
  (verifier E2 reads state via SDK-v3 + CFN; CDK adapter E3/T3 + drift tasks E11; A/B read-only role)
- `terraform-style-guide`, `terraform-test` ← `hashicorp/agent-skills` — adapter-terraform E3/T2 + fixtures
- `openenv-cli`, `generate-openenv-env` ← `huggingface/OpenEnv` — env-server conformance E5 (canonical repo; `meta-pytorch/openenv` redirects here)
- `hf-cli`, `trl-training` ← `huggingface/skills` — trainer E12 (TRL+LoRA) + HF Hub model/checkpoint mgmt
- `uv`, `ruff` ← `astral-sh/claude-code-plugins` — `py/` UV workspace + the ruff linter (official astral)
- `localstack`, `localstack-deploy`, `localstack-iam`, `localstack-state`, `localstack-logs` ← `localstack/skills`
  — LocalStack dev loop (E0-3/#20): container lifecycle, deploy CDK/TF (`cdklocal`/`tflocal`), IAM-policy testing, state snapshots (replay E6/T8), log debug
- `map-inspect-packages`, `reading-logs`, `babysitting-evals` ← `meridianlabs-ai/inspect-skills` — Inspect AI
  eval lane E13/T11 (Meridian Labs now maintains `inspect_ai`; `map-inspect-packages` also routes Harbor = orchestrator E7)
- `typescript-advanced-types`, `python-testing-patterns`, `python-type-safety`, `async-python-patterns` ← `wshobson/agents`
  — well-adopted **community** TS/Python craft (no official skill exists): strict TS types, pytest, mypy/typing, asyncio

**Deliberately excluded:** the off-target majority of each multi-skill repo (AWS bedrock/amplify/
containers/serverless/billing/observability/messaging/secrets/swift/python-sdk; all TF provider-dev +
Packer + stacks; OpenEnv's own dev-workflow + HF-Spaces-deploy skills; LocalStack `localstack-extensions`);
`ty` (we use mypy, not ty); from `wshobson/agents` only on-target TS/Python craft (skipped uv-package-manager
[dup astral], python-code-style/design-patterns [ruff/CLAUDE.md cover; design-patterns risks classes], js-testing/nodejs-backend [bun, not jest/Node]).
**Scope note:** the user chose the *fuller* set (incl. `ruff` + `terraform-test` + `generate-openenv-env`) and OK'd
well-adopted **community** skills where no official exists (`wshobson/agents`) — a policy now in `CLAUDE.md`.

### Build (branch `feat/skills-official-packs`) — done
- [x] Installed each pack with **default agent targeting** (never `-a '*'`); `git status` after each →
      only `.agents/`, `.claude/`, `.hermes/`, `skills-lock.json` changed; **zero stray dotdirs**.
- [x] `anthropics/skills` → skill-creator
- [x] `aws/agent-toolkit-for-aws` → aws-cdk, aws-sdk-js-v3-usage, aws-cloudformation, aws-iam
- [x] `hashicorp/agent-skills` → terraform-style-guide, terraform-test
- [x] `huggingface/OpenEnv` → openenv-cli, generate-openenv-env (canonical repo; `meta-pytorch/openenv` redirects here)
- [x] `huggingface/skills` → hf-cli, trl-training
- [x] `astral-sh/claude-code-plugins` → uv, ruff
- [x] `meridianlabs-ai/inspect-skills` → map-inspect-packages, reading-logs, babysitting-evals (added after /review)
- [x] `localstack/skills` → localstack, localstack-deploy, localstack-iam, localstack-state, localstack-logs (LocalStack dev loop; user-requested)
- [x] `wshobson/agents` → typescript-advanced-types, python-testing-patterns, python-type-safety, async-python-patterns (well-adopted community; inspected for conflicts vs locked style)

### Hygiene — green
- [x] skill-creator (18 files, incl. executable `scripts/*`) + generate-openenv-env (17 files, incl.
      `assets/*.py` templates) **byte-identical to upstream** (git blob SHAs); all 25 `SKILL.md` verbatim.
- [x] All 25 `description` ≤ 1024 (max: hf-cli 1008). 3 AWS skills carry a benign upstream `version:`
      frontmatter key (Claude Code loads them fine — not edited, would break byte-identity + lock hash).
- [x] `.claude/skills/*` + `.hermes/skills/*` all mode-120000 symlinks → `../../.agents/skills/<name>`;
      executable scripts preserved at 100755.
- [x] `skills-lock.json`: 29 entries (4 prior + 25), each source + skillPath + computedHash; `npx skills list` resolves all.

### Gate + bookkeeping
- [x] `bun run verify` green — 6/6 tasks (typecheck/lint/test, both lanes), FULL TURBO.
- [x] `PROGRAM.md` + `ISSUES.md` + `CLAUDE.md` updated to landed state (before merge).
- [x] Focused PR #91 "Closes #85" (house style); `/review` run (Claude + Codex adversarial passes).

### Review

- **Done:** 25 skills added to the committed skills.sh layer for **#85** (18 official-vendor + 3 maintainer-authored
  Inspect AI `meridianlabs-ai` + 4 well-adopted community `wshobson/agents`), each mapped to an AssayOps coding surface
  (verifier/adapters/env-server/trainer/Python lane/eval lane/dev loop). Lock +
  3-dir symlink layout (`.agents/skills` → `.claude/`+`.hermes/`) preserved; `bun run verify` green.
- **Method/traps avoided:** every multi-skill repo (AWS 43, HashiCorp 16, OpenEnv 16, HF 19) was previewed
  with `--list` and only on-target skills vendored — **not bulk-added**. Default agent targeting throughout
  (never `-a '*'`), `git status` clean after each add (the [[skills-add-default-agent-targeting]] trap).
  Byte-identity verified for all resources incl. executable scripts ([[skills-sync-hygiene]]).
- **Corrections caught in review:** (1) `meta-pytorch/openenv` redirects to canonical `huggingface/OpenEnv`
  — declared the latter; (2) OpenEnv's `.agents/skills` curated set is `openenv-cli`+`hf-cli`, not the 16 a
  broad scan surfaces; (3) **Inspect AI was NOT a true gap** — my first "no skill exists" call was wrong;
  `/review` (Claude subagent) caught it. `meridianlabs-ai/inspect-skills` (Meridian Labs, who now maintain
  `inspect_ai`) is the de-facto first-party Inspect AI skills repo → vendored the 3 skills for E13;
  (4) fixed a stale "10 skills / excluded ruff,terraform-test,generate-openenv-env" contradiction in this file.
- **Known limitation (fast-follow, noted in `ISSUES.md`):** `skills-lock.json` hashes only each `SKILL.md`,
  not `resources/`/`scripts/`; the [[skills-sync-hygiene]] manual `git diff` is the current guard; CI
  enforcement belongs to E0-2 (#19). The lock is restore-grade, not wired into `bun run verify`.
- **Scope:** the five homegrown AssayOps domain skills are now authored + vendored (**E0-11 / #86**);
  `assay-brain` (#73) already closed.
