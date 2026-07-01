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
- **Comparison: equal iff JCS canonical bytes match.** Two property values are equal **iff their RFC 8785
  (JCS) canonical bytes are identical** — the same canonical form `RewardRecord.reportDigest` is signed
  with, so the grade and the digest can never disagree (the diff can't call "in sync" two values the digest
  would distinguish). The JSON value semantics fall out of JCS instead of being re-derived by hand:
  **`bool` is a JSON boolean distinct from a number** (`True`→`true` ≠ `1`→`1`, so Python's `==`-collapse
  can't forge a reward 1), **one number type** means `90 == 90.0` (treating them distinct would be a
  false-negative drift), object keys are **sorted** (mappings compare key-order-independently), and **lists
  stay order-sensitive** (the adapter sorts order-insensitive collections).
- **Value representability (fail closed): an exact JSON builtin that canonicalizes.** A property value is
  valid **iff it is an exact JSON builtin (recursively) AND canonicalizes under RFC 8785 JCS**;
  `NormalizedResource` guards both at construction. The **exact-type guard comes first and is load-bearing**:
  `rfc8785.dumps` canonicalizes a builtin **subclass** by calling `int()`/`float()`/`list()`/`dict()` on it —
  **user code** — so a subclass could **forge** its canonical bytes (`LyingInt(9).__int__() → 1`
  canonicalizes the value 9 to `b"1"`, a false reward 1) or make them **nondeterministic**. So only exact
  `str`/`int`/`float`/`bool`/`None`/`list`/`dict` (checked `type(x) is T`, never `isinstance`) reach `dumps`;
  a subclass, a **non-JSON type** (set/bytes/object/dataclass), a **non-string object key**, or a
  **reference cycle** (not JSON, and would recurse forever) fails closed. `dumps` then enforces the
  **number domain** — a **non-finite** (NaN/Infinity) or **oversized** (beyond
  JS-safe ±2⁵³) number is not representable in JCS and fails closed. Two AssayOps rules layer on top (JCS
  accepts both): a present top-level **`None`** (absent = omit the key; `exclude_none` can't tell `None` from
  absent) and a **`$`-prefixed key** (reserved — see below). Validation stores the **canonical snapshot**
  (re-parsed from the JCS bytes, so plain exact builtins), decoupling the report from the caller's objects.
  `grade` **re-validates** its inputs from the raw object graph (never `copy.deepcopy`/`model_dump`, whose
  user dunders could launder a non-JSON value past the gate), so a post-construction in-place mutation of a
  properties dict — which `frozen` does not prevent — is caught at the trust boundary.
- **Unique addresses.** A `NormalizedState` rejects duplicate addresses at construction — a duplicate
  would silently collapse in the address map and lose data (a wrong grade). Fail closed.
- **Reserved paths.** `$`-prefixed property paths are reserved by the IR for structural markers. A
  resource-type mismatch at the same address emits a `$type` `propertyDiff`
  (`expected`/`actual` = the two type strings); `$`-prefixed property keys are **rejected** at
  construction so a real property can never collide with a marker.

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
  ingress rules). The core compares values by their **JCS canonical bytes**, which preserve array order —
  only the adapter knows which lists are semantically sets.
- **Make intent-bearing defaults explicit, exclude server-filled metadata.** Do **not** exclude an
  intent-bearing property just because AWS defaults it (encryption, public-access/ACL posture,
  retention, deletion protection) — that would reward the agent for omitting required intent. The golden
  makes the property **explicit** and the adapter reports the deployed value. Exclude only AWS read-only
  server metadata (auto-generated policy-version ids, managed-by tags).

  This is a **corpus-authoring contract**, because a real read returns server-**defaulted** posture the
  deploy never set and the diff is symmetric — a golden omitting a present block grades a *correct*
  deploy reward 0 (the safe direction, but a broken signal). For `AWS::S3::Bucket`, goldens declare all
  four explicitly: `BucketEncryption` (SSE-S3 is every bucket's base encryption),
  `PublicAccessBlockConfiguration` and `OwnershipControls` (`BucketOwnerEnforced`) — both defaulted on
  for new buckets — and `AbacStatus` (`Disabled`; a writable schema property, not readOnly). Before
  authoring corpus tasks of a new type, **pin its golden shape to a real read** — the `infra-local`
  adapter↔golden grade round-trip smoke is that pin (it also catches a nested-shape mismatch, e.g.
  `VersioningConfiguration`). The *defaults* above are AWS-documented facts; the exact read *shape*
  the pin asserts is the pinned LocalStack image's — re-pin it against a real-AWS read when the
  real-cloud read path lands (a shape divergence grades a correct deploy 0: the safe direction,
  never a forge, but a broken signal to fix).

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
