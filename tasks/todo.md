# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## E0-10 (#85) — assay-ops skills layer: the prefer-official cloud/IaC packs

**Goal:** finish #85 by adding the remaining **official** skill packs to the committed skills.sh layer
(lock + `.agents/skills/` → `.claude/`+`.hermes/` symlinks), then close it. The lock mechanism +
`assay-brain` already landed (PR #89). What's left: the cloud/IaC/training/Python/eval packs.

**Selection (21 skills; each maps to a coding surface — prefer-official, reviewed per-repo, not bulk-added):**
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

**Deliberately excluded:** the off-target majority of each multi-skill repo (AWS bedrock/amplify/
containers/serverless/billing/observability/messaging/secrets/swift/python-sdk; all TF provider-dev +
Packer + stacks; OpenEnv's own dev-workflow + HF-Spaces-deploy skills; LocalStack `localstack-extensions`);
`ty` (we use mypy, not ty).
**Scope note:** the user chose the *fuller* set, so `ruff` + `terraform-test` + `generate-openenv-env` are in.

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

### Hygiene — green
- [x] skill-creator (18 files, incl. executable `scripts/*`) + generate-openenv-env (17 files, incl.
      `assets/*.py` templates) **byte-identical to upstream** (git blob SHAs); all 21 `SKILL.md` verbatim.
- [x] All 21 `description` ≤ 1024 (max: hf-cli 1008). 3 AWS skills carry a benign upstream `version:`
      frontmatter key (Claude Code loads them fine — not edited, would break byte-identity + lock hash).
- [x] `.claude/skills/*` + `.hermes/skills/*` all mode-120000 symlinks → `../../.agents/skills/<name>`;
      executable scripts preserved at 100755.
- [x] `skills-lock.json`: 25 entries (4 prior + 21), each source + skillPath + computedHash; `npx skills list` resolves all.

### Gate + bookkeeping
- [x] `bun run verify` green — 6/6 tasks (typecheck/lint/test, both lanes), FULL TURBO.
- [x] `PROGRAM.md` + `ISSUES.md` + `CLAUDE.md` updated to landed state (before merge).
- [x] Focused PR #91 "Closes #85" (house style); `/review` run (Claude + Codex adversarial passes).

### Review

- **Done:** 21 skills added to the committed skills.sh layer for **#85** (18 from official vendor repos +
  3 maintainer-authored Inspect AI from `meridianlabs-ai`), each mapped to an AssayOps coding surface
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
- **Scope:** the six homegrown AssayOps domain skills remain **#86**; `assay-brain` (#73) already closed.
