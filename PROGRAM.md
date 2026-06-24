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
  The contracts spine (**E1 #2**) is **complete** (planned deliverables #26–#29 all landed),
  **reframed Python-signer↔TS-consumer**: **#28** (JCS + golden vectors) and **#29** (the CI
  regenerate-and-diff parity gate) landed; one review-surfaced codegen-hardening follow-up (**#140**) is
  tracked under the epic.
- **Type checker:** `mypy --strict` is the bridge — now also **`disallow_any_explicit`** + ruff `ANN401` (the Python `Any` ban mirroring the TS `any` ban; `object` is the `unknown` equivalent); **`ty`** (Astral) is the committed target, adopted at
  E2's first step once it is Stable + Pydantic-clean (**#119**). **Other tooling follow-ups:** **#132
  (Python structlog logger — landed; carved from #116)**, **#116 (boto3 skill + LocalStack boto3 read smoke
  + language flip — landed, PR #134)**, #117 (brain/wiki sync).
- **Next ready work:** **#80** (boto3 read coverage — now **grounded + unblocked by #116**: the vendored
  `aws-sdk-python-usage` skill + the `infra-local` boto3 LocalStack smoke prove the Cloud Control
  read path). With **E1's spine (#26–#29) complete**, the remaining gates for E2–E7 are the **#114** +
  **#115** spikes (both landed GO; **E5/#6** unblocked by the #114 GO; **E4/#5** inputs surfaced by the
  #115 GO). **T0 team gate (#25) closed** (founder interim RL/eval owner; Phase 3 hard-gated on the
  permanent owner).

## Recently Landed

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
