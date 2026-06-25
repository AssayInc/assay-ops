# iam-readiness-probe — real-AWS IAM eventual-consistency probe

A **Python** (uv) measurement tool. What it is + why + the baseline result → [`README.md`](./README.md).

- **MUTATES real AWS.** It creates/deletes IAM roles + inline policies and assumes them in the target
  account. Run only against a **throwaway/dev** account (`--profile`), never prod or an Orgs-pool account.
- **Never add a `test` script.** Like `infra-local`, this exposes its run as `probe`, **not** `test`, so
  `turbo run test` (`bun run verify`) skips it — real AWS is not in the hermetic gate. `lint`/`typecheck`
  still cover the code. Run via `bun run --filter @assayops/iam-readiness-probe probe -- --profile ...`.
