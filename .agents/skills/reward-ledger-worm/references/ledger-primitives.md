# Reward-ledger primitives — the WORM + signing substrate

API-level detail for `SKILL.md`. Load this when you're actually wiring the ledger client or the
portable-proof verifier. Distilled from official AWS / RFC docs + the brain
(`[[concepts/write-isolated-verifier]]` — read it via **assay-brain** for the rationale).

- [Immutability — S3 Object Lock](#immutability--s3-object-lock)
- [Write-once — conditional writes](#write-once--conditional-writes)
- [Authenticity — KMS asymmetric Sign](#authenticity--kms-asymmetric-sign)
- [Offline verification recipe](#offline-verification-recipe)
- [IAM / key policy — least privilege](#iam--key-policy--least-privilege)

## Immutability — S3 Object Lock

- Bucket needs **Object Lock enabled** — at bucket creation **or on an existing bucket** (console /
  CLI / SDK / REST) — **and Versioning** (Object Lock requires versioning).
- Write the record with **Compliance** retention:
  `PutObject(..., ObjectLockMode=COMPLIANCE, ObjectLockRetainUntilDate=<now + audit window>)`.
  Compliance = no principal (incl. root) can overwrite/delete that *version* until the date.
  (Uploading **with** Object Lock retention requires `Content-MD5` or `x-amz-sdk-checksum-algorithm`:
  the AWS SDKs send a checksum automatically; a raw REST `PUT` must include one or the request fails.)
- **Version-scoped caveat.** Lock protects a *version*, not the *key*. To make the record
  effectively write-once and tamper-evident at the key level:
  - A **bucket policy** that `Deny`s `s3:PutObject` without `s3:if-none-match`, and `Deny`s
    `s3:DeleteObject`, `s3:DeleteObjectVersion`, and `s3:BypassGovernanceRetention` to every
    principal except a tightly-scoped admin (and **never** the agent role).
  - **No lifecycle delete markers.** S3 Lifecycle expiration can place a delete marker on the key
    even under Object Lock (delete markers aren't WORM-protected), and `If-None-Match: *` treats a
    delete-marker current version as *absent* — reopening the key for another conditional write. So
    configure **no expiration / delete-marker lifecycle rules** on the ledger prefix, and **deny
    `s3:PutLifecycleConfiguration`** to untrusted roles.
  - **Record the `versionId`** returned by the write; the portable proof pins
    `(key, versionId)` so a later delete-marker or new version can't masquerade as the record.

## Write-once — conditional writes

First-writer-wins; reject (don't merge) the second write.

- **S3:** `PutObject(..., IfNoneMatch="*")` → `200` if the key was absent, **`412 PreconditionFailed`**
  if it already exists. Requires SigV4. With concurrent writers, the first to complete wins.
- **DynamoDB** (if a queryable index is wanted alongside the S3 object):
  `PutItem(..., ConditionExpression="attribute_not_exists(pk)")` →
  **`ConditionalCheckFailedException`** if the item exists (rejected, not merged). To inspect the
  existing item on that rejection, use **`ReturnValuesOnConditionCheckFailure=ALL_OLD`** — not
  `ReturnValues=ALL_OLD`, which only returns a prior item on a *successful* overwriting put.
- A re-grade uses a **new key/sort value** (`<trajectory_id>#<attempt>` or a ULID), so history is
  append-only; nothing is ever overwritten.

## Authenticity — KMS asymmetric Sign

- **Key:** `CreateKey(KeySpec=ECC_NIST_P256, KeyUsage=SIGN_VERIFY)` in account B. The key policy
  grants `kms:Sign` to **only** the B-side verifier role (see below).
- **Sign:** canonicalize the record (RFC 8785 JCS) → UTF-8 → SHA-256 digest, then
  `Sign(KeyId, Message=<digest>, MessageType=DIGEST, SigningAlgorithm=ECDSA_SHA_256)`.
  Store `{ payload: <jcs string>, signature: <base64>, keyId, alg: "ECDSA_SHA_256" }`.
- **Replay / confusion bound:** the canonical `payload` binds `trajectory_id` + `attempt` + the
  report digest + `graderVersion` + `gradedAt` + a **verifier-issued episode nonce**; the verifier
  **rejects** a stale timestamp, a reused nonce, or a mismatched trajectory context — a valid
  signature over the *wrong* context must not pass.

JCS (RFC 8785) in one line: sort object keys lexicographically by UTF-16 code unit, no insignificant
whitespace, shortest ECMAScript number form, minimal string escaping. Use a conformant library, not a
hand-rolled `JSON.stringify` — and run the RFC 8785 conformance vectors in CI.

## Offline verification recipe

The lab/auditor needs **no** AWS call and **no** trust in Assay:

1. Obtain the **public key** once: `GetPublicKey(KeyId)` (or ship the SPKI DER/PEM alongside the
   corpus). Pin it.
2. For each record: recompute `SHA-256(JCS(payload))`, then verify the ECDSA-P-256 signature against
   the public key with any standard crypto library (offline). No `kms:Verify` required.
3. **Tamper test in CI:** flip one byte of `payload` → verification must fail. A passing flip is a bug
   in the canonicalization or the verify path.

(`kms:Verify` exists for in-account checks, but the *portable* proof must not depend on it — that
would reintroduce trust in Assay's KMS.)

## IAM / key policy — least privilege

- **Signing key policy:** `kms:Sign` allowed for the **verifier role in B only**; no account-A
  principal, no `Principal: "*"`, no org-wide grant. `kms:GetPublicKey` may be broad (the public key
  is meant to be distributed).
- **Ledger bucket:** writable only by the verifier role (and only via conditional `PutObject` with
  Object Lock params); the agent's sandbox role has **no** `s3:PutObject`/`s3:Delete*`/
  `s3:BypassGovernanceRetention` and at most read-none on the bucket.
- **Cross-account direction:** account B owns the key + bucket; nothing in B trusts account A. (The
  agent reaching B at all is the `write-isolated-verifier` boundary violation — see that skill.)
