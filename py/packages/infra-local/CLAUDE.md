# infra-local — boto3 LocalStack read-path smoke

A **Python** (uv) package: the LocalStack dev-loop smoke for the verifier's Cloud Control read path. What it is + why → [`README.md`](./README.md).

- **Never add a `test` script.** Unlike its `py/packages/*` siblings, this package exposes the smoke as
  `smoke`, **not** `test`, **by design** — so `turbo run test` (`bun run verify`) skips it (LocalStack
  isn't in the hermetic gate). A `test` script would run it there and break CI. Run it via `just smoke`
  (needs `just up` + `LOCALSTACK_AUTH_TOKEN`).
