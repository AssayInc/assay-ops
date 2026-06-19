# AssayOps — ARCHITECTURE (the structural map: *how / where*)

> **How vs. why.** This file is **how / where** — the package layout, the build wiring, and the
> episode data-flow. For **why / rules** — the trust model, the locked decisions, the threat bar —
> read **[`DECISIONS.md`](../DECISIONS.md)**. The trust model lives there and is **not** duplicated
> here; this file points to it.

`assay-ops` is the core monorepo: the proprietary IP in **TypeScript** (write-isolated verifier,
OpenEnv env-server, IaC adapters, reward ledger) plus the **Python** trainer/eval, bridged by **one
codegen'd contract schema** ([`DECISIONS.md` §2, decision 5A](../DECISIONS.md#2-locked-architecture-decisions-1ct3)).
The split is polyglot by design ([I1, I2](../DECISIONS.md#4-implementation-decisions-i1i11)).

## Build & toolchain (how the lanes run)

- **TS lane** — Bun + Turborepo + Biome. Shared config lives in `ts/packages/typescript-config`
  (tsconfig `base`/`bun`) and `ts/packages/biome-config` (lint/format). Per package: `typecheck`
  = `tsc --noEmit`, `lint` = `biome lint .`, `test` = `bun test`.
- **Python lane** — a **UV** workspace, **orchestrated by Turbo** via a thin `package.json` wrapper
  in each Python package whose scripts shell out to `uv run` (decision **I2** / `vercel/turborepo#1077`).
  UV owns Python deps + the shared `.venv`; Turbo owns the one task graph. Per package: `typecheck`
  = `mypy`, `lint` = `ruff check`, `test` = `pytest`. *(ruff/mypy/pytest are E0-1 `[impl]` defaults,
  not a locked decision — swap freely.)*
- **One gate:** `bun run verify` → `turbo run typecheck lint test` across **both** lanes.
- **Setup:** `bun install && uv sync` (or `bun run setup`). Lockfiles `bun.lock` + `uv.lock` are
  committed. Generated contract artifacts (TS + Pydantic) will be committed in E1, so neither lane needs
  the other's toolchain to build ([I2, I3](../DECISIONS.md#4-implementation-decisions-i1i11)).

## Repository layout (target map; status per item)

Legend: **✅ scaffolded in E0-1** · **◻ added by the named epic** (mapping: [`DECISIONS.md` §3](../DECISIONS.md#3-locked-tasks-t1t13--epic-mapping)).

```
assay-ops/
├─ DECISIONS.md ............... ✅ the frozen floor — why/rules, the trust model, the 15-vector bar
├─ docs/ARCHITECTURE.md ....... ✅ this file — how/where
├─ package.json turbo.json .... ✅ root TS tooling: Bun workspaces + the `verify` task graph
├─ biome.json ................. ✅ root Biome lint/format config
├─ pyproject.toml ............. ✅ UV workspace ([tool.uv.workspace]) + dev tools (ruff/mypy/pytest)
├─ .python-version ........... ✅ pins the Python interpreter (3.12) for uv + CI
├─ bun.lock uv.lock ........... ✅ committed lockfiles (both lanes)
│
├─ contracts/ ................. ◻ E1 — THE SPINE: JSON Schema (Draft 2020-12) source of truth [5A/I3]
│  ├─ schemas/ ................ ◻ reward-record · trajectory · diff-ir · task-spec
│  ├─ vectors/ ................ ◻ golden JCS byte-parity fixtures — fixture-change only (#28)
│  └─ codegen.config .......... ◻ quicktype (TS) + datamodel-code-generator (Pydantic v2)
│
├─ ts/                          # ── Bun + Turborepo ──────────────────────────────────
│  ├─ packages/
│  │  ├─ typescript-config/ ... ✅ shared tsconfig (base + bun)
│  │  ├─ biome-config/ ........ ✅ shared lint/format
│  │  ├─ contracts/ ........... ✅ shell → ◻ E1 generated TS types (quicktype) + JCS canonicalize
│  │  ├─ diff-ir/ ............. ◻ E3 normalized diff IR + shared reward core [6A]
│  │  ├─ adapter-terraform/ ... ◻ E3 Terraform → diff IR (the A-spike engine) [T2]
│  │  ├─ adapter-cdk/ ......... ◻ E3 CDK adapter [T3]
│  │  ├─ verifier/ ............ ◻ E2 write-isolated verifier core (account B, read-only) [T1]
│  │  ├─ reward-ledger/ ....... ◻ E4 KMS-sign + S3 Object Lock (WORM), trajectory-keyed [T4]
│  │  ├─ replay/ .............. ◻ E6 deterministic replay + flaky-task quarantine [T8]
│  │  ├─ env-server/ .......... ◻ E5 OpenEnv-compatible TS HTTP/WS server [I5]
│  │  └─ orchestrator/ ........ ◻ E7 direct orchestration; Harbor slot for Phase-2 [T12]
│  └─ apps/
│     └─ assayctl/ ............ ◻ E7 dev CLI (run episode, grade, replay, red-team)
│
├─ py/                          # ── UV workspace (each pkg: thin package.json wrapper → uv) ──
│  └─ packages/
│     ├─ contracts/ ........... ✅ shell → ◻ E1 generated Pydantic v2 + rfc8785 canonicalize
│     ├─ trainer/ ............. ◻ E12 SFT pipeline (TRL v1.0 + LoRA) [I6]
│     └─ evals/ ............... ◻ E13 Inspect AI harness (deploy-verifier as Scorer) [T11]
│
├─ tasks/ ..................... ◻ E11 CDK drift&debug task SPECS [T13]; gold corpus + held-out eval
│                                  live in a PRIVATE data store, never committed [I11]
├─ infra-local/ .............. ◻ E0-3 LocalStack docker-compose (`just up`)
├─ tools/red-team/ ........... ◻ E10 the 15-vector attack suite — fixture-change only (#56) [T10]
└─ .github/workflows/ci.yml .. ◻ E0-2 two independent cache-keyed lanes (turbo / uv)
```

> **Layout note — `ts/` + `py/`, not `apps/` + `packages/`.** Split by **language** at the top level so
> each workspace manager and linter has an unambiguous scope (Bun/Biome own `ts/**`; UV/ruff/mypy own
> `py/**`); the app-vs-library split is preserved *under* `ts/` (`ts/apps/*`, `ts/packages/*`). Per
> Turborepo's directory-grouping support: single-level globs only (`ts/packages/*`, never `**`), and no
> `package.json` at the grouping dirs.

The AI-operating layer (`CLAUDE.md`/`AGENTS.md`, `PROGRAM.md`, `ISSUES.md`, `tasks/{todo,lessons}.md`)
and the `assay-brain` skill arrive in **E0-6 (#18)** and **E0-7 (#73)**.

## The contract-schema spine (codegen)

Built **first** (E1) — it is the join key for the whole system and the thing a buying lab can
independently verify:

```
contracts/schemas/*.schema.json   (one neutral source of truth, neither language owns it)
        │ quicktype                              │ datamodel-code-generator
        ▼                                        ▼
ts/packages/contracts  (TS types + JCS)   py/packages/contracts  (Pydantic v2 + rfc8785)
```

Generated artifacts on both sides are **committed**, regenerated by a root **`just codegen`** task both
lanes depend on. **Schema-modeling rules (JCS-forced):** model large IDs / nonces / ns-timestamps as
**strings** (JCS numbers must fit IEEE-754; ints > 2^53−1 lose precision), rewards as **bounded
doubles**, and **reject NaN/Infinity** — violating these silently breaks the byte-parity gate that
[`DECISIONS.md` §8](../DECISIONS.md#8-agent-non-negotiables-checklist) makes non-negotiable. **CI parity
gate:** regenerate from `contracts/schemas`, assert no diff vs the committed artifacts, and check the
golden-vector sha256 in **both** lanes. Why JSON Schema + RFC 8785 JCS (not Protobuf) and the signing
flow are in [`DECISIONS.md` I3 / 4B](../DECISIONS.md#4-implementation-decisions-i1i11).

## Episode data-flow (how a graded episode moves through the packages)

A structural view of the runtime path. **The trust boundary — account A vs B, why the verifier
never runs the agent's `synth`/`plan` — is in [`DECISIONS.md` §1](../DECISIONS.md#1-trust-model-the-moat-in-one-diagram--the-rule-that-defines-the-product)** and is not restated here.

```
  agent (policy) ⇄ env-server [E5]          # OpenEnv HTTP/WS; agent deploys IaC,
        │                                   # its synth/plan runs A-side as untrusted data
        ▼
  DEPLOYED cloud resource state
        │  cross-account, READ-ONLY
        ▼
  verifier [E2] ── adapter [E3] → diff IR [E3] → reward ∈ {0,1} + diff report
        │
        ▼
  reward-ledger [E4]   # KMS-signed, S3 Object Lock (WORM), keyed by trajectory_id, in account B
        │  read-only signed records
        ▼
  py/trainer [E12] · py/evals [E13]         # join on trajectory_id; SFT + the lift proof
```

Determinism + deterministic replay ([E6, T8]) wrap the episode so a trajectory regrades to an
identical reward. The headline proof is a lift on an OOD slice — eval rigor is in
[`DECISIONS.md` §6](../DECISIONS.md#6-eval-rigor-the-proof-must-clear-this-bar).

## How to navigate

- **Read order:** [`DECISIONS.md`](../DECISIONS.md) (rules) → this file (layout).
- **Add a TS package:** `ts/packages/<name>/` with `package.json` (extend the shared configs via
  `workspace:*`, add `typecheck`/`lint`/`test` scripts) + `tsconfig.json` extending
  `@assayops/typescript-config/bun.json`. Turbo picks it up via the `ts/packages/*` workspace glob.
- **Add a Python package:** `py/packages/<name>/` with a `pyproject.toml` *and* a thin `package.json`
  whose `typecheck`/`lint`/`test` scripts call `uv run` — that wrapper is what lets the one Turbo
  graph drive the Python lane (I2). Add it to nothing else; `[tool.uv.workspace]` + the
  `py/packages/*` glob pick it up.
- **The gate is `bun run verify`.** Every *source* package wires `typecheck`/`lint`/`test` (the
  config-only packages — `typescript-config`, `biome-config` — export config and have no gate tasks);
  CI (E0-2) runs
  the same gate.
- **Locked fixtures:** `contracts/vectors` (#28) and `tools/red-team` (#56) change **only** in
  `fixture-change` PRs — see [`DECISIONS.md` §8](../DECISIONS.md#8-agent-non-negotiables-checklist).
