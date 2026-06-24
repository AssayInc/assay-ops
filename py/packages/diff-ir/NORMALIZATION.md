# Normalization & determinism — the diff-IR contract

Reward 1 = **zero normalized diff** between the read-back deployed state and the independently
regenerated golden target (DECISIONS.md 2A). "Normalized" is load-bearing: read-back state carries
fields that differ across *identical-correct* deployments, and if any reach the diff, the same correct
deploy scores a nonzero diff — a **nondeterministic reward**, which poisons training. An un-normalized
field is a flaky-reward bug, not a cosmetic one.

This document is the contract that makes "no diff" deterministic: what the **adapter** must do (the
tool-specific normalization) versus what the **core** guarantees (the tool-agnostic diff). It mirrors
the `deterministic-verification` skill's checklist; that skill and DECISIONS.md 6A/2A/7A are the source.

## The split: adapter (tool-specific) vs core (tool-agnostic)

- **The per-tool adapter** (Terraform, CDK/CloudFormation, …; separate packages) reads one side and
  emits a `NormalizedState` — a tool-agnostic set of `NormalizedResource`s. **Every tool-specific quirk
  lives here.** The golden-target generator emits the golden side the same way.
- **The core** (`grade`) consumes two `NormalizedState`s and owns only the **tool-agnostic** diff: it
  never inspects which tool produced a side. The determinism-critical comparison lives here **once**, so
  every adapter inherits the same deterministic reward.

## Diff direction & the reward predicate

- **golden = expected**, **deployed = actual.** The `DiffIR` `change` status is *against the golden*:
  - present on both, equal → `unchanged`
  - present on both, different → `modified` (with `propertyDiffs`)
  - in golden, not deployed → `removed` (the deploy is **missing** an expected resource)
  - in deployed, not golden → `added` (the deploy has an **extra** resource)
- **`reward = 1` iff every resource is `unchanged`** — a single `added`/`removed`/`modified` ⇒ `reward = 0`.
  The reward is **binary**; there is no partial-credit / similarity score (that is the gameable
  anti-pattern the project exists to replace).

## What the core guarantees (tool-agnostic)

- **Canonical ordering.** Resources are matched by `address` and emitted **sorted by address**;
  `propertyDiffs` are **sorted by path**. The DiffIR is therefore independent of the order resources or
  properties were supplied in — the same two states always produce the same DiffIR.
- **Structural comparison.** Property values are compared with Python structural equality (`==`), which
  is recursive and key-order-independent for mappings.
- **Unique addresses.** A `NormalizedState` rejects duplicate addresses at construction — a duplicate
  would silently collapse in the address map and lose data (a wrong grade). Fail closed.
- **Reserved paths.** `$`-prefixed property paths are reserved by the IR for structural markers. A
  resource-type mismatch at the same address emits a `$type` `propertyDiff`
  (`expected`/`actual` = the two type strings); normalized property keys must never start with `$`.

## What the adapter must do (tool-specific) — the normalization checklist

Two read-backs of the *same correct* deployment must produce the **same** `NormalizedState`. Before
emitting it, the adapter must:

- **Drop non-intent AWS-assigned identifiers** — the sandbox's own account id, partition/region (where
  not intent), physical resource ids / `*-Id` fields, generated name suffixes (e.g.
  `MyBucket-1ABCD2EFGH3`). Use the resource's **logical** identity for the `address`; resolve
  cross-resource references **structurally** (logical → logical), never by physical id.
- **Keep intent-bearing ARNs/IDs.** An IAM policy `Resource`, a principal / trust target, a KMS key, an
  event target, cross-account wiring — these *define correctness*. Normalize only their *variable*
  segments (partition / region / own-account / generated id); never blanket-drop them, or a permissive
  value (`Resource: *`) would normalize to the golden.
- **Drop timestamps & generation counters** — `CreationDate`, `LastModified`, `VersionId`, `ETag`,
  drift `LastCheckTimestamp`.
- **Sort order-insensitive collections** *within* a property value (tag sets, policy statements,
  ingress rules). The core compares values with `==`, which is order-sensitive for lists — only the
  adapter knows which lists are semantically sets.
- **Make intent-bearing defaults explicit, exclude server-filled metadata.** Do **not** exclude an
  intent-bearing property just because AWS defaults it (encryption, public-access/ACL posture,
  retention, deletion protection) — that would reward the agent for omitting required intent. The golden
  makes the property **explicit** and the adapter reports the deployed value. Exclude only AWS read-only
  server metadata (auto-generated policy-version ids, managed-by tags).

Rule of thumb: if a field can differ between two runs of the same correct deploy, it must not appear in
the `NormalizedState`.

## Serialization of the diff report

The `DiffIR` is the **diff report**; its SHA-256 is `RewardRecord.reportDigest` (the reward ledger, E4).
Serialize it with **`model_dump(mode="json", exclude_none=True)`** — the schema-valid sparse form:
omitted optionals are dropped, so a non-modified resource has **no** `propertyDiffs` key (never
`propertyDiffs: null`, which the JSON Schema rejects), and a one-sided property diff dumps only its
present side. Canonicalization for the signature (RFC 8785 JCS) is the ledger's job; this is the
JSON-safe, schema-valid dict that feeds it.

## Determinism boundary

The core is deterministic **in process**: same inputs → identical reward + DiffIR, every run. The
**live-cloud** determinism — transient vs genuine failure classification, eventual consistency, the
golden-×K reproduce / quarantine of flaky tasks (DECISIONS.md 7A) — is the verifier read harness's job
(the deterministic-verification skill), upstream of this pure core.
