# read-smoke — LocalStack boto3 read-path smoke

The Python/boto3 counterpart to [`infra-local`](../../../infra-local)'s TS `smoke.test.ts`. It proves the
**write-isolated verifier's read path** (`DECISIONS.md` §1): the verifier reads DEPLOYED state read-only via
AWS Cloud Control `get_resource` / `list_resources` — uniform and provisioning-agnostic. The smoke seeds a
known S3 bucket, then reads it back through the **exact** read API the real account-B verifier (E2) uses,
proving LocalStack serves it (the "prove the read API, not 'S3 works'" rule). It is the read-path seed that
grounds the verifier read-coverage spike (#80); it is **not** the verifier itself.

## Scope

- `get_resource` — per-resource state read (`Identifier` + `Properties`).
- `list_resources` — enumerate all resources of a type (paginated).
- `ResourceNotFoundException` — the clean negative-assertion path.

CloudFormation server-side **drift detection** is also part of the verifier read path (`DECISIONS.md` §1),
but LocalStack does **not** serve `DetectStackDrift` ("not currently supported by LocalStack", verified) —
drift-read coverage is the #80/E2 job against real AWS.

## Running

Runs only against a running LocalStack, via the root `just` recipes — never in the hermetic `bun run verify`
gate (the package exposes a `smoke` script, not `test`, exactly like `infra-local`):

    just up         # start LocalStack (needs LOCALSTACK_AUTH_TOKEN; see infra-local/README.md)
    just smoke-py   # this smoke (boto3 / Python — the real verifier read SDK)
    just smoke      # the TS counterpart (kept as a dev convenience)
    just down

`bun run verify` still typechecks (`mypy --strict`) and lints (`ruff`) this package; it just does not
execute the LocalStack-dependent smoke.
