# Issues

Durable open problems and external follow-ups — the kind that outlive a single PR. Day-to-day work is
tracked in **GitHub Issues + Projects v2** ([`DECISIONS.md` I4](./DECISIONS.md#4-implementation-decisions-i1i11));
this file is for cross-cutting context a GitHub issue doesn't capture.

## Open Follow-Ups

- **E17 Python-first rebaseline (#113) — decision PR landed; migration follow-ups open.** The
  proof-critical core is rebaselined TypeScript → **Python** (verifier, diff/reward, adapters, ledger,
  replay, env-server, orchestration → `py/packages/*`); TS stays for the public/web/tooling surface. The
  decision PR changed the **floor only** (`DECISIONS.md` I1–I7 + §8 + the §1 diagram labels,
  `docs/ARCHITECTURE.md` package map + episode flow, `CLAUDE.md` top-line + the skill-preflight AWS-read
  row) and **preserved the trust floor untouched**; the **OpenEnv reward-boundary invariant is locked
  non-waivable** (§8). **E2–E7 (#3–#8) are re-scoped to Python and blocked on the decision + the
  scheduled feasibility spikes** (OpenEnv/TRL spike, ledger spike; verifier-read = #80, re-scoped to
  boto3). **Open migration follow-ups** (no proof-critical code moved — it is unbuilt): (1) **re-home the
  built TS** — `@assayops/logger` (retire vs keep) + a Python structured-logging story, and a **boto3
  counterpart** to the `infra-local` LocalStack smoke; (2) **brain/wiki sync** — the raw plans
  (`assayops-implementation-plan-2026-06-17`, `assay-eng-architecture-2026-06-17`) + wiki pages still
  describe the TS-IP split; (3) **vendor a boto3 / Cloud-Control skill** and finish the
  `CLAUDE.md`/skill-layer language flip beyond the top-line + AWS row.
- **LocalStack auth token + plan tier (E0-3 / #20).** The free tokenless community edition was retired in
  the 2026-03-23 single-image change; the `infra-local` dev loop + the smoke CI run the licensed **LocalStack
  for AWS** image with `LOCALSTACK_AUTH_TOKEN` (a secret, never committed — local `.env` + a CI repo secret,
  both set; the smoke CI is green). **Current tier: free Hobby** (non-commercial, includes CI) — covers the
  R&D stage; **revisit** at higher load or production / clearly-commercial use (move to a paid plan, Base+).
  Staying on LocalStack (vs moto/Floci/MiniStack, which empirically don't serve Cloud Control `GetResource`)
  + the substrate qualifier are in #20 + DECISIONS.md; the broader secret-management decision is spike #96.

- **CI + branch protection landed; the parity gate is the open tail of E0-2 (#19).** The two-lane
  `ci.yml` (turbo + uv, independent cache-keyed lanes, zero account-B creds) runs `bun run verify` on
  every PR. **Branch protection on `main` is applied** — a repository ruleset requires the `ts` + `py`
  checks + a PR and blocks force-push/deletion. **Plan dependency:** rulesets / branch protection are
  gated behind a paid GitHub plan (Pro/Team) on private repos — keep the repo on that plan or the
  ruleset can't be edited/re-created. The **codegen-parity gate (#29)** is deferred to its own issue
  (blocked-by #27/#28; the schemas exist (E1-1) but codegen + golden vectors don't yet), and the
  **`fixture-change` guard** (a CI
  path+label check or a CODEOWNERS rule on the ruleset) activates when `contracts/vectors` (#28) /
  `tools/red-team` (#56) land.
- **Secret scanning + CODEOWNERS deferrals (E0-4 / #21, PR #108).** Secret scanning + push protection are
  **enabled** repo-side (GitHub-native; the org has Advanced Security) — proven by a planted
  push-protection-supported secret rejected on push (`google_api_key` is detection-only, so it doesn't test
  push protection). `.github/CODEOWNERS` (global owner), the PR template (documents `Closes #`), and
  `CONTRIBUTING.md` ship in PR #108. Two deferrals: (1) **require-code-owner-review is not wired into the
  `main` ruleset** — a single collaborator would deadlock every solo PR (no one else can approve); enable it
  with a second reviewer. (2) The **per-path CODEOWNERS rules for the locked grader** (`contracts/vectors`
  #28 / `tools/red-team` #56) land in those epics' `fixture-change` PRs — the dirs don't exist yet (see
  below). Together these complete the `fixture-change` guard noted above.
- **The committed skill layer — #85 + #86 landed.** The skills.sh lock + consumer `.agents/skills/`
  wiring (PR #89) and the **prefer-official cloud/IaC/training/eval packs** (**E0-10 / #85**) are in: 25
  skills (18 official-vendor + 3 maintainer-authored Inspect AI + 4 well-adopted community `wshobson/agents`) — `skill-creator`, AWS `aws-cdk` / `aws-sdk-js-v3-usage` / `aws-cloudformation` / `aws-iam`,
  `terraform-style-guide` / `terraform-test`, `openenv-cli` / `generate-openenv-env` (canonical
  `huggingface/OpenEnv`; `meta-pytorch/openenv` redirects there), `hf-cli` / `trl-training`, `uv` / `ruff`,
  LocalStack `localstack` / `localstack-deploy` / `localstack-iam` / `localstack-state` / `localstack-logs`
  (dev loop E0-3, from `localstack/skills`), and Inspect AI `map-inspect-packages` / `reading-logs` / `babysitting-evals` (from
  `meridianlabs-ai/inspect-skills`, who now maintain `inspect_ai`), and TS/Python craft `typescript-advanced-types` /
  `python-testing-patterns` / `python-type-safety` / `async-python-patterns` (well-adopted community `wshobson/agents`) — vendored verbatim and symlinked into
  `.claude/`+`.hermes/`, each `SKILL.md` hash-pinned in `skills-lock.json`. Each maps to a coding surface; off-target skills
  in each multi-skill repo were excluded. All `CLAUDE.md` preflight domains (AWS / Terraform / OpenEnv /
  TRL / Inspect AI / LocalStack) now have a vendored skill. The five homegrown AssayOps domain skills
  (`write-isolated-verifier` / `reward-ledger-worm` / `deterministic-verification` / `red-team-exit-bar` /
  `eval-rigor`) are authored in `AssayInc/skills` and vendored here (**E0-11 / #86**); the **`assay-brain`**
  recall skill (**#73**) is closed.
  `CLAUDE.md` documents the layer (prefer-official; author homegrown only for gaps). Recall also works from
  any repo via the per-developer `assay-brain` install (or `../brain/wiki` via `qmd` / the brain-side `wiki-query`).
- **Skill-lock coverage is `SKILL.md`-only (fast-follow).** `skills-lock.json` hash-pins each vendored
  `SKILL.md` but **not** its `resources/`/`scripts/` (e.g. skill-creator's executable `scripts/*.py`). A
  future `npx skills` sync could alter a script without changing the lock — the [[skills-sync-hygiene]] rule
  (manual `git diff` of the full vendored skill dir — all non-`SKILL.md` files, especially executable `scripts/*` —
  after any sync) is the current guard. A full-dir hash check in CI is a **fast-follow on top of the
  two-lane gate** (out of E0-2's ACs); the lock today is restore-grade, not part of `bun run verify`.
- **Locked-fixtures directories don't exist yet.** `contracts/vectors` (#28, E1-3) and `tools/red-team`
  (#56, E10-1) are scaffolded by their owning epics; the locked-fixtures rule in
  `CLAUDE.md`/`DECISIONS.md` binds the moment they do. Listed so the rule isn't mistaken for stale config
  pointing at nothing — no action until those epics run.
