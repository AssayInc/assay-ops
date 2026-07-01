# assay-ops

AssayOps core monorepo: the **Python** proof-critical IP (write-isolated verifier, OpenEnv env-server,
IaC adapters, reward ledger) plus the **Python** trainer/eval — one Python core — with **TypeScript**
for the public/web surface (`@assayops/contracts`, `assay-web`), bridged by one codegen'd contract
schema. Python core, TS at the edge — **UV** (Python) + **Bun + Turborepo** (TS), with a single
`verify` gate spanning both lanes.

## Start here

- **[`DECISIONS.md`](./DECISIONS.md)** — the frozen floor: the locked decisions, the trust model,
  and the threat bar. Read this before touching code.
- **[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)** — the structural map: where each package
  lives and how an episode flows (env-server → verifier → reward ledger → trainer).

## Get started

**Prerequisites** (install once):

| Tool | Install (macOS) | Used for |
|------|-----------------|----------|
| [Docker](https://docs.docker.com/get-docker/) | Docker Desktop, or `brew install colima && colima start` | the LocalStack dev loop (any container runtime works) |
| [Bun](https://bun.sh) | `brew install oven-sh/bun/bun` | the TypeScript lane (runtime + package manager, pinned `1.3.14`) |
| [uv](https://docs.astral.sh/uv/) | `brew install uv` | the Python lane |
| [just](https://just.systems) | `brew install just` | the task runner for the dev loop |

Install dependencies and run the gate:

```sh
bun run setup     # TS deps (Bun) + Python env (UV) — = bun install && uv sync
bun run verify    # the single gate: turbo run typecheck lint test, both lanes
```

### Local dev loop (LocalStack)

The verifier grades against a local LocalStack instead of real AWS. Put a LocalStack token in a
gitignored `.env` at the repo root (free Hobby tier — create one at app.localstack.cloud, Auth Tokens):

```sh
# .env
LOCALSTACK_AUTH_TOKEN=<your token>
```

Then:

```sh
just up      # start LocalStack and wait for it to report healthy
just smoke   # Cloud Control read smoke + the adapter↔golden grade round-trip
just down    # stop LocalStack and remove its volumes
```

Details: [`py/packages/infra-local/README.md`](./py/packages/infra-local/README.md). Why licensed LocalStack: [`DECISIONS.md`](./DECISIONS.md).
