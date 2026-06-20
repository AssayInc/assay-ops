# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## E0-3 (#20) — LocalStack dev loop via `just up` — IN PROGRESS (branch `feat/localstack-dev-loop`)

**Goal (AC, revised):** `infra-local/docker-compose` brings LocalStack up via `just up`; a smoke test
issues a Cloud Control `GetResource` and reads a known resource. **No real AWS; licensed LocalStack**
(`LOCALSTACK_AUTH_TOKEN` as a CI/local secret); runs in CI.

**Resolved blocker — LocalStack licensing (founder decision = keep LocalStack):**
- The free tokenless community edition was retired in the **2026-03-23 single-image change**; current
  `localstack/localstack` requires `LOCALSTACK_AUTH_TOKEN` (empirically: exits 55 without one).
- Free Cloud-Control-capable alternatives don't exist: moto has no Cloud Control; Floci + MiniStack
  empirically 404 on `GetResource` (S3 create passes). The verifier (T1) grades the Cloud Control read
  path, so LocalStack is the only fit. AC changed "cost-free" -> "no real AWS; licensed LocalStack."
- Recorded: #20 AC, DECISIONS.md substrate qualifier, ISSUES.md follow-up (license + CI secret).

**Wiring (keeps `bun run verify` Docker-free):**
- `infra-local/` workspace member: `typecheck` + `lint` + `smoke` (NO `test`), so `verify` lints/typechecks
  the smoke but never runs it. Image pinned by digest; `LOCALSTACK_AUTH_TOKEN` via env or gitignored `.env`.
- Smoke (`infra-local/smoke.test.ts`): seed S3 bucket (`@aws-sdk/client-s3`), read via
  `@aws-sdk/client-cloudcontrol` `GetResource` (`AWS::S3::Bucket`). The E2 verifier read pattern, minimal.

**Env:** Docker UP · LocalStack CLI 2026.5.4 · `just` 1.53.0 · image pulled · **token: NOT yet set (blocks proof).**

**Steps (TDD):**
- [x] Branch `feat/localstack-dev-loop`; pin image by digest.
- [x] Author `infra-local/{docker-compose.yml,package.json,tsconfig.json,smoke.test.ts}` + `justfile`;
      `infra-local` in workspaces; `infra-local/**` in biome includes.
- [x] `bun add --exact @aws-sdk/client-s3 @aws-sdk/client-cloudcontrol` (3.1073.0); lockfile updated.
- [x] Rework for licensed LocalStack: compose token, `just up` token-load, `.env.example`, AC, DECISIONS.md, ISSUES.md.
- [ ] **BLOCKED on token:** user adds `LOCALSTACK_AUTH_TOKEN` to `.env` -> `just up` healthy -> `just smoke` GREEN.
- [ ] `bun run verify` green + Docker-free.
- [ ] `.github/workflows/localstack-smoke.yml` (`secrets.LOCALSTACK_AUTH_TOKEN`; pinned action SHAs).
- [ ] PR "Closes #20"; `/review`; user adds the `LOCALSTACK_AUTH_TOKEN` GH secret; watch CI green; update `PROGRAM.md`.

### Review

- **Done + proven:** `just up` (licensed LocalStack 2026.5.4 activates + healthy), `just smoke` GREEN
  (Cloud Control `GetResource` reads a seeded S3 bucket — the T1 verifier read path), `just down`/`logs`,
  `bun run verify` green + Docker-free (smoke typechecked/linted, never executed). Full down→up→smoke→down
  cycle re-verified after fixing the down/logs token-interpolation bug (compose `:?` → `:-`; `up` enforces).
- **Pivot:** LocalStack retired its free tokenless community edition (2026-03-23 single image); free
  alternatives (moto/Floci/MiniStack) empirically don't serve Cloud Control `GetResource`. Founder chose
  licensed LocalStack; AC changed cost-free → no-real-AWS/licensed; recorded in #20 + DECISIONS.md + ISSUES.md.
- **CI:** `.github/workflows/localstack-smoke.yml` (pinned action SHAs, path-scoped). Needs the human to add
  the `LOCALSTACK_AUTH_TOKEN` GH **CI auth token** secret before the smoke job goes green.
- **Left:** open PR "Closes #20" + `/review`; user adds the GH secret; then merge. Remaining E0 eng: #19, #21.
