# Issues

Durable open problems and external follow-ups — the kind that outlive a single PR. Day-to-day work is
tracked in **GitHub Issues + Projects v2** ([`DECISIONS.md` I4](./DECISIONS.md#4-implementation-decisions-i1i11));
this file is for cross-cutting context a GitHub issue doesn't capture.

## Open Follow-Ups

- **E3-4 (#80) boto3 read-coverage spike — GO (with conditions); recorded decision (no floor change).**
  Resolves the E17 #113 verifier-read spike. Grounded in AWS primary docs (fetched live) + `DECISIONS.md`
  §1/§5/§8 + brain; hardened by a cross-model `/review` (Claude adversarial + Codex `gpt-5.5` xhigh, PR #138):
  - **Read path split by tool:** **Terraform → Cloud Control `GetResource`/`ListResources` only**
    (provisioning-agnostic; no provider plugins — the T1 constraint). **CFN drift / `DescribeStackResources`
    are CloudFormation-stack-scoped → the CDK adapter's (T3) path** (and drift alone is itself incomplete:
    `NOT_CHECKED`, uncomparable properties), N/A for Terraform (it creates no stack). Clarifies the AI-issue's
    bundling (flag, not code-around).
  - **Coverage (AC1):** authoritative = AWS "Resource types that support Cloud Control API" (~**1300** public
    types). Three distinct properties: **readable** (a `read` handler), **enumerable** (a `list` handler —
    differs per type), **property-covered** (`GetResource` omits write-only props). Common Terraform corpus
    well covered; gaps = **`IAM::Policy`** + **`Route53::RecordSet`/`RecordSetGroup`** (fallbacks:
    `ManagedPolicy` / `iam:List*Policies`; `route53:ListResourceRecordSets`); inline
    `RolePolicy`/`UserPolicy`/`GroupPolicy` are **Read-but-not-List** (readable, not enumerable). Exact matrix
    + IAM set regenerated via `cloudformation list-types --provisioning-type FULLY_MUTABLE|IMMUTABLE` +
    `describe-type` (`Schema.handlers` + `writeOnlyProperties`) — real-AWS, T7-gated; LocalStack
    non-authoritative.
  - **Unsupported/unreadable policy (AC2) = FAIL-CLOSED + CLOSED-WORLD** (never silently reward — §5 vector
    #15). Expected-resource unreadability: type/property uncovered → quarantine at authoring; transient (incl.
    read-after-create) → `7A` classifier; genuine → `reward=0`. **Extra/over-provisioned resources are the
    moat-critical half:** `list_resources` is per-`TypeName`/per-Region, so reads alone can't see an extra
    resource of an out-of-scope/non-listable type or in an unscanned Region → reward must be **deployed set ≡
    golden set**, enforced primarily by **T7 SCP create-allow-lists** (a closed set of CC-listable types +
    Regions makes an out-of-scope resource unreachable by construction) + **exhaustive, paginated,
    Region/global-service-aware, fail-closed** union-enumeration as defense-in-depth (a truncated/errored
    enumeration must never read as "no extra resources").
  - **Read-only IAM (AC3):** control-plane = **`cloudformation:GetResource` + `cloudformation:ListResources`**
    (Cloud Control's IAM service prefix is `cloudformation`, verified) with **`Resource:"*"`** (no ARN
    scoping); underneath, the union of in-scope types' **`handlers.read.permissions` ∪
    `handlers.list.permissions`** (least-privilege via `describe-type`; `ReadOnlyAccess` = Phase-1 bootstrap
    only). `kms:Decrypt`/`GetSecretValue` intentionally absent (reads config/metadata, not plaintext).
    Account-B verifier assumes (`sts:AssumeRole`) a read-only role in account A (SCP-protected from the agent;
    no A→B path; read-only). CDK/T3 adds `cloudformation:*StackDrift*` + `DescribeStackResource*`.
  - **Go/no-go (AC4) = GO (with conditions):** scope the Phase-1 **Terraform engine-validation** corpus to
    CC-readable types — conditional on (1) the closed-world predicate (T7 allow-lists + enumeration), (2) the
    per-asserted-property coverage gate, (3) the corrected IAM set. **Representativeness caveat (R2/§6):** the
    CC-readable screen must NOT silently shape the Phase-2 proof/OOD corpus (uncovered families get fallback
    adapters there, not exclusion).
  - **Recorded as tracked work (not just comments):** the findings are **landed in `DECISIONS.md` §1** as a
    resolved-`[spike]` note (founder-ratified, PR #138); the implementation conditions are **#141** (E2 —
    verifier-side read-coverage enforcement: FAIL-CLOSED + closed-world + per-property gate + coverage tooling +
    corrected read IAM, under epic #3) and the **closed-world create-allow-list is appended to #53** (E9-1,
    the T7 SCP issue). Informs **T2** (#35 Terraform adapter) + the read role (#52 / #33).

- **Python type-safety parity + its three hardening tails (#126, #128, #127) — all landed.** The Python
  lane now bans explicit `Any` (mypy `disallow_any_explicit` per source package + ruff `ANN401`), mirroring
  the TS `any` ban — `object` + a runtime narrow (Pydantic) is the `unknown` equivalent — with `S`/`LOG`/`G`/
  `ASYNC` ruff rules and `ruff format --check` gated, and **structlog** named as the Python logging lib (the
  pino analog; advances the #113 "Python structured-logging story"). **Tracked follow-ups (now GitHub issues,
  not orphaned):** **#126 (done — #129)** config-DRY — the shared **ruff** config is hoisted to a root `[tool.ruff]` + `extend`
  in each member; **mypy/pytest stay per-package by design** (mypy has no config-merge, and the two packages
  run divergent `disallow_any_explicit` strategies — contracts global incl. `scripts/`, env-server scoped so
  its OpenEnv/TRL-mock tests keep `Any` — so it is intentional divergence, not duplication). **#128 (done — AssayInc/skills#9, vendored)** the
  homegrown **Pydantic-v2 skill** (`AssayInc/skills`, grounded in official Pydantic docs — frozen/`extra=forbid`,
  deterministic `model_dump_json` → RFC 8785 JCS, `TypeAdapter`; Pydantic is the contract spine and has no
  official skill). **#127 (done — all 4 vendored)** the 4 **wshobson Python skills** (resilience /
  error-handling / configuration / observability) — founder elected to vendor all four now (cheap; community
  skills auto-load by relevance), overriding the epic-gating, each mapped to its surface in the CLAUDE.md
  preflight. The official
  **FastAPI** skill is **not** vendored — AssayOps never hand-writes FastAPI (OpenEnv's `create_app` owns the
  routes), so it is YAGNI (founder call).

- **Reward-ledger primitives spike (#115) — GO; E4 (#5) inputs surfaced.** The E17-S2 feasibility spike
  (`py/packages/contracts/tests/ledger_spike.py` + `test_ledger_primitives_spike.py`) recorded **GO**: the
  four primitives are real in the Python core over the canonical `RewardRecord` — RFC 8785 JCS via `rfc8785`
  (byte-exact on the official vectors **and** byte-identical to the RFC 8785 reference JS `canonicalize`, the
  #29 parity shown), the KMS `Sign` call shape via boto3 (`MessageType=DIGEST`, ECDSA P-256 over JCS→SHA-256),
  S3 Object Lock WORM (Compliance + conditional write-once) via boto3, and portable **offline** verify on real
  `cryptography` (confirms `DECISIONS.md` I3 / 4B / §8 / T4, no floor change). **E4 follow-ups the spike
  flagged:** (1) **moto's KMS crypto is non-functional** — a moto `Sign` doesn't verify against its own
  `GetPublicKey`, so E4 must validate offline-verify against **real KMS** (the recipe is proven real on
  `cryptography`); (2) **Object Lock is version-scoped** — the locked version is immutable and survives a new
  PUT or a simple-delete marker, but key-level write-once needs `(key, versionId)` pinning **+ an E4 bucket
  policy denying unconditioned PUT/DELETE + `BypassGovernanceRetention`** (the agent holds none of those, nor
  `kms:Sign`); (3) the **real account-B `reward-ledger` package + the KMS key/bucket IAM policies** are E4's
  build; (4) the production `canonicalize` (both sides) + the locked golden-vector corpus
  (`contracts/vectors`) **landed in #28**; the CI byte-parity / regenerate-and-diff gate is **#29** — the
  spike used the official RFC 8785 vectors as a test fixture, distinct from `contracts/vectors`. Spike deps
  (`rfc8785`/`boto3`/`moto`, `canonicalize`) live in the workspace dev group / ts-contracts devDep
  (`rfc8785` is now also a runtime dep of `assayops-contracts`), kept out of the agent-reachable env-server.
- **OpenEnv env-server spike (#114) — GO; E5 (#6) inputs surfaced.** The E17-S1 feasibility spike
  (`py/packages/env-server`) recorded **GO on OpenEnv-native Python** (vs. a TS wire-only server): a
  runnable `create_app`/FastAPI env proves concurrent-session isolation over HTTP + `/ws`, the
  delayed/terminal reward shape, and the TRL drive — with the **reward boundary held** via the
  trl-1.6.0 `rollout_func`→`reward_funcs` seam joined by `trajectory_id` (confirms `DECISIONS.md` I5 +
  §8, no floor change). **E5 follow-ups the spike flagged:** `openenv[core]` is a heavy ~100-dep install
  (web UI off by default — slim it in E5); openenv 0.3.1 ships no `py.typed` (mypy-strict needs
  `ignore_missing_imports` + a few subclass `# type: ignore[misc]` — vendor/contribute stubs); the
  **B-side was mocked** (real KMS asymmetric signing + RFC 8785 JCS (#28), S3 Object Lock (#115), an
  independently regenerated golden + cross-account boto3 read (#80) are the production pieces). The spike
  models the **independent read** via `cloud_state.CLOUD` and mints the join key **out-of-band**
  (`reset(episode_id=...)`), but `CLOUD` is a lossless **echo** — modeling deploy-vs-requested divergence
  is the real boto3 read's job (#80); the #124 cross-model review also flagged that `CLOUD` snapshots shallow-copy nested values (pre-existing, moot once the read is real cross-account boto3). Board nit: the `area:env-server` label still reads "OpenEnv **TS**
  env-server" (pre-E17 stale).
- **E17 Python-first rebaseline (#113) — decision PR landed; migration follow-ups open.** The
  proof-critical core is rebaselined TypeScript → **Python** (verifier, diff/reward, adapters, ledger,
  replay, env-server, orchestration → `py/packages/*`); TS stays for the public/web/tooling surface. The
  decision PR changed the **floor only** (`DECISIONS.md` I1–I7 + §8 + the §1 diagram labels,
  `docs/ARCHITECTURE.md` package map + episode flow, `CLAUDE.md` top-line + the skill-preflight AWS-read
  row) and **preserved the trust floor untouched**; the **OpenEnv reward-boundary invariant is locked
  non-waivable** (§8). **E2–E7 (#3–#8) are re-scoped to Python and gated on the feasibility spikes** —
  the **OpenEnv/TRL spike (#114) is delivered: GO on OpenEnv-native Python → E5 (#6) unblocked** and the
  **ledger spike (#115) is delivered: GO → E4 (#5) inputs surfaced** (both see above); **verifier-read
  (#80, boto3)** remains — now **grounded + unblocked by #116** (the boto3 skill + the read smoke). **Open
  migration follow-ups** (no proof-critical code moved — it is unbuilt): (1) **re-home the
  built TS** — the **`@assayops/logger` retire-vs-keep + the Python structured-logging story carved out
  to #132 and landed**: **KEEP** `@assayops/logger` (scoped to the TS consumer/web surface) and the new
  `py/packages/logger` (`assayops_logger`) is the structlog mirror for the proof-critical core (JSON→stdout,
  deny-by-key redaction, the boto3/uvicorn stdlib bridge, `trajectory_id` contextvars; the two lanes share
  the `SECRET_KEYS` contract, parity-tested). The Python censor matches **case-insensitively** (to catch
  botocore's capitalized `Authorization`/`X-Amz-Security-Token`); the TS consumer-surface lane stays
  case-sensitive — a low-priority future TS fixture-change only if it ever logs AWS-signed requests.
  **#116 landed (PR #134):** the prefer-official boto3 skill (`aws-sdk-python-usage`, first-party AWS) + the
  **`infra-local` smoke re-homed TS→boto3/Python** (the TS `smoke.test.ts` + `@aws-sdk` deps retired — the
  verifier reads via boto3 now; Cloud Control `get_resource`/`list_resources` + the `ResourceNotFoundException`
  negative path, botocore's own bounded retries; LocalStack does **not** serve `DetectStackDrift`, so
  drift-read coverage is #80/E2 on real AWS) + the CLAUDE.md language flip — **grounds + unblocks #80**; (2) **brain/wiki
  sync** — the raw plans (`assayops-implementation-plan-2026-06-17`, `assay-eng-architecture-2026-06-17`) +
  wiki pages still describe the TS-IP split; (3) **vendor a boto3 / Cloud-Control skill** + finish the
  `CLAUDE.md`/skill-layer language flip — **done in #116/PR #134** (`aws-sdk-python-usage` vendored; Toolchain
  reordered Python-first; the AWS preflight row names the skill).
- **LocalStack auth token + plan tier (E0-3 / #20).** The free tokenless community edition was retired in
  the 2026-03-23 single-image change; the `infra-local` dev loop + the smoke CI run the licensed **LocalStack
  for AWS** image with `LOCALSTACK_AUTH_TOKEN` (a secret, never committed — local `.env` + a CI repo secret,
  both set; the smoke CI is green). **Current tier: free Hobby** (non-commercial, includes CI) — covers the
  R&D stage; **revisit** at higher load or production / clearly-commercial use (move to a paid plan, Base+).
  Staying on LocalStack (vs moto/Floci/MiniStack, which empirically don't serve Cloud Control `GetResource`)
  + the substrate qualifier are in #20 + DECISIONS.md; the broader secret-management decision is spike #96.

- **CI + branch protection landed; the codegen-parity gate landed (#29 → E1 #2 complete).** The two-lane
  `ci.yml` (turbo + uv, independent cache-keyed lanes, zero account-B creds) runs `bun run verify` on
  every PR. **Branch protection on `main` is applied** — a repository ruleset requires the `ts` + `py`
  checks + a PR and blocks force-push/deletion. **Plan dependency:** rulesets / branch protection are
  gated behind a paid GitHub plan (Pro/Team) on private repos — keep the repo on that plan or the
  ruleset can't be edited/re-created. The **codegen-parity gate (#29, PR #139)** is **landed**: a dedicated
  **`codegen-parity` job** in `ci.yml` regenerates from `contracts/schemas` (`just codegen`) + `contracts/vectors`
  (`just vectors`) and fails on any diff vs the committed artifacts;
  byte-parity (AC2 — the golden-vector sha256, both lanes) was already asserted in `bun run verify` (#28), so
  #29 verified it rather than rebuilding. It is a **dedicated job** (spans both generators; regenerates into
  the tree, which the verify lanes must not do) added to the `main` ruleset as a **third required status
  check** (`ts` + `py` + `codegen-parity`) once the workflow is on `main` — GitHub's create-the-check-before-requiring
  order, since requiring it while open PR #138's branch lacks a `codegen-parity` run would block #138 on a
  never-reported check (#138 picks it up on its next main-sync). The
  #29 cross-model `/review` also **hardened `just codegen`** (quicktype now reads the whole
  `contracts/schemas/` dir via an `LC_ALL=C` glob — byte-identical to the prior explicit list — so a newly
  added schema reaches **both** generators and the gate can see its TS drift; it also fixes an opaque
  removed-schema crash). Residual codegen hardcoded-list nits (the TS ajv schema-test, the over-broad
  reward-pin) are tracked in **#140**; the `just` binary is now version-pinned (1.53.0) in both workflows. The
  **`fixture-change` guard** is **active for `contracts/vectors`** (its CODEOWNERS rule + the
  `fixture-change` label landed with #28); it extends to `tools/red-team` when #56 lands.
  **Canonicalization cross-language follow-ups (E3/#26 + E4), surfaced by the #28 `/review` (Claude +
  Codex xhigh).** The Python signer canonicalizes the **materialized** `model_dump` form; a TS consumer
  canonicalizes the **raw** object. They agree on the same materialized JSON (the corpus locks this), and
  the signed **`RewardRecord` is fully safe** (all 7 fields required — no optional/large-number exposure).
  Two residuals on the **not-yet-signed** `DiffIR`/`Trajectory`:
  - **Optional-field materialization (DiffIR).** The generated Pydantic model materializes an **omitted**
    optional field to `None` → `model_dump` emits `null`, while a TS consumer canonicalizing the raw object
    **omits the key** — a model_dump-vs-raw divergence on any sparse record. DiffIR has **three** optional
    surfaces (a Codex xhigh re-review corrected an earlier "lone field" misread): `Resource.propertyDiffs`
    (omitted → `"propertyDiffs":null`, **schema-invalid** — the schema requires an `array`) and
    `PropertyDiff.expected`/`actual` (the `anyOf` requires one side; the other → `null`, which **is**
    schema-valid). The signed **`RewardRecord` has no optional fields** (unaffected). **Root-cause fix
    (E3/#26/#27):** align model + schema (e.g. `propertyDiffs` non-optional, default `[]`), or have the
    canonical path drop omitted optionals (`exclude_none`) so the materialized form matches a sparse wire
    form. #28 keeps the corpus to **valid records** (the schema-invalid `propertyDiffs:null` vector was
    reverted) and **locks the schema-valid materialized parity, both sides** (`diff-ir/optional-property-sides`).
  - **Out-of-domain values.** Numbers must be IEEE-754-representable + strings valid Unicode; the signer
    (`rfc8785`) **fails closed**, a JS consumer rounds/escapes. **For E4:** the verify side must reject
    out-of-domain values, or verify over the stored payload bytes (never re-canonicalize a sparse object).
    #28 locks the fail-closed (`test_canonicalize_fails_closed_on_a_non_representable_number`).
- **Secret scanning + CODEOWNERS deferrals (E0-4 / #21, PR #108).** Secret scanning + push protection are
  **enabled** repo-side (GitHub-native; the org has Advanced Security) — proven by a planted
  push-protection-supported secret rejected on push (`google_api_key` is detection-only, so it doesn't test
  push protection). `.github/CODEOWNERS` (global owner), the PR template (documents `Closes #`), and
  `CONTRIBUTING.md` ship in PR #108. Two deferrals: (1) **require-code-owner-review is not wired into the
  `main` ruleset** — a single collaborator would deadlock every solo PR (no one else can approve); enable it
  with a second reviewer. (2) The **per-path CODEOWNERS rule for `contracts/vectors`** landed with **#28**
  (its `fixture-change` PR); the **`tools/red-team`** rule lands with **#56**. Together these complete the
  `fixture-change` guard noted above.
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
- **Locked-fixtures directories: `contracts/vectors` now exists (#28); `tools/red-team` not yet (#56).**
  `contracts/vectors` (the JCS golden corpus) landed with **E1-3 (#28)** — the locked-fixtures rule
  (`CLAUDE.md`/`DECISIONS.md` §8) **now binds it**, enforced by its CODEOWNERS rule + the `fixture-change`
  label. `tools/red-team` (#56, E10-1) is still scaffolded by its owning epic; the rule binds it the moment
  it lands.
