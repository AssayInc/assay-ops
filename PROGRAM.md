# Program State

Project state + handoff for humans, engineers, and AI agents. Read this before non-trivial work.
Keep it concise (see `CLAUDE.md`/`AGENTS.md` → **Program State**).

## Right Now

- **Python-first core is LOCKED (E17 decision landed, PR #118; epic #113 stays open tracking the follow-ups).** The proof-critical core is **Python**
  (verifier, diff/reward core, IaC adapters, reward ledger, deterministic replay, the OpenEnv env-server,
  episode orchestration in **`py/packages/*`**); **TypeScript** is the public/web/tooling surface
  (`@assayops/contracts` binding, `assay-web`, dashboards, npm consumers). The **trust floor is preserved
  untouched** (§1 account split, §2 locked decisions, §5 15-vector bar, §6 eval rigor). The **OpenEnv
  reward-boundary invariant** is locked **non-waivable** (§8): the A-side env-server never computes the
  graded reward — the **verifier (T1) computes** `reward∈{0,1}`, the **reward ledger (T4) signs +
  WORM-writes** it, joined by `trajectory_id`; the trainer trains on **that**, never the env's `step()`.
- **E2–E7 (#3–#8) are re-scoped to Python and gated** on the feasibility spikes: **#114 (OpenEnv/TRL,
  gates E5) LANDED — GO on OpenEnv-native Python → E5/#6 unblocked** (PR #121, `b91da87`); **#115 (ledger
  rfc8785/KMS/Object-Lock, gates E4) LANDED — GO** (PR #122); **#80** (boto3 read coverage) + **account
  infra T7 (P1-BLOCKING)** + LocalStack remain — **no proof-critical code starts on stale TS assumptions**.
  The contracts spine continues, **reframed Python-signer↔TS-consumer**: **#28** (JCS + golden vectors)
  then **#29** (CI parity).
- **Type checker:** `mypy --strict` is the bridge; **`ty`** (Astral) is the committed target, adopted at
  E2's first step once it is Stable + Pydantic-clean (**#119**). **Other tooling follow-ups:** #116
  (re-home built TS `@assayops/logger` + LocalStack smoke + boto3 skill), #117 (brain/wiki sync).
- **Next ready work:** **#28** (contract-spine JCS canonicalization + golden vectors) + **#80** (boto3 read
  coverage) — the remaining gates for E2–E7 (**#114** + **#115** spikes both landed GO; **E5/#6** unblocked
  by the #114 GO; **E4/#5** inputs surfaced by the #115 GO). **T0 team gate (#25) closed** (founder interim
  RL/eval owner; Phase 3 hard-gated on the permanent owner).

## Recently Landed

- **E17-S2 (#115): reward-ledger primitives feasibility spike (PR #122).** A runnable proof that the four
  reward-ledger primitives are real in the Python core, over the canonical `@assayops/contracts`
  `RewardRecord`: **RFC 8785 JCS** via `rfc8785` (byte-exact on the official vectors **and** byte-identical
  to the RFC 8785 reference JS `canonicalize` — the #29 parity shown), the **KMS `Sign`** call shape via
  boto3 (`MessageType=DIGEST`, ECDSA P-256 over JCS→SHA-256), **S3 Object Lock WORM** (Compliance +
  conditional write-once) via boto3, and portable **offline verify** on real `cryptography`. **GO** —
  confirms `DECISIONS.md` I3/4B/§8/T4 with no floor change. Lives in `py/packages/contracts/tests/` (imports
  the real `RewardRecord`; keeps signing/KMS/S3 out of the agent-reachable env-server). Cross-model
  `/review` (Claude + Codex `gpt-5.5` xhigh) caught a real fail-closed gap (`verify_offline` now pins P-256)
  + the Object-Lock checksum requirement; the KMS/S3 contract was verified against the **primary AWS docs**.
  **E4 builds the real account-B ledger** (real KMS validation + a bucket deny-policy; the agent holds no
  `kms:Sign`/`s3:BypassGovernanceRetention`). `bun run verify` green (16 spike tests).
- **E17-S1 (#114): OpenEnv-native Python env-server feasibility spike (PR #121, `b91da87`).** A minimal
  runnable OpenEnv-native Python `create_app`/FastAPI env-server (`py/packages/env-server`) proving four ACs
  against a real uvicorn server + WebSocket clients — concurrent-session isolation, terminal/delayed reward
  shape, the TRL OpenEnv drive seam, and the **non-waivable reward boundary** (the A-side env-server never
  computes the graded reward; account B grades **ground-truth** deployed state by `trajectory_id`, never the
  agent's observation). **GO — OpenEnv-native Python** (vs. a TS wire-only server). Grounded against the
  pinned source (`openenv[core]==0.3.1`, `trl==1.6.0`); cross-model `/review` (Claude + Codex `gpt-5.5`
  xhigh) caught + fixed a tautological boundary proof (now reads `cloud_state.CLOUD` independently). The
  account-B mock's primitives (sorted-key JSON, local ECDSA, in-memory WORM) are **stand-ins #115 makes real**
  (rfc8785 JCS · KMS Sign · S3 Object Lock · offline verify). `bun run verify` green.
- **E17 (#113): Python-first rebaseline — decision gate (PR #118).** Locked the **Python-first
  proof-critical core** (verifier / diff-reward / adapters / ledger / replay / OpenEnv env-server /
  orchestration → `py/packages/*`; TS kept for the public/web/tooling surface) with the **trust floor
  preserved untouched** (§1 account split, §2 locked decisions, §5 15-vector bar, §6 eval rigor). Locked
  the **OpenEnv reward-boundary invariant** non-waivable (§8): the A-side env-server never computes the
  graded reward — the verifier (T1) computes it, the reward ledger (T4) signs + WORM-writes it, joined by
  `trajectory_id`. Rewrote `DECISIONS.md` §4 I1–I7 + §8 + §1 diagram labels, `docs/ARCHITECTURE.md` package
  map + episode flow, `CLAUDE.md` + `README.md` framing + skill-preflight AWS-read→boto3; re-scoped epics
  #3–#8 + contracts #2/#28/#29 + #80; created follow-ups #114/#115 (blocking spikes) + #116/#117/#119.
  Cross-model `/review` (Claude + Codex `gpt-5.5` xhigh) caught the `README` front-line + the
  verifier-vs-ledger signing attribution; the type-checker gate was grounded against the official Astral
  docs (`ty` beta/0.0.x → `mypy --strict` bridge, `ty` the committed target, #119). **No proof-critical
  code moved** (unbuilt). (PR #118; the **#113 epic stays open** until #114/#115/#80/#116/#117/#119 close.)
- **E1-2 (#27): codegen wiring.** Root **`just codegen`** regenerates the committed contract types from
  `contracts/schemas/` — **quicktype** → `ts/packages/contracts/src/generated.ts` (interfaces) +
  **datamodel-code-generator** → `py/packages/contracts/src/assayops_contracts/models/` (Pydantic v2,
  `--use-annotated` for mypy-strict, modular package re-exported via a hand-written `__init__.py`). Both
  generators pinned (`bun.lock`/`uv.lock`) + fixed flags → **deterministic** (byte-identical re-gen; the
  #29 precondition). A cross-language **reward-record round-trip test** (TS serialize → Pydantic parse →
  Py serialize → semantic deep-equal) runs in the py lane via a tsc-checked emitter. Generated `any` (the
  open diff-IR/trajectory fields) excluded from Biome; generated `E501` excluded from ruff
  (`per-file-ignore`) — `tsc` / `mypy --strict` still typecheck both. A guarded post-process pins
  **`reward: 0|1`** into the TS type (quicktype can't emit a numeric literal union; the `DECISIONS.md` §8
  binary invariant — `reward: 2` is a tsc error); the Python `Reward` enum already encoded it. Cross-model
  `/review` (Claude + Codex `gpt-5.5 xhigh`) caught the orphan-module prune + the reward-type gap. JCS +
  golden vectors (#28), CI parity (#29) follow. (PR #112.)

- **E1-1 (#26): the 4 contract JSON Schemas.** `contracts/schemas/{reward-record,trajectory,diff-ir,task-spec}.schema.json`
  (Draft 2020-12, `additionalProperties:false`) as the neutral source of truth, + an ajv validation test in
  `ts/packages/contracts`. Modeling rules: ids / nonces / timestamps / seeds / digests = strings
  (ns-timestamps as canonical no-leading-zero digit strings); `reward` = `enum {0,1}` (binary, per
  `DECISIONS.md` §8 — **not** a continuous double); `tool` = `terraform | cdk`; `diff-ir`
  `modified ⟺ non-empty propertyDiffs`. `contracts/schemas/**` added to turbo `globalDependencies` (a schema
  change now busts the contracts-test cache). Two cross-model `/review` rounds (Claude + Codex `gpt-5.5
  xhigh`) caught the reward-binary frozen-floor deviation and the JCS leading-zero / empty-diff holes.
  Codegen (#27), JCS + golden vectors (#28), CI parity (#29) follow. (PR #109.)

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
  `aws-cloudformation` / `aws-iam` (verifier read surface E2 + CDK adapter/drift E3/E11 + A/B role; **E17
  supersedes:** the verifier read is now **boto3/Python**, `aws-sdk-js-v3-usage` → the TS consumer surface);
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
