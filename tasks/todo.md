# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

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
- [ ] Author `.github/workflows/ci.yml` (two lanes).
- [ ] Validate: `actionlint` clean; YAML parses; both lane commands green locally; no creds in the workflow.
- [ ] Update `PROGRAM.md` + `ISSUES.md` (CI landed; parity #29 + fixture-guard deferred; protection state).
- [ ] PR "Closes #19"; `/review`.
- [ ] Branch protection on `main` via `gh api` once `ci` is green (require a PR + the `ts` + `py` checks).

### Review

_(filled on completion)_
