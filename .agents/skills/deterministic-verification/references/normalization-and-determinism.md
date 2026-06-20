# Normalization & determinism — the details

API-level detail for `SKILL.md`. Load this when you're actually writing an adapter, the reward core,
or the determinism check. The AWS read-API *shapes* (Cloud Control `GetResource`/`ListResources`,
CloudFormation `DescribeStackResources` + drift detection) live in the **write-isolated-verifier**
skill's `references/grading-primitives.md` — this file is the determinism layer on top. Grounded in
official AWS docs + the brain (`[[concepts/deterministic-verification]]`, `[[references/nsync]]`,
`[[concepts/retries-and-backoff]]` — read via **assay-brain**).

- [Normalization checklist](#normalization-checklist)
- [Transient vs genuine — fail open or closed?](#transient-vs-genuine--fail-open-or-closed)
- [K-run reproduce & quarantine](#k-run-reproduce--quarantine)
- [Conformance fixtures](#conformance-fixtures)

## Normalization checklist

The IR must be **canonical**: two read-backs of the same correct deployment must produce
byte-identical IR. Before diffing against the golden, normalize away everything that varies across
identical-correct deployments:

- **Non-intent AWS-assigned identifiers** — the sandbox's own account id, partition/region (where not
  intent), physical resource IDs / `*-Id` fields (VPC/Subnet/ENI/SG ids), generated name suffixes (e.g.
  CloudFormation's `MyBucket-1ABCD2EFGH3`). Placeholder these keyed by the resource's **logical**
  identity, and resolve cross-resource references **structurally** (logical-id → logical-id), never by
  physical id.
- **Intent-bearing ARNs/IDs — do NOT drop.** An IAM policy `Resource`, a principal / trust-policy
  target, a KMS key/alias, an event target, or cross-account wiring *defines correctness* — blanket
  dropping lets a permissive or wrong value (`Resource: *` vs a specific ARN) normalize to the golden.
  Normalize only the *variable* segments (partition / region / own-account / generated id); preserve
  service, resource type, path, and the logical target.
- **Timestamps & generation counters** — `CreationDate`, `LastModified`, `VersionId`, `ETag`, drift
  `LastCheckTimestamp`. Drop.
- **Ordering** — sort every collection by a stable key (tags, statements, list-valued properties,
  paginated results). JSON object keys too if you compare serialized form.
- **Server-filled metadata only** — exclude AWS read-only/server metadata (auto-generated policy
  version ids, managed-by tags). **Do NOT exclude intent-bearing properties** just because AWS defaults
  them — encryption, public-access/ACL posture, retention, deletion protection. Drift doesn't track a
  property unless it's explicitly set, so excluding these would **reward an agent for omitting required
  intent**. If the task intent includes a property, the golden makes it **explicit** and the adapter
  **verifies** the deployed value.
- **Compare intent-bearing properties only** — validate the read-back against the **CloudFormation
  resource specification** (typed catalog: which properties are `Required`, their types,
  `Mutable`/`Immutable`) so the diff is over the properties that define correctness
  (`RetentionInDays: 90`, encryption on, least-privilege policy), not incidental metadata.

Rule of thumb: if a field can differ between two runs of the *same correct* `cdk deploy`, it must not
appear in the diff. An un-normalized field is a flaky-reward bug.

## Transient vs genuine — fail open or closed?

Two different failure classes need **opposite** handling, and conflating them breaks determinism:

- **Transient (retry, don't score 0).** `ThrottlingException`, `RequestLimitExceeded`,
  `TooManyRequestsException`, 5xx, connection resets, the Cloud Control temporary classes
  (`ResourceConflictException`, `NetworkFailureException`, `ServiceInternalErrorException`,
  `NotStabilizedException`), and **eventual consistency** (a just-created IAM role/policy or S3 object
  not yet visible; drift detection not yet `DETECTION_COMPLETE`). These are *grading-harness* hiccups,
  not wrong answers. Retry with exponential backoff + jitter; use idempotent reads; wait for
  propagation/`DETECTION_COMPLETE` before reading the result. Scoring these 0 is a **false-negative reward**.
- **Genuine (a settled mismatch → reward 0).** After retries/propagation settle: the resource is
  absent, a property mismatches the golden, the stack is `DRIFTED` (stack statuses:
  `DRIFTED`/`IN_SYNC`/`UNKNOWN`/`NOT_CHECKED`), or a resource is `MODIFIED`/`DELETED`. That is the real grade.
- **Hard wall (surface, don't retry).** `AccessDeniedException` is the boundary firing
  (`write-isolated-verifier`), not a transient — surface it; don't retry-loop through it.

The asymmetry: **fail-open on transients** (retry, never a spurious 0) but **fail-closed on coverage**
(a resource you can't read after settling is non-passing, not assumed-fine — see the read-side
coverage rule in `write-isolated-verifier`).

## K-run reproduce & quarantine

- **Determinism check:** grade the golden K times (default K per the determinism policy) → the reward
  must be **identical** every run. Also re-grade a fixed deployed state K times → identical IR.
- **Variance ⇒ investigate, then quarantine.** If the reward varies after transient handling, the
  cause is usually un-normalized fields (fix normalization) or an inherently fuzzy signal (incident
  health, cost). A task that stays flaky after K-run is **quarantined** out of the scored corpus — it
  never ships a reward into training.
- This is decision **7A** (transient/genuine classifier + K-run reproduce + quarantine); recall the
  rationale via **assay-brain** (`[[projects/assay/eng-architecture]]`).

## Conformance fixtures

Lock the adapter + normalization so a refactor can't silently change a reward:

- **Per-adapter fixture:** a captured deployed-state read → the expected normalized IR → the expected
  reward. Same input ⇒ same IR ⇒ same reward, asserted in CI.
- **Cross-deploy fixture:** two *different* read-backs of the same correct deployment (different ARNs,
  timestamps, order) → the **same** normalized IR (proves normalization is complete).
- **Negative fixture:** a genuinely-wrong deployment → reward 0 over the right property, not over
  incidental metadata.
