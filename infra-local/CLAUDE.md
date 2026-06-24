# infra-local — boto3 LocalStack read-path smoke

A **Python** (uv) package despite living at the repo root. What it is + why → [`README.md`](./README.md).

- **Never add a `test` script.** The smoke is exposed as `smoke`, not `test`, **by design** — so
  `turbo run test` (`bun run verify`) skips it (LocalStack isn't in the hermetic gate). A `test` script
  would run it there and break CI. Run it via `just smoke` (needs `just up` + `LOCALSTACK_AUTH_TOKEN`).
- It's a `uv` package, so CI routes it to the **`py`** lane (not `ts`) despite living at the repo root.
