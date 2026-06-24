# infra-local — LocalStack dev loop

In development the verifier reads against a local [LocalStack](https://localstack.cloud) stack instead of
real AWS. The smoke (`tests/test_localstack_read_smoke.py`) seeds a known S3 bucket, then reads it back via
**boto3** Cloud Control `get_resource` / `list_resources` — the **exact** read API the cross-account
account-B verifier uses in production (`DECISIONS.md` §1). It is boto3/Python because the verifier read path
is boto3/Python (E17 — re-homed from the original TS smoke); it grounds the verifier read-coverage spike
(#80) and is **not** the verifier itself.

## Why this exists (it is NOT a boto3 test)

boto3 is reliable — testing AWS's SDK would be pointless. The uncertain thing worth guarding is
**LocalStack's fidelity for the verifier's *exact* read path**: does our dev/CI substrate genuinely serve
Cloud Control `get_resource`/`list_resources` (and surface a missing resource correctly), or only
"AWS-ish things"? That is a real risk:

- **LocalStack read-API fidelity is an open question** in the research, and `DECISIONS.md` **R3** names
  "LocalStack fidelity too low to be lab-credible" as a kill-risk.
- **"S3 works" ≠ "the read path works."** Floci and MiniStack pass a generic S3 smoke yet **fail** Cloud
  Control `GetResource`; moto and the others simply don't serve the Cloud Control read path. An emulator that
  looks fine generically does not imply it serves the verifier's read path — which is why this smoke reads
  via Cloud Control *specifically*, not just by creating a bucket.
- **It is a regression canary on the pinned image.** When `docker-compose.yml` bumps the LocalStack digest,
  the smoke catches a dropped or broken Cloud Control read **before** it silently breaks verifier dev
  (#80/E2). It has already paid off — it is how we learned LocalStack does not serve `DetectStackDrift`.

Secondary value: it is the **read-path contract for #80** (the exact boto3 call shapes the real verifier
reuses, in working code) and a **fast dev loop** — `just up && just smoke` confirms a dev's LocalStack
serves the read path before building on it.

## Scope

- `get_resource` — per-resource state read (`Identifier` + `Properties`).
- `list_resources` — enumerate all resources of a type (paginated).
- `ResourceNotFoundException` — the clean negative-assertion path.

CloudFormation server-side **drift detection** is also part of the verifier read path (`DECISIONS.md` §1),
but LocalStack does **not** serve `DetectStackDrift` ("not currently supported by LocalStack", verified) —
drift-read coverage is the #80/E2 job against real AWS. Cold-start transients (a service warming after the
gateway reports healthy) are covered by botocore's own bounded retries, not a hand-rolled loop.

## Recipes (`just`)

- `just up` — start LocalStack and wait for the gateway (http://localhost:4566) to report healthy
- `just smoke` — seed an S3 bucket and read it back via Cloud Control `get_resource` / `list_resources` (boto3)
- `just down` — stop LocalStack and remove its volumes
- `just logs` — follow LocalStack logs

## Auth token (required)

LocalStack for AWS is a licensed single image (the free tokenless community edition was retired in the
2026-03-23 single-image change), so `just up` needs `LOCALSTACK_AUTH_TOKEN`. Put it in a gitignored `.env`
at the repo root (never commit the value):

    LOCALSTACK_AUTH_TOKEN=<your token>

Get a token from your LocalStack workspace (app.localstack.cloud, Auth Tokens; a CI auth token for CI).
Commercial, private use needs a paid plan, not the non-commercial Hobby/OSS tiers. Why LocalStack rather
than a free emulator (see *Why this exists* above) is recorded in DECISIONS.md.

## CI

`.github/workflows/localstack-smoke.yml` runs `just up` / `just smoke` against LocalStack using a
`LOCALSTACK_AUTH_TOKEN` repo secret. The smoke is **not** part of `bun run verify` (the hermetic gate stays
Docker-free) — the package exposes a `smoke` script, not `test`, so `turbo run test` skips it while `ruff`
+ `mypy --strict` still lint and typecheck it. It runs as its own job.
