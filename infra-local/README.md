# infra-local — LocalStack dev loop

In development the verifier reads against a local [LocalStack](https://localstack.cloud) stack instead of
real AWS. This is the seed of the verifier's read path: the smoke test issues a Cloud Control `GetResource`
against deployed state, exactly as the cross-account verifier does in production (DECISIONS.md section 1).

## Recipes (`just`)

- `just up` — start LocalStack and wait for the gateway (http://localhost:4566) to report healthy
- `just smoke` — seed an S3 bucket and read it back via Cloud Control `GetResource`
- `just down` — stop LocalStack and remove its volumes
- `just logs` — follow LocalStack logs

## Auth token (required)

LocalStack for AWS is a licensed single image (the free tokenless community edition was retired in the
2026-03-23 single-image change), so `just up` needs `LOCALSTACK_AUTH_TOKEN`. Put it in a gitignored `.env`
at the repo root (never commit the value):

    LOCALSTACK_AUTH_TOKEN=<your token>

Get a token from your LocalStack workspace (app.localstack.cloud, Auth Tokens; a CI auth token for CI).
Commercial, private use needs a paid plan, not the non-commercial Hobby/OSS tiers. Why LocalStack (rather
than moto / Floci / MiniStack, which do not serve the Cloud Control read path) is recorded in DECISIONS.md.

## CI

`.github/workflows/localstack-smoke.yml` runs the same `just up` / `just smoke` against LocalStack using a
`LOCALSTACK_AUTH_TOKEN` repo secret. The smoke is not part of `bun run verify` (the hermetic gate stays
Docker-free); it runs as its own job.
