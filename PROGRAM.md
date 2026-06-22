# Program State

Project state + handoff for humans, engineers, and AI agents. Read this before non-trivial work.
Keep it concise (see `CLAUDE.md`/`AGENTS.md` → **Program State**).

## Right Now

- **Phase 0 — Gate & scaffolding.** The repo skeleton ([`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md))
  and the frozen floor ([`DECISIONS.md`](./DECISIONS.md)) are in; the AI-operating layer lands with
  **E0-6 (#18)** (this file set). The **agent skill layer** is in: the **skills.sh lock + consumer `.agents/skills/`
  wiring** (PR #89 — `bun`/`turborepo`/`karpathy-guidelines` + the `assay-brain` recall skill, vendored and
  symlinked into `.claude/`+`.hermes/`; `assay-brain` built in `AssayInc/skills`, **#73**, closed),
  the **prefer-official cloud/IaC/training/eval/dev-loop packs** (**E0-10 (#85)**, landed — 25 skills:
  18 official-vendor (AWS / Terraform / OpenEnv / TRL / Python-UV / LocalStack + `skill-creator`), 3 Inspect AI
  (maintainer-authored, `meridianlabs-ai`), and 4 well-adopted community (`wshobson/agents` — TS/Python craft)),
  and the **five homegrown AssayOps domain skills** (**E0-11 (#86)**, landed — `write-isolated-verifier` /
  `reward-ledger-worm` / `deterministic-verification` / `red-team-exit-bar` / `eval-rigor`, authored in
  `AssayInc/skills` and vendored here). **E0-5 board (#22)** and **E0-9 assay-web rename (#81)** are done
  (verified + closed). **E0-3 LocalStack dev loop (#20)** **landed** (PR #95) — the `localstack-smoke` CI goes green once the
  `LOCALSTACK_AUTH_TOKEN` repo secret is set; LocalStack retired its free tokenless edition, so the loop runs
  **licensed** LocalStack (see [`DECISIONS.md`](./DECISIONS.md) / [`ISSUES.md`](./ISSUES.md)). **Phase-0
  scaffolding is complete; Phase-1 build has started.** The **T0 team gate (#25) closed** — the founder
  is the interim RL/eval owner and the hire is opened (`DECISIONS.md` §4 **R5** founder-backstop: Phases
  1–2 proceed now; Phase 3 stays hard-gated on the permanent owner). The build opens at the
  **contract-schema spine (E1)**, the join key for the whole system: **E1-1 (#26)** authors the four JSON
  Schemas (`reward-record` / `trajectory` / `diff-ir` / `task-spec`, Draft 2020-12) + a validation test
  (in review).

## Recently Landed

- **E0-4 (#21): repo hygiene.** `.github/CODEOWNERS` (global owner; the DECISIONS.md §8 enforcement arm —
  no speculative locked-grader rules, those land with #28/#56), `.github/pull_request_template.md`
  (documents the `Closes #` convention), and `CONTRIBUTING.md` (branch → focused PR → `bun run verify` →
  `/review` → merge-on-explicit-go; links the README Get started). **Secret scanning + push protection
  enabled** repo-side (the org has GitHub Advanced Security) — proven by a planted push-protection-supported
  secret (Stripe/SendGrid/Slack) **rejected on push** (`GH013`); `google_api_key` is detection-only, so it
  doesn't test push protection. Deferred (ISSUES.md): require-code-owner-review on the `main` ruleset (a
  single collaborator would deadlock solo PRs) + the per-path grader CODEOWNERS rules (#28/#56). (PR #108.)

- **E0-2 (#19): two-lane CI + branch protection.** `.github/workflows/ci.yml` runs the canonical
  `verify` gate (`turbo run typecheck lint test`) on every PR as two parallel, independently
  cache-keyed lanes that don't block each other — **`ts`** (bun/turbo, `--filter='!./py/**'`) and
  **`py`** (uv + turbo, `--filter='./py/**'`); the two filters partition all packages, so the union is
  exactly `bun run verify`. `permissions: contents: read`, no secrets/OIDC — **zero account-B creds**
  (DECISIONS.md §1/§8). Branch protection on `main` is **applied** — a repository ruleset requires the
  `ts` + `py` checks + a PR and blocks force-push/deletion. The **codegen-parity gate (#29)** is deferred —
  it's blocked-by #27/#28 and there's no `contracts/` schema yet (a parity check against nothing would be
  an empty verifier). (PR #101.)

- **E0-11 (#86): homegrown AssayOps domain skills.** Five brain-distilled skills authored in `AssayInc/skills`
  (each provenance-cited to a brain page/plan, `skill-creator`-authored, independently reviewed by Codex
  `gpt-5.5 xhigh` two-pass and A/B-evaluated) and vendored into the committed layer: `write-isolated-verifier`
  (the trust boundary), `reward-ledger-worm` (the WORM/KMS reward record), `deterministic-verification` (the
  diff-IR reward), `red-team-exit-bar` (the reward-channel red-team gate), `eval-rigor` (the
  eval-to-performance proof protocol). Each `SKILL.md` hash-pinned in `skills-lock.json`, symlinked into
  `.claude/`+`.hermes/`. Homegrown only where no official pack covers the AssayOps-specific need
  (`localstack-verifier` folded into the official `localstack/skills` pack instead). (PR #92, `330d340`.)

- **E0-10 (#85): prefer-official skill packs.** 25 skills vendored into the committed layer (18 official-vendor +
  3 maintainer-authored Inspect AI + 4 well-adopted community `wshobson/agents`), each mapped to a coding surface: `skill-creator` (anthropics); AWS `aws-cdk` / `aws-sdk-js-v3-usage` /
  `aws-cloudformation` / `aws-iam` (verifier read surface E2 + CDK adapter/drift E3/E11 + A/B role);
  `terraform-style-guide` / `terraform-test` (adapter-terraform E3); `openenv-cli` / `generate-openenv-env`
  (env-server E5, from canonical `huggingface/OpenEnv` — `meta-pytorch/openenv` now redirects there);
  `hf-cli` / `trl-training` (trainer E12); `uv` / `ruff` (Python lane); LocalStack `localstack` /
  `localstack-deploy` / `localstack-iam` / `localstack-state` / `localstack-logs` (dev loop E0-3, from
  `localstack/skills`); and Inspect AI `map-inspect-packages` / `reading-logs` / `babysitting-evals` (eval
  lane E13, from `meridianlabs-ai/inspect-skills` — Meridian Labs now maintain `inspect_ai`); and TS/Python craft
  `typescript-advanced-types` / `python-testing-patterns` / `python-type-safety` / `async-python-patterns`
  (well-adopted community `wshobson/agents`, where no official skill exists). Vendored verbatim (byte-identical to upstream), symlinked into
  `.claude/`+`.hermes/`, each `SKILL.md` hash-pinned in `skills-lock.json` (scripts/resources guarded by the
  `skills-sync-hygiene` rule, not the lock); the off-target majority of each multi-skill repo excluded
  (prefer-official, smallest-change). All six `CLAUDE.md` preflight domains now have a vendored skill. (PR #91.)

- **E0-6 (#18): AI-operating layer.** `CLAUDE.md` (the single auto-loaded constitution) + `AGENTS.md`
  symlink, `PROGRAM.md`, `ISSUES.md`, `tasks/{todo,lessons}.md`; the **`verify`-gate + locked-fixtures
  loop**, the "implement the next ready issue" trigger, and the quality bar — adapted to the polyglot,
  verification-infra domain. No `HANDOFF.md` (folded into `CLAUDE.md`); no `ci.yml` (that is E0-2/#19). (PR #84, `4d3fdf7`.)
- **E0-8 (#74): `DECISIONS.md`** — the frozen floor (trust model, locked decisions 1C–T3, I1–I11, the
  15-vector threat bar, eval rigor) ported from the `brain` plans so the repo stands alone. (PR #82.)
- **E0-1 (#17): bootstrap polyglot monorepo skeleton** — Bun + Turborepo TS lane (`ts/**`), UV Python
  lane (`py/**`), shared `typescript-config`/`biome-config`, `contracts/` shells, the `verify` task
  graph, committed lockfiles. (PR #83, `c871960`.)

## Handoff Notes

- **CI landed (E0-2, #19).** `.github/workflows/ci.yml` runs `bun run verify` per PR as two parallel,
  independently cache-keyed lanes (`ts` = bun/turbo, `py` = uv + turbo) that don't block each other,
  with zero account-B creds. Branch protection on `main` is **applied** — a repository ruleset requires
  the `ts` + `py` checks + a PR and blocks force-push/deletion (rulesets need the repo's paid GitHub plan;
  tracked in `ISSUES.md`). The **codegen-parity gate (#29)** is deferred (blocked-by #27/#28; no
  `contracts/` schema yet).
- **Brain sibling + skill layer.** Strategy/research/vision live in `../brain/` (`AssayInc/brain`);
  recall via the **`assay-brain`** skill, built in `AssayInc/skills` (**#73**, closed). As of PR #89
  it's **committed into this repo's skill layer** (`.agents/skills/assay-brain`, symlinked into
  `.claude/`+`.hermes/`, `SKILL.md` hash-pinned in `skills-lock.json`), so every agent here — Codex, CI, a fresh clone —
  gets it with zero setup. It also still ships as a **per-developer install** (`AssayInc/skills` →
  `./install.sh`, symlinked into `~/.claude/skills`) that makes recall work from *any* Assay repo; on a dev
  machine that global copy shadows the committed one (same content). Both resolve `../brain` with zero config
  and degrade gracefully when the brain is absent. The prefer-official cloud/IaC/training/eval packs landed
  in **#85** (PR #91 — 25 skills, each `SKILL.md` hash-pinned in `skills-lock.json`); the five homegrown
  domain skills are authored + vendored (**E0-11 / #86**). `CLAUDE.md` documents the layer as the design.
- **Read order for a new agent:** `CLAUDE.md`/`AGENTS.md` (operating layer) → `DECISIONS.md` (why/rules)
  → `docs/ARCHITECTURE.md` (how/where). The build spine is the `contracts/` schema (E1) — built first
  because it is the join key both lanes and a buying lab verify against.
