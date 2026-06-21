# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## E0-4 (#21) — Repo hygiene (CODEOWNERS, PR template, secret scanning, CONTRIBUTING) — IN PR (branch `chore/e0-4-repo-hygiene`)

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
- [ ] Prove: a planted (fabricated) secret is blocked on push.
- [ ] Update `PROGRAM.md` + `ISSUES.md`; PR "Closes #21"; `/review`.

### Review

_(added on completion)_

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
