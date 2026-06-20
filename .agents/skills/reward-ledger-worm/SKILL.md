---
name: reward-ledger-worm
description: >
  The build playbook for the AssayOps reward ledger — the tamper-evident, WORM, KMS-signed reward
  record the write-isolated verifier emits. Use it whenever you build or review the reward-ledger
  client, the reward-record writer, the KMS signing of a grade, the S3 Object Lock store, or the
  portable-proof verifier — any code that stores, signs, or verifies a reward record keyed by
  trajectory_id. Three properties every record needs: immutable (S3 Object
  Lock Compliance), written exactly once (conditional write — If-None-Match / attribute_not_exists),
  and signed by a key the agent never holds (asymmetric KMS Sign over RFC 8785 JCS). It all lives in
  account B; the agent has no kms:Sign and no s3:BypassGovernanceRetention. Triggers on "sign the
  reward", "WORM reward record", "reward ledger", "Object Lock", "portable proof", "verify the signed
  grade" — even when not named. NOT for the trust boundary itself (use write-isolated-verifier), NOT
  for generic KMS/S3/IAM usage (use aws-iam / aws-sdk-js-v3-usage).
compatibility: >
  Self-contained guidance. The AWS primitives and canonicalization are in official AWS / RFC docs (no
  checkout needed); the project rationale is recalled through the co-located assay-brain skill — a
  sibling skill in this same repo that resolves the brain and degrades gracefully if it isn't checked
  out. Never hard-code a brain path. Designed for Claude Code; portable to any skills-compatible agent.
metadata:
  author: AssayInc
  version: "1.0.0"
  repository: https://github.com/AssayInc/skills
  provenance: "brain concepts/write-isolated-verifier, concepts/reward-hacking, projects/assay/eng-architecture (decision 4B); official AWS docs (S3 Object Lock, S3 conditional writes, DynamoDB conditional PutItem, KMS Sign/Verify/GetPublicKey) + RFC 8785 (JCS)"
---

# Reward Ledger (WORM) — build the record the agent can't forge

This is the **write-side mechanism** the **write-isolated-verifier** trust boundary defers to. The
reward record must be something the trained agent can neither **overwrite**, **forge**, nor
**replay** — and that a buying lab can verify **offline**, without trusting Assay. This skill is the
how-to-build; it **assumes the boundary** (account B, agent has zero creds/network — that's the
`write-isolated-verifier` skill) and does not re-explain it. Grounded in official AWS / RFC docs + the
brain (recall via **assay-brain**).

> **Stance.** A forgeable reward is worse than none. When unsure, **prove it or flag it.** If a task
> seems to need a mutable reward or A-side signing, **flag the issue; don't code around it.**

## The three properties (a record needs all three)

A grade is trustworthy only if the agent can't overwrite it, forge it, or replay it — three primitive
classes (brain `[[concepts/write-isolated-verifier]]`):

| Property | Primitive |
|---|---|
| **Immutable** — can't be mutated or deleted | S3 Object Lock (**Compliance** mode) |
| **Written exactly once** — no overwrite, no replay | conditional write (`If-None-Match: *` / DynamoDB `attribute_not_exists`) |
| **Authentic** — signed by a key the agent never holds | **asymmetric** KMS `Sign` |

**Precondition — isolation.** The bucket, the lock config, and the signing key all live in **account
B**, under credentials the agent's sandbox cannot assume. The agent role has **no `kms:Sign`**, **no
`s3:BypassGovernanceRetention`**, and **no write** to the ledger. (That boundary is the
`write-isolated-verifier` skill; immutability without it is hollow.)

## 1. Immutable — S3 Object Lock (Compliance)

**Compliance** mode = no principal, including the account root, can overwrite or delete a protected
*object version* for the retention period. (Governance mode is weaker — overridable with
`s3:BypassGovernanceRetention`; don't use it for the ledger, and the agent never holds Bypass.)
Requires Object Lock **and** Versioning enabled on the bucket.

**Version-scoped — the subtlety that bites:** Object Lock protects a *version*, not the *key*.
Versioning still permits new versions and delete markers, so Object Lock **alone** is not write-once
at the key level. Pair it with a **bucket policy denying unconditioned `PutObject` / `DeleteObject` /
`DeleteObjectVersion`** (and `BypassGovernanceRetention`), and **record the signed object's
`versionId`** so verification pins the exact version. Size the retention period to the audit window.

## 2. Written exactly once — conditional write

First-writer-wins; a second write is **rejected, not merged**:

- **S3** — `If-None-Match: *` on `PutObject` (412 if the key exists). Subject to the version caveat
  above: a key whose current version is a delete marker reads as *absent*, so combine with the deny
  policy.
- **DynamoDB** — `PutItem` with `ConditionExpression: attribute_not_exists(<pk>)`.

A re-grade is a **new record** (a new `attempt` under the trajectory), **never an overwrite** — which
ties to determinism: golden ×K → identical reward, so a *divergent* re-grade must **surface** (a new
signed record), not silently replace the old. A rejected write is the integrity guarantee firing, not
a bug to smooth over.

## 3. Authentic — asymmetric KMS Sign

An asymmetric `SIGN_VERIFY` key (`ECC_NIST_P256`), private key in account B; **the agent never has
`kms:Sign`** on it. The flow:

```
record → RFC 8785 JCS canonical JSON → UTF-8 → SHA-256
       → kms:Sign(MessageType=DIGEST, SigningAlgorithm=ECDSA_SHA_256)
store { payload, signature, keyId, alg }   # the WORM object
```

**Bind the context to bound replay/confusion:** the signed payload includes the expected
`trajectory_id` + `attempt` + report digest + `graderVersion` **and a verifier-issued episode
nonce**; verification **rejects** a stale timestamp, a reused nonce, or a mismatched trajectory
context — not just a missing signature.

**Why JCS, not Protobuf or ad-hoc JSON:** the signature must verify byte-for-byte **across runtimes**
(e.g. a TypeScript signer and a Python verifier). Protobuf serialization is explicitly non-canonical,
and ad-hoc JSON lets two encodings of "the same" record produce different bytes — a verification /
forgery gap. **RFC 8785 (JCS)** pins every serialization degree of freedom and ships a cross-language
conformance suite. (The project's choice — recall the rationale via **assay-brain**.)

## The record

One **contract-typed** schema, codegen'd to both languages (never hand-maintain dual TS/Python
types). Keyed by `trajectory_id` (+ `attempt` for re-grades). Sign the **whole canonical record**:
`trajectory_id`, `attempt`, `reward ∈ {0,1}`, a digest of the diff report, `graderVersion` (pins
which grader/vectors scored it), `gradedAt`, and a **verifier-issued episode `nonce`** (binds the
record to this run; verification rejects reuse). The signed bytes are the JCS encoding of that record.

## Portable proof — verify offline with the public key

The payoff: a buying lab or auditor verifies each record's signature with the **public key** (fetched
once via `kms:GetPublicKey`, then verified **offline** — no KMS call, no trust in Assay's infra). This
is the portable-proof verifier: it hardens the eval-to-performance proof, because the headline lift
rests on a tamper-evident record the lab can **independently** check. Distribute the public key + the
verification recipe; **never** make the proof depend on trusting Assay's KMS or API.

## Anti-patterns = trust breaks (you will be tempted; don't)

| Tempting shortcut | Why it's a trust break | Instead |
|---|---|---|
| "DynamoDB row we upsert / overwrite on rerun." | Mutable reward = the forgery/overwrite vector; defeats WORM. | Conditional write-once; a re-grade is a new attempt, never an overwrite. |
| "Object Lock is enough — skip the bucket policy." | Version-scoped: new versions / delete markers slip past it. | Deny unconditioned `Put`/`Delete` + pin the signed `versionId`. |
| "Governance mode — easier to clean up." | Overridable with `s3:BypassGovernanceRetention` → not tamper-proof. | Compliance mode; the agent never holds Bypass. |
| "HMAC / a shared secret is simpler than asymmetric." | Anything that gets the secret (the agent included) forges grades. | Asymmetric `Sign`; private key in B only, public key for verify. |
| "Sign a Protobuf / hand-rolled JSON of the record." | Non-canonical bytes → cross-runtime verify fails, or two encodings forge. | RFC 8785 JCS canonicalization before SHA-256. |
| "Sign just the reward value, no timestamp." | An old signed reward can be replayed. | Sign the whole record incl. a timestamp/nonce; bound replay. |
| "Let the A-side env-server hold the signing key to avoid a hop." | An agent-reachable signer forges grades. | Key + signing in account B only; agent role no `kms:Sign`. |
| "Verify the proof by calling Assay's KMS." | Forces the lab to trust the issuer — not portable. | Offline verify with the distributed public key. |

## Prove it or flag it

- The reward-record **forgery/overwrite** path is on the red-team exit bar — any open path ⇒ **STOP**
  (no proof claim on a forgeable reward).
- Ship a **round-trip + cross-runtime conformance** test: TS sign → Python verify over the JCS
  encoding; a known-answer JCS vector; a **tamper test** (flip a byte → verify fails); a
  **double-write test** (second write rejected, original unchanged).
- Determinism: golden ×K → identical reward; a re-grade **appends**, never overwrites.
- If a task seems to need a mutable reward, A-side signing, or dropping a property, that's a
  flag-the-issue moment (cross-ref `write-isolated-verifier`) — don't code around the boundary.

## Going deeper

**Dependency-free anchors (no checkout).** Official AWS docs — **S3 Object Lock**, **S3 conditional
writes**, **DynamoDB** conditional `PutItem`, **KMS** `Sign`/`Verify`/`GetPublicKey` — and **RFC
8785** (JCS canonical JSON). Full API shapes, the offline-verify recipe, and the key/bucket-policy IAM
shape: **`references/ledger-primitives.md`**.

**Project rationale.** Decision 4B, the JCS-not-Protobuf choice, and the trust boundary live in the
brain — `[[concepts/write-isolated-verifier]]`, `[[concepts/reward-hacking]]`,
`[[projects/assay/eng-architecture]]` — recall via the **assay-brain** skill. The boundary itself is
the **write-isolated-verifier** skill.
