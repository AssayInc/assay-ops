# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done. Ephemeral per-session — durable records go to GitHub/PROGRAM.md/DECISIONS.md, not here.

---

## E3-1 (#34) — `diff-ir` package (normalized IR + shared reward core) — DONE, awaiting review (branch `e3-1-diff-ir-package`)

**Goal (3 ACs):** the first `py/packages/diff-ir` — the tool-agnostic normalized IR + the shared reward core [6A].
1. IR tool-agnostic (Terraform now, CDK later) + **round-trips** through the reward core.
2. Reward core consumes **only** {deployed-state read, golden target}; feeding agent `plan`/state is **rejected**.
3. Normalization rules (ordering/defaults/computed fields) **documented** so "no diff" is deterministic.

**Validation (issue vs DECISIONS + brain + skills):** 6A/2A/T1 + `deterministic-verification` +
`write-isolated-verifier` — per-tool adapters do tool-specific normalization of one side; the shared core owns
the determinism-critical diff (won in one place) → `reward∈{0,1}`. DRY: **reuse** the codegen'd
`DiffIR`/`Resource`/`PropertyDiffs`/`Change`/`Reward` from `assayops_contracts`. **Flagged reconciliation:** the
schema *description* says "adapter produces this IR"; AC2 says the **core** consumes {deployed, golden}. The
brain leaves the diff-owner open ("design space; ground in DECISIONS"). Chose: the core produces the `DiffIR`
from two `NormalizedState`s — satisfies AC2 literally, keeps the diff DRY/deterministic in one place, unifies
with `RewardRecord.reportDigest`. Honors 6A. → noted on the issue.

**Design:** `Provenance` (DEPLOYED_READ/GOLDEN_TARGET gradeable; AGENT_PLAN/AGENT_STATE named only to be
rejected) · `NormalizedResource`/`NormalizedState` (frozen Pydantic; unique-address + JSON-domain value
validators) · `grade(deployed, golden) -> GradeOutcome(reward, diff)` — the **only** public reward entry, so
consumption is exactly {deployed, golden}; T1 guard **fails closed** + **re-validates** inputs · tool-agnostic
deterministic diff with **type-strict** value comparison (sort by address + path; golden=expected,
deployed=actual; type-mismatch → reserved `$type` propertyDiff) · `NORMALIZATION.md` (the adapter↔core split +
the determinism + value-representability contract). Report serializes with `exclude_none` (schema-valid sparse).

**Wiring:** first intra-workspace import — diff-ir `pyproject` extends `pythonpath`/`mypy_path` to
`../contracts/src` (all members virtual; in-convention); the `pydantic.mypy` plugin (first hand-written
plain-`BaseModel` under the `Any` ban) + `follow_imports=silent` for the spine. `uv.lock` + `bun.lock` updated.

**Steps:** [x] all — TDD (40 tests, RED→GREEN per behavior); `NORMALIZATION.md` + `README.md`; `bun run verify`
green **20/20** (forced, 0-cached); PROGRAM.md/ISSUES.md updated; focused PR #145 `Closes #34`; cross-model
`/review`; issue comment.

### Review (`bun run verify` green 20/20 forced; 40 tests)

- **Done + proven (3 ACs).** AC1: tool-agnostic (TF + CFN naming) + `DiffIR` round-trip + schema-valid sparse
  dump. AC2: the trust guard (accept {deployed, golden}; reject agent-plan/state/swapped — parametrized). AC3:
  order-independence + K-run determinism + `NORMALIZATION.md`. Each behavior RED-first.
- **Trust boundary (in scope per `write-isolated-verifier`):** the core's only public entry consumes exactly
  {deployed, golden}, fails closed (`UntrustedInputError`) on any other provenance, and **re-validates** its
  inputs — the code-level T1, a complement to (not a replacement for) account-B isolation.
- **Grounded:** DECISIONS 6A/2A/T1; `deterministic-verification`; `write-isolated-verifier`; `pydantic-v2`
  (plugin `Any`-gotcha + `exclude_none`); `uv`; `python-type-safety` (`object` not `Any`);
  `python-testing-patterns`. Brain recall confirmed the diff-owner is open design space → chose the core.
- **Cross-model `/review` (Claude adversarial + test-audit subagents + Codex `gpt-5.5` xhigh, 3 passes) caught
  real reward holes — the value of running both.** Each fixed TDD (RED-first): (1) **false reward 1 via
  value-type collapse** (`True==1`, `1==1.0`) → **type-strict comparison** (bool≠int≠float, recursive); (2)
  **Codex-only: non-string nested dict keys** (`{1:…}`/`{True:…}` collide) → **recursive JSON-domain
  validation**; (3) **scalar *subclasses* with overloaded `__eq__`** pass `isinstance` (Codex pass-2) →
  **exact `type(...)` gate**; (4) **shallow `frozen` bypass** (in-place mutation past the guards; Codex
  reproduced a reward-1) → **`grade` re-validates** inputs; (5) NaN / present-`None` / `$type` guards. +17
  hardening tests. Codex re-reviewed the fixed code at xhigh to convergence.
