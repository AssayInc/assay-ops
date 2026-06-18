# assay-ops

AssayOps core monorepo: the proprietary IP (write-isolated verifier, OpenEnv env-server, IaC
adapters, reward ledger) in **TypeScript**, plus the **Python** trainer/eval, bridged by one
codegen'd contract schema. Polyglot by design — **Bun + Turborepo** (TS) and **UV** (Python),
with a single `verify` gate spanning both lanes.

## Start here

- **[`DECISIONS.md`](./DECISIONS.md)** — the frozen floor: the locked decisions, the trust model,
  and the threat bar. Read this before touching code.
- **[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)** — the structural map: where each package
  lives and how an episode flows (env-server → verifier → reward ledger → trainer).

## Setup

```sh
bun install && uv sync     # TS deps (Bun) + Python env (UV); or: bun run setup
```

## Verify (the single gate)

```sh
bun run verify             # turbo run typecheck lint test, across the TS + Python lanes
```
