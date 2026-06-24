# infra-local — boto3 LocalStack read-path smoke

A **Python** (uv) package despite living at the repo root. What it is + why → [`README.md`](./README.md).

- **Never add a `test` script.** The smoke is exposed as `smoke`, not `test`, **by design** — so
  `turbo run test` (`bun run verify`) skips it (LocalStack isn't in the hermetic gate). A `test` script
  would run it there and break CI. Run it via `just smoke` (needs `just up` + `LOCALSTACK_AUTH_TOKEN`).
- `lint`/`typecheck` run via `uv` (ruff + `mypy --strict`) → CI routes this package to the **`py`** lane,
  not `ts`.
