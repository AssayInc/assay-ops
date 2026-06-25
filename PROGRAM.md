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
  rfc8785/KMS/Object-Lock, gates E4) LANDED — GO** (PR #122); **#80 (boto3 read coverage, gates E2/E3) LANDED —
  GO (with conditions)** (Terraform read path = Cloud Control `GetResource`/`ListResources` only; unreadable =
  FAIL-CLOSED; detecting *extra* resources needs a **closed-world** predicate via **T7** SCP create-allow-lists —
  reads alone can't close vector #15); **account infra T7 (P1-BLOCKING — now also owns the closed-world
  allow-list)** + LocalStack remain — **no proof-critical code starts on stale TS assumptions**.
  The contracts spine (**E1 #2**) is **complete** (planned deliverables #26–#29 all landed),
  **reframed Python-signer↔TS-consumer**: **#28** (JCS + golden vectors) and **#29** (the CI
  regenerate-and-diff parity gate) landed; the review-surfaced codegen-hardening follow-up (**#140**)
  **landed** (PR #144).
- **Type checker:** `mypy --strict` is the bridge — now also **`disallow_any_explicit`** + ruff `ANN401` (the Python `Any` ban mirroring the TS `any` ban; `object` is the `unknown` equivalent); **`ty`** (Astral) is the committed target, adopted at
  E2's first step once it is Stable + Pydantic-clean (**#119**). **Other tooling follow-ups:** **#132
  (Python structlog logger — landed; carved from #116)**, **#116 (boto3 skill + LocalStack boto3 read smoke
  + language flip — landed, PR #134)**, #117 (brain/wiki sync).
- **Next ready work:** **E2 verifier core started** — the golden-target generator (**#75**,
  `py/packages/verifier`) landed (account-B-pure; needs no cloud substrate). Next E2: the deployed-state
  read path / skeleton (**#30**) + reward core (**#32**); **E3's diff-IR (#34) + Terraform adapter (#35) have landed** (the adapter in PR #150).
  Plus **account infra T7 (P1-BLOCKING)** — now also owns the #80-surfaced closed-world SCP
  create-allow-list (**#53**) — plus **#141** (E2 verifier-side read-coverage enforcement, from the #80 spike).
  With **E1's spine (#26–#29) complete** and the **#80 / #114 / #115 spikes all GO**, the gates for E2–E7 are
  cleared (**E5/#6** from the #114 GO; **E4/#5** inputs from the #115 GO; **E2/E3** inputs from the #80 GO); and
  the **E3 diff-ir core (#34) + Terraform adapter (#35) have landed** — the shared reward core + normalized
  IR + the deployed-state adapter, so the verifier core (E2/#3 — read path #30, reward wiring #32) is next.
  **T0 team gate (#25) closed** (founder interim RL/eval owner; Phase 3 hard-gated on the permanent owner).

## Recently Landed

- **#60 (spike): IAM eventual consistency — resolved (measured against real AWS).** A bounded engineer probe
  (new `py/packages/iam-readiness-probe`, fenced out of the `verify` gate like `infra-local` — a `probe`
  script, never `test`, since it mutates real AWS) measured propagation for a fresh `AWS::IAM::Role` (n=20,
  us-east-1): **Cloud Control read-after-create is effectively immediate** (p99 < 0.2s, zero variance) — the
  verifier read path (E2/T1) is largely insulated (cc_get p99 ~0.76s, 0 bound-exceeded), so its
  read-after-create 7A budget is small + FAIL-CLOSED — while **`AssumeRole`/use propagates at ~7s p50 with a
  tail to ~42s**, so the real delay is the **E8
  provision-then-use** path: gate first use of a fresh cross-account role behind a **bounded (~60s) FAIL-CLOSED
  readiness poll, isolated from the grade**. The "readiness gate" is a **calibration of the locked 7A transient
  budget**, not a new mechanism (reconciles with #80's read-after-create→7A + #141). The smoke caught a real
  bug pre-full-run (fresh STS creds are transiently `InvalidAccessKeyId` — folded into the `perm` horizon).
  Ratified note landed in `DECISIONS.md` §1; consumers updated (#45 the 7A classifier, #141 read-coverage,
  #52/#33 cross-account role assume). Probe is mypy-strict/ruff-clean (boto3 `BaseClient` boundary). Grounded
  in `deterministic-verification` (7A) + `aws-iam` + `aws-sdk-python-usage` + brain `retries-and-backoff`.
  `bun run verify` green 19/19. (PR #151.)
- **E3-2 (#35): `adapter-terraform` package — the Terraform deployed-state → diff-IR adapter (6A/T2, the
  A-spike engine).** New **`py/packages/adapter-terraform`** (`assayops_adapter_terraform`):
  `normalize(reads, registry)` turns already-enumerated **Cloud Control deployed-state reads** into the
  diff-ir `NormalizedState(DEPLOYED_READ)` (#34) the shared reward core grades against the golden (#75).
  **Pure** — no boto3, no `terraform`/provider/`.tfstate`/plan read (T1, the moat); the boto3 read +
  closed-world enumeration stay with the read harness (#30/#141/#53). **Address bridge (the one
  floor-unspecified call, founder-decided):** Cloud Control returns a physical id but the core diffs by
  logical `address`, so the deploy tags each resource with a reserved case-sensitive **`assayops:address`**
  tag, read from the schema tag property under a per-type **`BridgeRegistry`** (the codified #80 matrix; an
  unregistered type → fail closed). The untrusted tag value is validated as a logical address; only that tag
  is stripped (user tags kept, sorted); server-computed `readOnlyProperties` dropped; declared set properties
  sorted. **Fail-closed, never a silent reward** (vector #15): a missing/duplicate/malformed/case-wrong/
  reserved/wrong-shape tag, an unsupported or unreadable record, a duplicate address, a non-JSON property.
  **Stale-issue reconciliation (flagged on #35):** the body's `+ CFN drift` read path is dropped —
  DECISIONS.md §1 (#80) locks Terraform = Cloud Control only (no CFN stack ⇒ drift = the CDK/T3 path #66).
  **Empirical proof:** a new `infra-local` LocalStack smoke proves Cloud Control `GetResource` surfaces the
  `assayops:address` tag for `AWS::S3::Bucket` (the founder's per-type gate; **ran green on local LocalStack**
  + in CI; kept out of the hermetic gate as a `smoke` script). TDD: **41 hermetic tests** (all 4 ACs
  end-to-end through the real `grade` + every fail-closed case). **Cross-model `/review`** (Claude
  adversarial + correctness + Codex `gpt-5.5` xhigh, re-reviewed to convergence) hardened it: funnel any
  unexpected exception (a deep-nested `RecursionError`) into the fail-closed `AdapterError` family;
  case-insensitive reserved-`assayops:*` check; dropped the unused/`json.dumps`-divergent set-sort seam
  (real set normalization → #66, JCS-aligned). `bun run verify` green **26/26**; both lockfiles
  frozen-clean. Establishes the **corpus deploy-tagging convention** (#76/#67 must tag resources
  `assayops:address`; goldens must also declare server-defaulted posture, e.g. S3 encryption/BPA, for a
  real-cloud read) — tracked as **#155** (E11), with the reward-core empty-golden guard as **#154** (E2).
  (PR #150.)
- **E3-1 (#34): `diff-ir` package — the normalized IR + shared reward core (6A); the first E3 deliverable.**
  New `py/packages/diff-ir`: the tool-agnostic normalized-state IR (`NormalizedResource`/`NormalizedState` —
  the adapter↔core interface) + the **shared, write-isolated reward core** `grade(deployed, golden) ->
  GradeOutcome(reward, diff)`. `grade` is the **only** public reward entry, so its consumption is exactly
  {B-side deployed-state read, regenerated golden target} (AC2): it **fails closed** (`UntrustedInputError`)
  on any other provenance — the code-level expression of **T1** (`AGENT_PLAN`/`AGENT_STATE` exist only to be
  rejected), a complement to (not a replacement for) account-B isolation. It builds the codegen'd `DiffIR`
  (golden=expected, deployed=actual; `reward∈{0,1}` = zero normalized diff) **tool-agnostically** and
  **deterministically** (resources + property paths canonically ordered → order-independent + K-run identical;
  a same-address type mismatch → a reserved `$type` propertyDiff). **DRY:** reuses the E1
  `DiffIR`/`Resource`/`PropertyDiffs`/`Change`/`Reward` contract types; per-tool adapters (#35) + the golden
  generator (#75) do the tool-specific normalization of one side. `NORMALIZATION.md` documents the adapter↔core
  split + the determinism contract (AC3); the report serializes with `exclude_none` (the schema-valid sparse
  form — closes the ISSUES.md `propertyDiffs:null` DiffIR residual). **Reconciliation flagged on the issue:**
  the schema *description* reads "adapter produces this IR," but the **core** producing it from two normalized
  states is what AC2 requires and keeps the determinism-critical diff in one place (the brain leaves the
  diff-owner open). **Wiring:** the first intra-workspace import (diff-ir → contracts via `pythonpath`/`mypy_path`;
  the `pydantic.mypy` plugin — first hand-written plain-`BaseModel` package under the `Any` ban —
  + `follow_imports=silent` for the sibling spine); `uv.lock` + `bun.lock` both updated. **Value equality +
  validity are defined by RFC 8785 JCS canonicalization** (the form `RewardRecord.reportDigest` is signed with,
  so the grade and the digest agree by construction), behind a thin **exact-type input guard** (`type(x) is T`):
  `rfc8785.dumps` coerces a builtin subclass via user code, so a subclass / reference cycle is rejected before
  it can forge or flip its canonical bytes. TDD: 50 tests; cross-model `/review` (Claude + Codex `gpt-5.5`
  xhigh, **9 passes to convergence** — 6 on the original diff + 3 on the JCS refactor that caught the
  subclass-coercion forge then the cycle crash) hardened the reward against false-reward-1 / laundering paths.
  `bun run verify` green **20/20** (forced, 0-cached). (PR #145.)
- **E2-5 (#75): golden-target generator — the account-B verifier's reproducible ephemeral target (2A).**
  The first **E2 verifier-core** code: new **`py/packages/verifier`** (`assayops_verifier`).
  `generate(task, seed)` deterministically regenerates the expected **normalized resource set**
  (`GoldenResource` = address/type/properties — diff-IR-compatible, so the E3/#34 adapter diffs deployed
  state against it) — **pure over (task, seed)**, never the agent's synth/plan/state (T1/§1/§8); a
  **declarative regeneration, not running reference IaC**. The per-task golden builders are the engine's
  **corpus seam** (`GoldenRegistry`); real builders live in the **private corpus (#76)** (the engine, NOT
  corpus authoring), and in-repo tests use **synthetic** builders only (held-out residency). **Determinism
  (AC1, feeds #46):** hash-based ephemeral tokens (no clock/RNG) + canonical address-sort + JCS key-sort →
  byte-identical across K runs (negative-controlled). **Content address (AC4):** `golden_digest` =
  lowercase-hex SHA-256 over RFC 8785 JCS canonical bytes, **reusing the locked `assayops_contracts.jcs`
  recipe** (DRY) — reproducible from (task, seed) + the record's `trajectory_id`→`task_id`→seed +
  `graderVersion`; **no contract-schema change** (the reward record has no golden-digest field; a dedicated
  one would be a flagged #28 `fixture-change`, not silently added). **Fail-closed** (unknown task / duplicate
  addresses raise — vector #15). **Hardened** Pydantic models (frozen/extra-forbid/strict; the pydantic.mypy
  `disallow_any_explicit` gotcha fixed via the plugin + init_typed/init_forbid_extra). First cross-package
  Python dep — consumes `assayops_contracts` by source path (the repo's virtual-member convention); contracts
  untouched. **Three adversarial-review rounds converged to MERGE** (`/review`, then a founder-requested
  **Opus 4.8 max** + **Codex `gpt-5.5` xhigh** pair): the **moat held in all** (no agent-reachable forge
  path — the golden is account-B-internal), and every finding was **content-address-integrity / fail-closed
  hardening** of the open-`properties` channel, all closed + negative-controlled: reject
  set/non-finite-float/oversized-int/non-UTF-8-surrogate/non-JSON and **only exact JSON types** (subclass
  iteration/encoding can diverge from what's hashed); canonical-by-construction model + immutable `resources`
  tuple; `generate` wraps **any** builder failure into the single `GoldenError`; `golden_digest` re-checks the
  **live** golden (catching a mutated set/BaseModel/cycle) before canonicalizing; injective length-prefixed
  token. `bun run verify` green **20/20** (35 verifier tests; the load-bearing guards negative-controlled);
  both lockfiles frozen-checked. Runtime-import hardening (consume contracts as an installed pkg) deferred to
  #147. **Gates #31** (golden→reward integration). (PR #146.)

- **E1-5 (#140): codegen hardening — align the hand-maintained lists with the whole schema set.** The
  #29-review tail: three spots that wouldn't follow a newly added schema. (1) `schemas.test.ts` now
  **disk-enumerates** `contracts/schemas/*.schema.json` for the Draft-2020-12 + ajv-compile coverage (a new
  schema is validated automatically; the 4 bespoke instance/modeling tests stay keyed to fixtures). (2) The
  `just codegen` **reward-pin** (`reward: number;` → `0 | 1;`, the §8 binary invariant quicktype can't emit as
  a literal union) was a blanket file-wide rewrite asserting only ≥1 match — now **anchored** to the
  `RewardRecord` interface block + an exactly-one fail-closed guard, so a future *unrelated* `reward: number;`
  can't be silently narrowed (regeneration byte-identical to the committed `generated.ts`). (3) A fail-loud
  **re-export parity test** (`test_model_reexports.py`): every `BaseModel`/`Enum` under `models/*.py` must be
  in `assayops_contracts.__all__` + importable (datamodel-codegen leaves `models/__init__.py` empty, so the
  top-level re-exports are hand-maintained; a *dynamic* re-export would break `mypy --strict` re-export
  visibility, so harden with a test, not magic). **Quicktype globbing + `just-version` pinning were already on
  `main` (PR #139)** — grounding against `origin/main` showed the issue body's "quicktype globbed" was
  correct (the review-comment's "not globbed / never touched justfile" was stale: `origin/main` globs;
  PR #139's squash changed `justfile` +11/−9) and the body's "just-version unpinned" was stale (pinned in
  `ci.yml` + `localstack-smoke.yml`) — so neither was re-done. Proven RED→GREEN with a throwaway 5th schema
  (reaches both generators + the ajv test + the parity test with no list edit), then removed → regeneration
  byte-identical (codegen-parity gate stays green). **Not a `fixture-change` PR** (no `contracts/schemas|vectors`,
  generated-file, or `tools/red-team` edits; `gen_vectors.py` untouched). **Cross-model `/review`** (Claude
  adversarial + Codex `gpt-5.5` xhigh, 3 passes to convergence) hardened the §8 reward-pin to fail **closed**
  on any quicktype-format drift — isolate the RewardRecord interface block by `export interface`-header count +
  top-level-brace termination, `${var:-0}` count default, block-scoped pin-landed backstop — and switched the
  re-export parity test to **object-identity** (catches a cross-module class-name collision); all changes keep
  regeneration byte-identical. `bun run verify` green 17/17. (PR #144.)
- **E1-4 (#29): CI regenerate-and-diff parity gate — E1 (the contract spine) complete.** The DECISIONS.md
  §8 "one-schema codegen" non-negotiable is now CI-enforced: a dedicated **`codegen-parity` job** in the ci.yml
  workflow (it spans both generators — quicktype/bun + datamodel-codegen/`gen_vectors`/uv) runs
  `just codegen` + `just vectors` and fails on any drift (a targeted `git add -A` + `git diff
  --cached` over the three generated paths — catches edits AND added/removed modules; a clear `::error::`
  points back at the recipes). It's its **own job** (not folded into the `ts`/`py` verify lanes — it spans
  both generators and regenerates into the tree; a failed `codegen-parity` check names the cause unambiguously), made
  a **required status check** on the `main` ruleset once the workflow is on `main` — GitHub's
  create-the-check-before-requiring order (requiring it while another open PR's branch lacks the `codegen-parity` run
  would block that PR on a never-reported check; grounded in the GitHub rulesets REST API + status-check docs).
  **Proven to have teeth:** a one-property schema edit drifts all three artifacts (TS `generated.ts`, the
  Pydantic model, the JCS `jcs-golden.json`) → gate exits 1; clean tree → exits 0 (no false-fail).
  **Byte-parity (AC2) was already covered** and runs in `bun run verify` — the py lane's
  `test_python_and_ts_canonicalize_are_byte_identical` (direct TS-subprocess identity) + the ts lane's
  `sha256(canonical)==golden` — so it was verified, not rebuilt. The cross-model `/review` (Claude
  adversarial + Codex gpt-5.5 xhigh) also **hardened `just codegen`**: quicktype now reads the **whole**
  `contracts/schemas/` dir (`LC_ALL=C` glob, byte-identical to the prior explicit list) so a newly added
  schema reaches **both** generators — a hardcoded list had let a new schema's TS type go ungenerated and
  thus invisible to the gate; it also fixes an opaque removed-schema crash. Residual hardcoded-list nits (TS
  ajv test, reward-pin breadth) are tracked in **#140**. **CI-wiring + a codegen-recipe
  fix** — no `contracts/schemas|vectors` or generated-file edits → not a fixture-change PR; the agent that
  writes code never edits the grader. `just` action SHA-pinned + binary version-pinned (`just-version` 1.53.0,
  in both ci.yml `codegen-parity` and localstack-smoke); codegen tools pinned
  (bun.lock/uv.lock) → deterministic. `bun run verify` green 17/17. (PR #139.)
- **E3-4 (#80): boto3 deployed-state read-coverage spike — GO with conditions (recorded decision; no floor
  change).** The E17 (#113) verifier-read spike is resolved. **Terraform read path = boto3 Cloud Control
  `GetResource`/`ListResources` only** — provisioning-agnostic (reads Terraform-created resources without
  provider plugins, the T1 constraint); **CFN drift / `DescribeStackResources` are stack-scoped → the CDK
  adapter's (T3) path** (and drift alone is incomplete: `NOT_CHECKED` / uncomparable props), N/A for Terraform.
  **Coverage:** the authoritative AWS "Resource types that support Cloud Control API" table (~**1300** public
  types) — distinguish **readable** (`read` handler) / **enumerable** (`list` handler, differs per type) /
  **property-covered** (`GetResource` omits write-only props). Common Terraform corpus well covered; gaps =
  `IAM::Policy` + `Route53::RecordSet`/`RecordSetGroup`; inline `RolePolicy`/`UserPolicy`/`GroupPolicy` are
  Read-but-not-List. **Unsupported/unreadable = FAIL-CLOSED**; and **extra/over-provisioned resources** (the
  moat-critical half — `list_resources` is per-`TypeName`/per-Region) require a **closed-world** predicate
  (deployed set ≡ golden set), enforced primarily by **T7 SCP create-allow-lists** (a closed set of
  CC-listable types + Regions makes an out-of-scope resource unreachable by construction) + exhaustive,
  paginated, Region/global-service-aware, fail-closed union-enumeration — reads alone can't close vector #15. **Read-only IAM** = **`cloudformation:GetResource`/`ListResources`**
  (Cloud Control's IAM prefix is `cloudformation`, verified) with `Resource:"*"`, + the union of in-scope
  types' `handlers.read`∪`list` permissions (least-privilege via `describe-type`); account-B verifier assumes a
  read-only role in account A (SCP-protected; no A→B path). **Go/no-go = GO with conditions** (closed-world via
  T7; per-property gate; corrected IAM) — scope the Phase-1 **Terraform engine-validation** corpus to
  CC-readable types, **without** letting that screen shape the Phase-2 proof corpus (R2/§6 representativeness —
  uncovered families get fallback adapters). Surfaces a **new T7 requirement** (SCP create-allow-list aligned
  to CC-listable types + Regions). Grounded against AWS primary docs (live) + `DECISIONS.md` §1/§5/§8 + brain;
  **cross-model `/review` (Claude + Codex `gpt-5.5` xhigh) caught the closed-world hole + an IAM-prefix error**
  (both fixed + re-reviewed). Decision recorded on #80; the resolved-`[spike]` note is **landed in
  `DECISIONS.md` §1** (founder-ratified), and the follow-up work is **tracked as #141** (E2 verifier-side
  read-coverage enforcement) + **#53** (the T7 closed-world create-allow-list) — not left in comments. (PR #138.)

- **infra-local: relocate under `py/packages/` + docs + nested agent-config (#135).** **Moved `infra-local`
  → `py/packages/infra-local`** so the one Python package that lived at the repo root now sits with its uv
  siblings: the `./py/**` CI glob routes it to the **py** lane automatically, so the ci.yml `infra-local`
  special-case filters, the explicit `uv`/bun workspace member, and the nested-md "py lane despite root" note
  all **drop** (the move removes more special-casing than it adds). `py/packages/infra-local/README.md`
  documents the *why* — the smoke validates **LocalStack's fidelity for the verifier's Cloud Control read
  path** (NOT boto3; the moto/Floci "S3 works ≠ GetResource" precedent + `DECISIONS.md` R3), a **regression
  canary** on the pinned image (already caught `DetectStackDrift` unsupported). Added a **concise, path-scoped
  nested `py/packages/infra-local/CLAUDE.md` + `AGENTS.md` symlink** (loads only when an agent works there —
  grounded in the official Claude Code + Codex nested-loading docs; the first nested constitution in the repo)
  carrying the one non-inferable landmine: never add a `test` script (unlike its siblings — it would run the
  LocalStack smoke in the hermetic `bun run verify` gate and break CI). Cross-model `/review` converged to
  merge. `bun run verify` green. (PR #136.)

- **E17-F1 (#116): boto3/Cloud-Control skill + LocalStack boto3 read smoke + the CLAUDE.md language flip.**
  Closes #116's three remaining parts (its logger task already landed as #132/#133). **(1) Vendored the
  prefer-official boto3 skill** `aws-sdk-python-usage` — first-party AWS (`aws/agent-toolkit-for-aws`, the
  same source as the repo's `aws-cdk`/`aws-cloudformation`/`aws-iam`; the Python peer of the demoted
  `aws-sdk-js-v3-usage`). skills.sh had only off-target community skills, so checked the maintainer's GitHub
  directly (`verify-skill-absence-beyond-the-registry`). It grounds the read-path SDK mechanics — clients,
  typed `ResourceNotFoundException` (the negative-assertion path), paginators (`list_resources`), waiters
  (async drift polling), adaptive retries. Vendored byte-identical to upstream (markdown-only → no script
  surface); no `-a '*'` overshoot; lock `skillPath` matches the sibling pattern. **(2) Re-homed
  `infra-local`'s smoke from TS to boto3/Python** (E17 Python-first): `infra-local` is now a boto3
  LocalStack smoke (an env-server-style py package + bun wrapper) proving the EXACT verifier read path —
  Cloud Control `get_resource` + `list_resources` + the `ResourceNotFoundException` negative assertion —
  against real LocalStack, **negative-controlled** (never a false pass). Retired the TS `smoke.test.ts` + its
  `@aws-sdk` deps (the verifier reads via boto3 now, so the TS smoke tested an SDK the verifier no longer
  uses); one LocalStack home, run via `just smoke`. The read-path seed that **grounds + unblocks #80**. Kept
  OUT of the hermetic `bun run verify` gate (a `smoke` script, not `test`), so the gate stays Docker-free
  while ruff + mypy --strict still cover it. **Validated against the Python craft skills**:
  `python-resilience`/`error-handling` → dropped the hand-rolled retry for botocore's own bounded retries
  (the `use-the-librarys-official-mechanism-not-a-hand-roll` lesson); `python-type-safety` → `Any` at the
  untyped-boto3 boundary is idiomatic; `python-testing-patterns` → pytest fixtures. **Empirical finding
  (`local-aws-emulator-must-prove-read-api`): LocalStack does not serve `DetectStackDrift` ("not currently
  supported by LocalStack") — drift-read coverage is #80/E2 against real AWS.** boto3 reuses the pinned
  workspace dev dep (no new dep). **(3) Finished the CLAUDE.md language flip:** Toolchain reordered
  Python-first (the proof-critical core); the AWS preflight row names `aws-sdk-python-usage`. `bun run verify`
  green **17/17**; both lockfiles frozen-checked. (PR #134.)

- **E17-F4 (#132): Python structlog logger for the proof-critical core.** New `py/packages/logger`
  (`assayops_logger`) — the structlog mirror of the TS `@assayops/logger` (pino) — for the env-server (E5),
  verifier (E2), and reward ledger (E4). JSON one-event-per-line to **unbuffered stdout** (dev `ConsoleRenderer`
  gated on `sys.stderr.isatty()`), ISO-8601 UTC timestamps, `make_filtering_bound_logger` fast filtering +
  `cache_logger_on_first_use`. The load-bearing item is a **deny-by-key redaction censor** (structlog ships
  none): a processor mirroring the TS `SECRET_KEYS` exactly (parity-tested against `ts/.../index.ts`), recursive
  (dicts + lists — closing pino's depth/array gap), mutating the already-copied event_dict **in place** (not a
  clone — the PR #110 mistake). The **unified `ProcessorFormatter` stdlib bridge** folds boto3/uvicorn records
  into the same JSON pipeline + redaction + `trajectory_id` (one shared chain = one censor). **Trust-boundary
  hardening (DECISIONS.md §8), secure-by-default:** botocore/boto3/urllib3/s3transfer clamped to never-below-INFO
  (wire-level DEBUG leaks AWS creds no pattern catches), and `show_locals=False` on the prod exception renderer
  (a KMS-signing crash can't dump key material from frame locals). `trajectory_id` via `structlog.contextvars`
  (tested on the async-emit path AND spawned-coroutine isolation). The redaction + clamp + `show_locals` tests
  were **proven real** by negative controls (disable → tests fail). **Grounded in the official structlog docs**
  (processors / standard-library / contextvars / exceptions / performance / logging-best-practices, structlog
  26.1.0) read this pass, not cached knowledge. **#116's logger task is complete** (decided: KEEP the TS
  `@assayops/logger`, scoped to the consumer/web surface; #116 retains the LocalStack boto3 smoke + boto3 skill).
  `bun run verify` green **17/17** (logger: 53 py tests; both lockfiles updated, frozen-checked). OTel
  export/trace-correlation + prometheus metrics are out of scope (later / #79). (PR #132.)

- **4 wshobson Python skills — vendored (closes #127); the Python-first hardening batch is complete.** The
  four `wshobson/agents` Python skills are now in the committed layer (`.agents/skills/` + `.claude`/`.hermes`
  symlinks + `skills-lock.json` hash-pins): **`python-resilience`** (the verifier's transient-vs-genuine-failure
  rule, `deterministic-verification`, + boto3 adaptive retries — E2/#80), **`python-error-handling`** (parsing
  untrusted IaC/boto3 responses at the verifier/adapter boundary — E2/E3), **`python-configuration`** (typed
  settings + secrets via `pydantic-settings` for the ledger/account creds — E4), and **`python-observability`**
  (the **structlog** logging decision + eval/verifier metrics). Founder elected to **vendor all four now**,
  overriding #127's epic-gating — community-skill vendoring is cheap and auto-loads by relevance — which closes
  the Python-first hardening batch (#124 `Any` ban, #126 config-DRY, #128 Pydantic-v2 skill). All four are
  **markdown-only** (no bundled scripts → no `skills-sync-hygiene` script surface; the `python-resilience`
  "Critical Risk (Gen)" scanner rating is a false positive on example `httpx` calls in a doc). A lean
  `CLAUDE.md` preflight row maps each to its surface. `bun run verify` green 14/14; no `bun.lock`/`uv.lock`
  change (skills-lock.json is separate from the package locks). (PR #131.)

- **Pydantic-v2 skill — authored + vendored (closes #128).** A homegrown Pydantic v2 skill for the contract
  spine (`AssayInc/skills#9`, merged): the load-bearing **`model_dump_json` isn't JCS-canonical** rule
  (canonicalize `model_dump(mode='json')` before signing), `frozen`/`extra='forbid'`/`strict` hardening, the
  `pydantic.mypy` `disallow_any_explicit` gotcha (ties to #124), validators/`TypeAdapter`/`pydantic-settings`.
  Grounded in the official Pydantic v2 docs (load-bearing claims **primary-source-verified**); reviewed Codex
  `gpt-5.5` xhigh **×5 to convergence**; eval = a with/without A/B + the **optimizer-run** trigger set
  (**0/10 false triggers**; recall is the capable-model confound). Vendored into `.agents/skills/pydantic-v2`
  (+ `.claude`/`.hermes` symlinks + `skills-lock.json`) with a `CLAUDE.md` preflight row.

- **#129 (closes #126): config-DRY — shared ruff config hoisted to root via `extend`.** The duplicated
  `[tool.ruff]` (line-length / target-version / lint.select) now lives once in the root `pyproject.toml`;
  each member `extend`s it (proven to inherit the select — a probe fires `ANN401` + `S311` via the root
  config, not silently dropped to defaults). **mypy/pytest stay per-package by design** — mypy has no
  config-merge and the packages run divergent `disallow_any_explicit` strategies (contracts global incl.
  `scripts/`, env-server scoped with tests exempt), so it is intentional divergence, not duplication.
  `bun run verify` green 14/14. (PR #129.)

- **#124: Python type-safety parity — forbid explicit `Any` (mypy + ruff).** The Python lane now mirrors the
  TS `any` ban: mypy **`disallow_any_explicit`** (which `--strict` does NOT enable, confirmed vs the mypy
  docs) + ruff **`ANN401`**; `object` (the `unknown` equivalent) / a Pydantic model at boundaries — proven to
  fire (a probe `Any` is rejected by both). Also added ruff `S`/`LOG`/`G`/`ASYNC` + `ruff format --check`
  gating, cleaned the env-server `dict[str, Any]` → `dict[str, object]` (surfacing the real 3-level
  cloud-state nesting), and `CLAUDE.md` got the `Any` rule + **structlog** named (the pino analog) + a
  Python-skills preflight row. Cross-model `/review` (Claude + Codex `gpt-5.5` xhigh; re-reviewed after the
  scripts-gap fix → ship). Closed **#125**; follow-ups tracked as **#126** (config-DRY), **#127** (4 wshobson
  Python skills, epic-gated), **#128** (homegrown Pydantic-v2 skill). `bun run verify` green 14/14.

- **E1-3 (#28): JCS canonicalization + golden vectors.** The contract spine's canonical-byte recipe is now
  **production on both sides + locked by a golden corpus**: `assayops_contracts.jcs.canonicalize` (PyPI
  `rfc8785`, the account-B **signer**) and `@assayops/contracts` `canonicalize` (npm `canonicalize`, the TS
  **consumer/verify** side) emit **byte-identical** RFC 8785 JCS (`DECISIONS.md` I3 · `record → JCS → UTF-8
  → SHA-256 → KMS Sign`). The locked **`contracts/vectors/jcs-golden.json`** (record → canonical bytes →
  sha256, regenerated by **`just vectors`**, deterministic) covers all four contract records —
  **reward-record** (the signed artifact: both `reward∈{0,1}` + the ns-timestamp digit string), trajectory,
  diff-ir, task-spec (incl. a non-ASCII vector for raw-UTF-8 parity). **Byte-parity is asserted three ways:**
  the Python lane + the TS lane each reproduce the committed corpus (drift-locked) **and** a direct
  Python↔TS subprocess identity test. This is the **inaugural `fixture-change` PR** (the locked-grader
  exception, `DECISIONS.md` §8): adds the `contracts/vectors` CODEOWNERS rule + the turbo
  `globalDependencies` cache-bust; the #115 spike's canonicalize is DRY'd onto the production recipe. **#29
  (the CI regenerate-and-diff / parity gate)** is the remaining E1 tail. `bun run verify` green (14/14).

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
  cache-keyed lanes that don't block each other — **`ts`** (bun/turbo) and **`py`** (uv + turbo); the two
  filters partition all packages by toolchain, so the union is exactly `bun run verify`. `permissions: contents: read`, no secrets/OIDC — **zero account-B creds**
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
