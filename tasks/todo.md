# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## E0-10 (#85) — assay-ops skills layer: the prefer-official cloud/IaC packs

**Goal:** finish #85 by adding the remaining **official** skill packs to the committed skills.sh layer
(lock + `.agents/skills/` → `.claude/`+`.hermes/` symlinks), then close it. The lock mechanism +
`assay-brain` already landed (PR #89). What's left: the cloud/IaC/training/Python packs.

**Selection (10 skills; each maps to a coding surface — prefer-official, reviewed per-repo, not bulk-added):**
- `skill-creator` ← `anthropics/skills` — author homegrown skills (#86)
- `aws-cdk`, `aws-sdk-js-v3-usage`, `aws-cloudformation`, `aws-iam` ← `aws/agent-toolkit-for-aws`
  (verifier E2 reads state via SDK-v3 + CFN; CDK adapter E3/T3 + drift tasks E11; A/B read-only role)
- `terraform-style-guide` ← `hashicorp/agent-skills` — adapter-terraform E3/T2 + fixtures
- `openenv-cli` ← `huggingface/OpenEnv` — env-server conformance E5 (canonical repo; `meta-pytorch/openenv` redirects here)
- `hf-cli`, `trl-training` ← `huggingface/skills` — trainer E12 (TRL+LoRA) + HF Hub model/checkpoint mgmt
- `uv` ← `astral-sh/claude-code-plugins` — the `py/` UV workspace (official astral)

**Deliberately excluded:** the off-target majority of each multi-skill repo (AWS bedrock/amplify/
containers/serverless/billing/observability/messaging/secrets/swift/python-sdk; all TF provider-dev +
Packer + stacks; OpenEnv's own dev-workflow + HF-Spaces-deploy skills); `ty` (we use mypy), `ruff`
(mirrors vendoring no biome skill on the TS side), `terraform-test`/`generate-openenv-env` (niche).
**Gap flagged:** Inspect AI (E13) has no eval-authoring skill on the registry → official docs per CLAUDE.md preflight.

### Build (branch `feat/skills-official-packs`) — done
- [x] Installed each pack with **default agent targeting** (never `-a '*'`); `git status` after each →
      only `.agents/`, `.claude/`, `.hermes/`, `skills-lock.json` changed; **zero stray dotdirs**.
- [x] `anthropics/skills@skill-creator`
- [x] `aws/agent-toolkit-for-aws` → aws-cdk, aws-sdk-js-v3-usage, aws-cloudformation, aws-iam
- [x] `hashicorp/agent-skills` → terraform-style-guide, terraform-test
- [x] `huggingface/OpenEnv` → openenv-cli, generate-openenv-env (canonical repo; `meta-pytorch/openenv` redirects here)
- [x] `huggingface/skills` → hf-cli, trl-training
- [x] `astral-sh/claude-code-plugins` → uv, ruff

### Hygiene — green
- [x] skill-creator (18 files, incl. executable `scripts/*`) + generate-openenv-env (17 files, incl.
      `assets/*.py` templates) **byte-identical to upstream** (git blob SHAs); all 13 `SKILL.md` verbatim.
- [x] All 13 `description` ≤ 1024 (max: hf-cli 1008). 3 AWS skills carry a benign upstream `version:`
      frontmatter key (Claude Code loads them fine — not edited, would break byte-identity + lock hash).
- [x] `.claude/skills/*` + `.hermes/skills/*` all mode-120000 symlinks → `../../.agents/skills/<name>`;
      executable scripts preserved at 100755.
- [x] `skills-lock.json`: 17 entries (4 prior + 13), each source + skillPath + computedHash; `npx skills list` resolves all 17.

### Gate + bookkeeping
- [x] `bun run verify` green — 6/6 tasks (typecheck/lint/test, both lanes), FULL TURBO.
- [x] `PROGRAM.md` + `ISSUES.md` + `CLAUDE.md` updated to landed state (before merge).
- [ ] Focused PR "Closes #85" (house style); run `/review`.

### Review

- **Done:** 13 official, prefer-official skills added to the committed skills.sh layer for **#85**, each
  mapped to an AssayOps coding surface (verifier/adapters/env-server/trainer/Python lane). Lock + 3-dir
  symlink layout (`.agents/skills` → `.claude/`+`.hermes/`) preserved; `bun run verify` green.
- **Method/traps avoided:** every multi-skill repo (AWS 43, HashiCorp 16, OpenEnv 16, HF 19) was previewed
  with `--list` and only on-target skills vendored — **not bulk-added**. Default agent targeting throughout
  (never `-a '*'`), `git status` clean after each add (the [[skills-add-default-agent-targeting]] trap).
  Byte-identity verified for all resources incl. executable scripts ([[skills-sync-hygiene]]).
- **Two corrections from the user's review:** (1) `meta-pytorch/openenv` redirects to canonical
  `huggingface/OpenEnv` — declared the latter; (2) the OpenEnv `.agents/skills` curated set is
  `openenv-cli`+`hf-cli`, not the 16 a broad scan surfaces.
- **Gap flagged (not papered over):** Inspect AI (E13) has **no** official eval-authoring skill on the
  registry (the 4 `ukgovernmentbeis/inspect_ai` SKILL.md files are `examples/`+`tests/` sandbox utilities) →
  eval lane uses official Inspect AI docs per the `CLAUDE.md` preflight rule. Recorded in `ISSUES.md`.
- **Scope:** the six homegrown AssayOps domain skills remain **#86**; `assay-brain` (#73) already closed.
