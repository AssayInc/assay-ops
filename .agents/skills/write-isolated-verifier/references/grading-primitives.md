# Grading primitives — the read & write substrate

API-level detail for the rules in `SKILL.md`. Load this when you're actually wiring an adapter, the
reward core, or the ledger. Distilled from the brain (`[[concepts/iac-verification-primitives]]`,
`[[concepts/write-isolated-verifier]]`) — read those via **assay-brain** for the full rationale.

- [Read side — grade deployed state](#read-side--grade-deployed-state)
- [Write side — store the reward](#write-side--store-the-reward)
- [Consistency & determinism traps](#consistency--determinism-traps)

## Read side — grade deployed state

The agent deploys; the verifier reads **observed reality** through read-only APIs and asserts it
matches the independently regenerated golden. Never `cdk synth` / `cdk diff` / `terraform plan` —
those run the agent's code and grade its *self-report* of desired state, not the world.

### 1. Cloud Control API — uniform per-resource read

One API shape across the resource types Cloud Control **supports** (a large but finite registry — not
literally every AWS type, and some types don't support every operation), so the verifier needs no
per-service client code for them (a 30-resource grade is N calls of the same shape). **Fail closed:**
if an expected resource's type isn't readable via Cloud Control, fall back to a service-specific read
or mark it non-passing — never silently skip state you can't read (a skip is a read-side coverage gap
the agent can exploit).

- **`GetResource(TypeName, Identifier)`** → current state as a `ResourceModel` JSON blob of live
  properties. The atomic assertion: *does resource X exist, and do its properties match spec?*
  (e.g. `RetentionInDays: 90`, bucket encrypted, policy least-privilege). Returns state "whether or
  not the resource was provisioned using Cloud Control API" — it reads reality, not a tool's intent.
- **`ListResources(TypeName)`** → enumerate all resources of a type in the account/Region (paginate
  via `NextToken`). Discovery: count them, confirm none left behind or over-provisioned.
- **`RoleArn`** (optional) → a *same-account* CloudFormation **service role (assumed by
  `cloudformation.amazonaws.com`) to perform the operation** (absent one, it uses the caller's credentials); it scopes downstream permissions,
  **not** the account read. **Cross-account** read-only reads use **STS `AssumeRole` into a read-only
  role in the target account** → temp creds → sign the call; the **target account is set by the
  signing credentials**.

### 2. CloudFormation `DescribeStackResources` — stack manifest

For CFN/CDK deployments (CDK compiles to a stack). Returns each member's `LogicalResourceId`,
`PhysicalResourceId`, `ResourceType`, `ResourceStatus` (e.g. `CREATE_COMPLETE`). The **manifest
check**: did the stack converge, is every expected logical resource present and `*_COMPLETE`?
(`ListStackResources` paginates for >100 resources.) Resource info survives **up to 90 days after
stack deletion** — useful for post-episode forensics.

### 3. Drift detection — declared vs live, computed server-side

The sharpest primitive for **drift & debug** tasks. CloudFormation computes the diff for you — the
grader synthesizes nothing.

- `detect-stack-drift` → `StackDriftDetectionId` (async, long-running, one-at-a-time per stack).
- `describe-stack-drift-detection-status` → poll to `DetectionStatus: DETECTION_COMPLETE`; yields
  `StackDriftStatus` (`DRIFTED` / `IN_SYNC`) + `DriftedStackResourceCount`.
- `describe-stack-resource-drifts` → per-resource detail: `ExpectedProperties` vs
  `ActualProperties` + a `PropertyDifferences` list (`PropertyPath`, `ExpectedValue`,
  `ActualValue`, `DifferenceType`).

Per-resource `StackResourceDriftStatus` ∈ `IN_SYNC` / `MODIFIED` / `DELETED` / `NOT_CHECKED`.
**Drift is one input, never the whole grade.** It only covers types that *support* it, and
`describe-stack-resource-drifts` **omits unchecked resources** — so "stack `IN_SYNC`" can hold while
critical resources were never checked (deploy nothing drift-checkable → a false `IN_SYNC`). **Fail
closed against the expected manifest:** reward 1 requires every *expected* resource present and
**provably `IN_SYNC`**; treat any resource that is `NOT_CHECKED`, omitted, or carries a status you
don't explicitly recognize as **non-passing** until covered by a per-resource `GetResource`
assertion. (The CFN analogue of "`terraform plan` reports no changes" — but coverage-complete, not
drift-status alone.)

### The assertion schema

The **CloudFormation resource specification** is a machine-readable, typed catalog of every resource
type — properties, which are `Required`, each type, and `UpdateType` (`Mutable`/`Immutable`).
Validate a read-back property blob against it programmatically; the same spec AWS ships for IDE
autocomplete is the verifier's property-level assertion contract.

## Write side — store the reward

The reward record must be **immutable**, **written exactly once**, and **signed by a key the agent
never holds** — all under account-B credentials. (Mechanism owned by the **reward-ledger-worm**
skill; summarized here for the isolation invariant.)

- **Immutability — S3 Object Lock (Compliance mode).** No principal, including account root, can
  overwrite or delete a protected *object version* for the retention duration (Governance mode is
  weaker — overridable with `s3:BypassGovernanceRetention`, so the agent role must never hold it).
  Requires S3 Versioning. **Caveat — version-scoped:** Object Lock protects a *version*, not the
  *key*. Versioning still permits new versions and delete markers, and `If-None-Match: *` treats a
  key whose current version is a delete marker as absent — so the conditional write alone is not
  write-once. Pair it with a **bucket policy denying unconditioned `PutObject`/`DeleteObject`** and
  **pin the signed object's version id**. (Precise WORM handling lives in the **reward-ledger-worm** skill.)
- **Atomic write-once.** `If-None-Match: *` on `PutObject` (412 if the key exists; first writer
  wins), or DynamoDB `PutItem` with `ConditionExpression: attribute_not_exists(<pk>)`. A rerun or
  tamper attempt is **rejected, not silently merged** — subject to the S3 version-scoping caveat above.
- **Authenticity — KMS Sign.** Sign the record (or its digest) with an asymmetric `SIGN_VERIFY` key:
  record → **RFC 8785 JCS** canonical JSON → UTF-8 → SHA-256 → KMS ECDSA **P-256**,
  `MessageType=DIGEST`. (JCS — RFC 8785 — not Protobuf: Protobuf serialization is non-canonical and
  breaks cross-runtime signing.) Embed a timestamp to bound replay. Anyone verifies with the public
  key — no trust in Assay's infra required.

The agent's sandbox role carries **no `kms:Sign`** on the signing key and **no
`s3:BypassGovernanceRetention`**. The verifier runs under a *separate* role owning the key and the
Object-Locked bucket.

## Consistency & determinism traps

Live cloud reads are not free or instant; deterministic grading depends on handling these (cousins of
the project's determinism policy — transient/genuine classifier + K-run reproduce; brain
`[[projects/assay/eng-architecture]]`):

- **Stale drift results (freshness / TOCTOU).** Don't just check timestamp ordering — require the
  drift detection used for grading to be **triggered by this grading run, after the episode's deploy
  converged**, and **fail closed if its `LastCheckTimestamp` predates the stack-update/deploy
  completion**. Otherwise you can grade a stale pre-deploy drift result as in-sync.
- **IAM eventual consistency.** Newly-created roles/policies take time to propagate; a verifier that
  provisions a role and immediately grades against it can hit a spurious failure. **Verify
  propagation before the grading path depends on it.**
- **`AccessDeniedException` is non-retryable** — it's the hard wall of the boundary, not a transient
  hiccup. Don't retry-loop through it; surface it.
- **Latency / cost.** Drift detection is async (poll-to-complete) and live reads add
  seconds-to-minutes per episode. LocalStack can stand in for much of this surface to keep the
  cost-free path viable — **with fidelity an open question** (flagged in the brain:
  `[[concepts/iac-verification-primitives]]`, `[[concepts/write-isolated-verifier]]`,
  `[[entities/localstack]]`): does LocalStack emulate drift detection, Object Lock Compliance,
  conditional writes, and KMS Sign faithfully enough, or must the grading store + signing key live on
  real AWS even when the task deploys to LocalStack?
