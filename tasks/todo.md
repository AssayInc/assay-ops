# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## E1-2 (#27) — Codegen wiring (quicktype + datamodel-code-generator) — IN PROGRESS (branch `feat/e1-2-codegen-wiring`)

**Goal (AC):** a root **`just codegen`** regenerates **committed** TS types (quicktype) + Pydantic v2
models (datamodel-code-generator) from `contracts/schemas/`; both generators **pinned** + **fixed flags**
→ deterministic (re-run = no diff, the #29 precondition); a **semantic** reward-record round-trip test
(TS serialize → Pydantic parse → Py serialize → deep-equal); `bun run verify` green (tsc strict + Biome;
mypy --strict + ruff).

**Validation (issue vs. DECISIONS + brain + code — don't trust the AI-written issue blindly):**
- Grounded in `DECISIONS.md` **I3 / 5A / §8**: one JSON-Schema source → quicktype (TS) +
  datamodel-code-generator→Pydantic v2 (Py); **never hand-maintain dual types**; artifacts committed.
  assay-brain adds no deeper locked codegen detail (rationale lives in I3). 0 open blockers (#26 landed).
- **Scope = codegen + semantic round-trip ONLY.** JCS canonicalization + golden vectors = **#28**; the CI
  regenerate-and-diff / byte-parity gate = **#29**. Keep both out. **Do not touch `contracts/vectors`**
  (locked, #28) — the round-trip uses a **synthetic inline** instance.
- **Empirical grounding caught two issue errors** (verified vs. the pinned tools' `--help` + output, not
  the issue prose — the skill-preflight rule):
  1. The issue's Python snippet `--input contracts/schemas … --output …/models.py` **fails** ("Modular
     references require an output directory, not a file") — directory input forces **modular dir output**
     → output to `…/assayops_contracts/models/` (4 `*_schema.py` modules + header `__init__.py`).
  2. `datamodel-codegen` default `constr()`/`conint()` annotations **fail `mypy --strict`** → add
     **`--use-annotated`** (emits `Annotated[str, Field(...)]`; verified Success). Ruff-clean wants the
     **`ruff-check ruff-format`** formatters (docs), not just `ruff-format`.

**Design:**
- **`just codegen`** (root justfile recipe; the placeholder comment already anticipates it), fixed flags:
  - TS: `quicktype -s schema --lang typescript --just-types <4 schemas, fixed order> -o
    ts/packages/contracts/src/generated.ts` (pinned `quicktype@23.2.6` → bun.lock).
  - Py: `datamodel-codegen --input contracts/schemas --input-file-type jsonschema --output-model-type
    pydantic_v2.BaseModel --use-annotated --disable-timestamp --formatters ruff-check ruff-format
    --target-python-version 3.12 --output …/assayops_contracts/models` (pinned
    `datamodel-code-generator[ruff]` + `pydantic` → uv.lock). `--disable-timestamp` = no header stamp
    (determinism).
- **Generated `any` (TS) — the #26-deferred call.** quicktype has **no `unknown` option** (confirmed:
  `--help` + README). Open fields (`observation`/`action` → `{[k]:any}`, `expected`/`actual` → `any`)
  emit `any`, which Biome `noExplicitAny:error` rejects. **Decision = option (a):** exclude the generated
  file from Biome (`!…/src/generated.ts` in root `biome.json`); **`tsc` strict still typechecks it.**
  (Rejected (b) refine-schema: touches the #26 source of truth + ripples to #28/#29, and an open/union
  JSON-value schema still emits `any` in quicktype; rejected a regex any→unknown post-process: fragile
  over the "any JSON" comments, a determinism risk for the #29 gate.)
- **Generated lint carve-out (Py).** Long schema-description strings → ruff **E501** (unwrappable);
  mypy --strict passes. → carve the generated `models/` out of ruff **lint** while datamodel's ruff-format
  owns its formatting; **mypy --strict still checks it.** (Symmetric with the TS Biome exclusion — the
  standard treatment for generated code.)
- **Layout / placeholders.** TS: `src/generated.ts` (generated) + `src/index.ts` re-exports it (replaces
  `PLACEHOLDER`); drop placeholder `smoke.test.ts` (round-trip + real types supersede it); `schemas.test.ts`
  (ajv) stays. Py: generated `models/` subpackage + a **hand-written** `assayops_contracts/__init__.py`
  re-export (stable; codegen writes only under `models/`); replace placeholder `test_smoke.py`.
- **Round-trip test (AC behavior).** Cross-language ⇒ runs in the **py lane** (only CI lane with bun+uv).
  `py/packages/contracts/tests/test_roundtrip.py`: `bun run` a tsc-checked emitter
  (`ts/packages/contracts/scripts/emit-reward-record.ts`: `const r: RewardRecord = {…synthetic…}` →
  `JSON.stringify`) → `RewardRecord.model_validate_json` → `model_dump_json` → `json.loads` deep-equal the
  TS emission. The emitter compiling under tsc proves the TS type accepts the instance; the cross-lang
  parse + re-serialize proves the Pydantic model agrees + round-trips.

**Steps (TDD):**
- [ ] Branch `feat/e1-2-codegen-wiring`.
- [ ] Pin generators: quicktype → `ts/packages/contracts` devDeps (`bun install`);
  `datamodel-code-generator[ruff]` + `pydantic` → py deps (`uv sync`).
- [ ] Add `just codegen` recipe (fixed flags, both lanes).
- [ ] RED: `test_roundtrip.py` (+ the emitter) → fails (no generated types).
- [ ] GREEN: run `just codegen` (commit artifacts); emitter + index/`__init__` re-exports; Biome exclude +
  ruff carve-out; drop placeholders/smoke. Round-trip green.
- [ ] `bun run verify` green (both lanes); re-run `just codegen` → `git diff` empty (determinism).
- [ ] Update `PROGRAM.md` (+ `docs/ARCHITECTURE.md` codegen sketch → justfile, drop the never-built
  `contracts/codegen.config`); PR "Closes #27"; `/review`.

### Review

- **Done + proven:** root **`just codegen`** regenerates committed TS interfaces (`quicktype@23.2.6` →
  `ts/packages/contracts/src/generated.ts`) + Pydantic v2 models (`datamodel-code-generator 0.65.0` →
  `py/packages/contracts/src/assayops_contracts/models/`) from `contracts/schemas/`. **`bun run verify`
  green (11/11, FULL TURBO)**; the cross-language reward-record round-trip test passes (TS-serialize →
  Pydantic-parse → Py-serialize → deep-equal). **Deterministic:** re-running `just codegen` is
  byte-identical (sha256-verified) — the #29 gate's precondition.
- **AC coverage:** `just codegen` regenerates both lanes, artifacts committed ✓; both generators pinned
  (`bun.lock` / `uv.lock`) + fixed flags → no-diff re-gen ✓; semantic round-trip test ✓; verify green —
  tsc strict + Biome (TS), mypy --strict + ruff (Py) ✓.
- **Grounding caught two issue errors** (verified vs. the pinned tools, not the issue prose): (1) the
  issue's `--output …/models.py` fails on directory input → **modular dir output** (`models/` package);
  (2) default `constr()`/`conint()` annotations fail `mypy --strict` → **`--use-annotated`** (and ruff
  formatters are `ruff-check ruff-format`, not just `ruff-format`).
- **Decisions settled (the #26-deferred codegen-policy calls):** generated **`any`** (open diff-IR /
  trajectory fields; quicktype has no `unknown` option per `--help` + README) → **Biome exclude** for
  `src/generated.ts` (tsc strict still typechecks). Generated Python **E501** (unwrappable
  description strings) → ruff **per-file-ignore** for `models/*.py` (mypy --strict still typechecks).
  Layout: generated `models/` subpackage + hand-written re-export `__init__.py`; `src/generated.ts` +
  re-export `index.ts`; placeholders + smoke tests dropped (round-trip + real types supersede them).
- **Scope discipline:** codegen + semantic round-trip only. JCS/byte-parity (#28), the CI parity gate
  (#29) **not** pulled in; `contracts/vectors` (locked, #28) **untouched** — the round-trip uses a
  synthetic inline instance.
- **Flagged (out of #27 scope, not silently fixed):** `docs/ARCHITECTURE.md` §spine still says "rewards as
  **bounded doubles**" — stale since #26 landed `reward ∈ {0,1}` (a `DECISIONS.md` §8 non-negotiable). A
  one-line follow-up (or fold into #28, which edits the same JCS prose).

---

## E1-1 (#26) — Author the 4 JSON Schemas — IN PROGRESS (branch `feat/e1-1-json-schemas`)

**Goal (AC):** `reward-record`, `trajectory`, `diff-ir`, `task-spec` JSON Schemas (Draft 2020-12) exist;
large IDs/nonces/ns-timestamps modeled as **strings**, rewards as **bounded doubles**, NaN/Infinity
**rejected** (validation test).

**Validation (issue vs. code + deps):**
- #26 was `blocked_by` #25 (T0 team gate); #25 **closed** (founder = interim RL/eval owner + hire opened) →
  #26 now ready (0 open blockers). Within E1: #26 → {#27, #28} → #29 (#29 `blocked_by` #27/#28); #27/#28
  logically need #26's schemas.
- No top-level `contracts/` exists yet (only per-lane shell pkgs). ARCHITECTURE.md §spine: schemas live at
  `contracts/schemas/*.schema.json` (neutral source of truth); `contracts/vectors` = #28, codegen = #27.
- **Scope = schemas + a validation test ONLY.** Codegen (#27), JCS/golden vectors (#28), CI parity (#29)
  are separate issues — don't pull them in (smallest change that meets the AC).

**Design:**
- `contracts/schemas/{reward-record,trajectory,diff-ir,task-spec}.schema.json` — Draft 2020-12, each with
  `$id` + `additionalProperties:false`. Field shapes grounded in the `reward-ledger-worm` +
  `deterministic-verification` skills. Modeling rules (JCS-forced, ARCHITECTURE.md §spine): IDs / nonces /
  ns-timestamps = `string`; reward = `{type:number, minimum:0, maximum:1}` (bounded double, finite).
- Validation test (TS lane, ajv Draft-2020-12) at `ts/packages/contracts/tests/schemas.test.ts`: every
  schema compiles; a good instance validates; reward NaN / Infinity / out-of-range rejected; a numeric ID
  rejected (string rule); an unknown property rejected (tight contract). ajv = dev-only test dep.
- **TS lane chosen** for #26's test: ajv's bounded min/max robustly rejects NaN/±Inf; cross-language
  byte-parity is #28/#29's job, not this issue's.

**Steps (TDD):**
- [x] Add `ajv` dev dep to `ts/packages/contracts`; `bun install`.
- [x] Write failing `tests/schemas.test.ts` (schemas absent → RED).
- [x] Author the 4 schemas → GREEN.
- [x] `bun run verify` green (both lanes).
- [x] Update `PROGRAM.md`; PR "Closes #26"; `/review`.

### Review

- **Done + proven:** `contracts/schemas/{reward-record,trajectory,diff-ir,task-spec}.schema.json` (Draft
  2020-12, `$id` + `additionalProperties:false`) authored as the neutral source of truth. Modeling rules
  applied uniformly: ids / nonces / timestamps / seeds / digests = `string`; `reward` = `enum {0,1}`
  (binary, finite). Validation test `ts/packages/contracts/tests/schemas.test.ts` (ajv Draft-2020-12) — TDD
  RED→GREEN, 16 tests. `bun run verify` green (8/8 tasks, both lanes).
- **AC coverage:** schemas exist ✓; large ids/nonces/ns-timestamps as strings ✓ (test rejects numeric ids);
  reward ∈ {0,1} (binary, finite double) ✓; NaN/Infinity + partial-credit rejected ✓ (enum admits only 0/1;
  test asserts 0.5 / 2 / −0.5 / NaN / ±Inf all rejected).
- **Cross-model `/review` fixes applied (Claude conf 9 + Codex gpt-5.5 xhigh):** (1) **`reward` →
  `enum:[0,1]`.** First modeled as a continuous bounded double `[0,1]`; `DECISIONS.md` §8 (non-negotiables)
  locks `reward ∈ {0,1}` and `deterministic-verification` names a 0.0–1.0 score as the gameable
  anti-pattern — the continuous form was a silent frozen-floor deviation. Corrected (still a finite JCS-safe
  number). (2) **`attempt`/`index` capped at 2^53−1** (the same >IEEE-754 hazard the string-id rule
  prevents). (3) **`diff-ir` `expected`/`actual`** documented as a deliberate any-JSON boundary (precise
  value typing deferred to where the IR is produced).
- **Tightening round (grounded in `DECISIONS.md` + assay-brain, per founder guidance — don't trust the
  AI-written issue blindly):** timestamps (`gradedAt`/`createdAt`) → integer-nanosecond **digit strings**
  (`^(0|[1-9][0-9]*)$`, one canonical no-leading-zeros form, not the RFC-3339-or-ns ambiguity); `task-spec.tool` →
  `terraform | cdk` (the locked T2/T3 authoring tools — CloudFormation is the read *substrate*, dropped);
  `diff-ir` **`modified ⟺ non-empty propertyDiffs`** via `if/then/else`; and `contracts/schemas/**` added to
  turbo `globalDependencies` — a schema change now busts the contracts-test cache (it didn't before: a
  false-green gap, since the test reads schemas from outside its package). Still deferred: unique
  resource-address (not cleanly JSON-Schema-expressible → the E3 reward core). 24 tests, pristine output.
- **Second cross-model review (pre-merge, Claude + Codex xhigh) — fixes:** timestamp pattern →
  `^(0|[1-9][0-9]*)$` (reject leading zeros — `"007"`≡`"7"` was a JCS byte-parity hole on the *signed*
  path); `diff-ir` propertyDiff now requires `expected` **or** `actual` (`anyOf`) so an empty `{path}` diff
  can't validate. Deferred to #27 (a codegen-policy call both reviewers agree on): typing `diff-ir`
  `expected`/`actual` (bare any-JSON → `any` in generated TS) and IR-number JCS precision.
- **Other design calls:** `tool` enum = `terraform | cdk`; field shapes a coherent v1 grounded in the
  `reward-ledger-worm` + `deterministic-verification` skills.
- **Scope discipline:** schemas + validation only. Codegen (#27), JCS canonicalization + golden vectors
  (#28, the locked `contracts/vectors`), CI parity (#29) are their own issues — not pulled in. `contracts/`
  is the neutral source (not a workspace pkg), so it's outside the lint/typecheck graph by design.
- **Validation:** #26 was `blocked_by` #25 (T0 gate) → closed (founder interim owner + hire opened) → ready.

---

## E0-4 (#21) — Repo hygiene (CODEOWNERS, PR template, secret scanning, CONTRIBUTING) — LANDED (PR #108)

**Goal (AC):** CODEOWNERS + PR template + secret-scanning push protection enabled (a planted secret is
blocked on push); the `Closes #` convention documented in the PR template; a `CONTRIBUTING.md` with the
contributor workflow + a pointer to the quality bar, linking (not duplicating) the README **Get started**.

**Validation (issue vs. code):**
- #21 is open, unblocked, Phase 0 — the last ready E0 eng issue (PROGRAM.md). Accurate, not already done.
- Sole collaborator is `@samuelcastro` (no org teams) → CODEOWNERS can only name him; a global rule is the
  right scope. The locked-grader paths (`contracts/vectors` #28, `tools/red-team` #56) **don't exist yet**
  (ISSUES.md) → no speculative per-path rules; they land in those epics' `fixture-change` PRs.
- The org has GitHub Advanced Security → secret scanning + push protection are enable-able on the private
  repo (unlike rulesets, which needed the paid plan).

**Design:**
- `.github/CODEOWNERS`: `* @samuelcastro`; header notes it's the DECISIONS.md §8 trust-rule enforcement arm.
- `.github/pull_request_template.md`: a `Closes #` line (documents the convention) + a lean quality-bar checklist.
- `CONTRIBUTING.md` (root): branch → focused PR (`Closes #`) → `bun run verify` → `/review` → merge on the
  maintainer's explicit go; trust-boundary + secrets sections; links README Get started + DECISIONS.md §8.
- Secret scanning + push protection enabled via the repo API; proven by a planted-secret push (blocked).
- Deferred (flagged in ISSUES.md): require-code-owner-review in the `main` ruleset (single collaborator →
  would deadlock solo PRs) + the per-path grader CODEOWNERS rules (land with #28 / #56).

**Steps (test-first via the planted-secret push + the gate):**
- [x] Enable secret scanning + push protection (repo API); resolve fabricated test alerts.
- [x] Add `.github/CODEOWNERS`, `.github/pull_request_template.md`, `CONTRIBUTING.md`.
- [x] `bun run verify` green (docs/config — no verify-graph impact; FULL TURBO).
- [x] Prove: a planted (fabricated) secret is blocked on push.
- [x] Update `PROGRAM.md` + `ISSUES.md`; PR "Closes #21" (#108); `/review`.

### Review

- **Done + proven:** secret scanning + push protection **enabled** repo-side (org has GitHub Advanced
  Security); `.github/CODEOWNERS` (`* @samuelcastro`), `.github/pull_request_template.md` (documents
  `Closes #`), `CONTRIBUTING.md` (workflow + quality-bar pointer + secrets; links README Get started). PR
  #108 (`Closes #21`); `bun run verify` green (8/8, FULL TURBO).
- **Push-protection proof:** a planted basket of push-protection-supported secrets (Stripe/SendGrid/Slack)
  was **rejected on push** (`GH013 … Push cannot contain secrets`, exit 1, ref rejected; no bypass, nothing
  landed). First attempts used `google_api_key` — **detection-only** (`hasPushProtection: false`), which
  lands + alerts and does NOT test push protection (user-corrected; lesson added).
- **Scope discipline:** no speculative CODEOWNERS rules for the not-yet-existent locked-grader paths
  (`contracts/vectors` #28 / `tools/red-team` #56) — they land in those epics' `fixture-change` PRs; the
  untracked `.env.example` (not this issue) kept out of the diff.
- **Deferred (ISSUES.md):** require-code-owner-review on the `main` ruleset (single collaborator → would
  deadlock solo PRs) + the per-path grader CODEOWNERS rules.
- **/review:** Claude + Codex (gpt-5.5 xhigh) adversarial passes — clean after fixing two doc-precision
  nits (push-protection wording in CONTRIBUTING.md; PROGRAM.md "essentially complete" → "once it lands").
- **Landed:** PR #108 squash-merged into `main`; E0-4 moved to PROGRAM.md *Recently Landed*; #21 closed.

---

## E0-2 (#19) — Two-lane CI (turbo + uv) + branch protection — IN PROGRESS (branch `feat/two-lane-ci`)

**Goal (AC):** `.github/workflows/ci.yml` runs the canonical `verify` gate on every PR across both
lanes, independently cache-keyed + non-blocking, holding zero account-B creds; branch protection on `main`.

**Validation (issue vs. code + dependency graph):**
- #19 has **no blocked-by deps**; project status Todo — ready.
- **Codegen-parity gate (AC#2) deferred to #29**, which is itself blocked-by #27 (codegen wiring) +
  #28 (golden vectors); no top-level `contracts/` schema exists yet. A regenerate-and-diff / byte-parity
  check against a non-existent schema would be an empty verifier — out of scope here (flag, don't fake).
- **Fixture-change guard deferred:** `contracts/vectors` (#28) + `tools/red-team` (#56) don't exist;
  ISSUES.md says "no action until those epics run." Branch protection records the intent now.
- `bun run verify` (= `turbo run typecheck lint test`) green locally; turbo drives BOTH lanes
  (TS via tsc/biome/`bun test`; Python via `uv run --frozen` mypy/ruff/pytest).

**Design — two parallel lanes (drift-proof complement partition):**
- `ts` lane: `bunx turbo run typecheck lint test --filter='!./py/**'` (bun/turbo) — every non-py package.
- `py` lane: `uv sync --locked` then `bunx turbo run typecheck lint test --filter='./py/**'` (bun + uv).
- Verified via `--dry`: `./py/**` = py-contracts only; `!./py/**` = the 4 non-py packages; union = all 5.
- Independent per-lane `.turbo` caches + uv `enable-cache`; no `needs` edge (lanes don't block each other).
- `permissions: contents: read`; no secrets / no OIDC — zero account-B creds (DECISIONS.md §1, §8).
- Actions SHA-pinned (checkout v7.0.0, setup-bun v2.2.0, setup-uv v8.2.0, cache v5.0.5); uv pinned 0.11.8.

**Steps (test-first via the gate + actionlint):**
- [x] Author `.github/workflows/ci.yml` (two lanes).
- [x] Validate: `actionlint` clean; YAML parses; both lane commands green locally; no creds in the workflow.
- [x] Update `PROGRAM.md` + `ISSUES.md` (CI landed; parity #29 + fixture-guard deferred; protection state).
- [x] PR "Closes #19" (#101); `/review` (3 cross-model findings fixed).
- [x] Branch protection on `main` via a repository ruleset (require a PR + the `ts` + `py` checks; block force-push/deletion).

### Review

- **Done + proven:** `.github/workflows/ci.yml` runs the canonical `turbo run typecheck lint test` as two
  parallel lanes — `ts` (`--filter='!./py/**'`) and `py` (`uv sync --locked` + `--filter='./py/**'`); the
  filters are a complement partition (verified by `--dry`: union = all 5 packages / 8 tasks = `bun run verify`).
  Green in real CI (run 27907919479: `ts` 12s, `py` 20s). `actionlint` clean; zero account-B creds
  (`permissions: contents: read`, no secrets/OIDC). Branch protection applied as ruleset `17947941`.
- **/review fixed 3 cross-model findings:** (1) `turbo.json` `globalDependencies` (`bun.lock`/`uv.lock`/
  `pyproject.toml`/`.python-version`) — without it a persisted `.turbo` cache could replay a stale pass and
  skip the Python checks after a dep bump (false green in a gate); fixes local `bun run verify` too.
  (2) `persist-credentials: false` on checkout. (3) `concurrency` + `cancel-in-progress`.
- **Scoped out (flagged, not faked):** the codegen-parity gate (AC#2) → #29 (blocked-by #27/#28; no
  `contracts/` schema yet); the `fixture-change` guard → activates when `contracts/vectors` (#28) /
  `tools/red-team` (#56) exist. A parity/guard against non-existent paths would be an empty verifier.
- **Surprise:** branch protection (classic AND rulesets) is gated behind a paid GitHub plan on private
  repos; going public is barred by DECISIONS.md §8. Founder upgraded the plan → ruleset applied. Recorded
  as a plan dependency in `ISSUES.md`.
- **Landed:** #101 merged (`009643e`); #19 closed; `main` ruleset-protected.

### Follow-up — xhigh re-review (branch `chore/e0-2-xhigh-review`)

The first `/review` Codex pass ran at `high` (the gstack skill hardcodes `-c model_reasoning_effort=high`,
overriding the repo's `gpt-5.5 xhigh` standard). Re-ran at **xhigh**; added three lessons (incl.
verify-against-official-docs-and-skills, the rule from this episode). Re-examined the three findings
against the **official turbo docs + skill** — none warranted a code change:
- **P1** `infra-local#test` `<NONEXISTENT>` → **non-issue** (E0-3 keeps the LocalStack smoke out of the
  Docker-free gate; typecheck+lint still run; the smoke lives in `localstack-smoke.yml`).
- **P2** `bunx turbo` "could fetch registry turbo" → **moot.** `bun install --frozen-lockfile` guarantees
  turbo is present, so `bunx turbo run` never fetches; turbo's CI rule only requires `turbo run` (which it is).
- **P3** `.turbo` cache "could replay a stale pass" → **already handled.** E0-2's `globalDependencies`
  (`uv.lock`/`pyproject.toml`/`.python-version`; the lockfile is auto-hashed) is turbo's prescribed fix —
  confirmed via `turbo --dry` (all four manifests are in the global hash) and the official caching docs.
  Turbo **recommends** CI caching, so dropping it would be contra-guidance.

Net: the merged E0-2 was already sound + turbo-idiomatic; this follow-up adds only the two lessons.
