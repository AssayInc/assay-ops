# todo — #30 E2-1: Verifier skeleton (account B, deployed-state read-only)

> Ephemeral per-session scratchpad (durable records → PROGRAM.md / the PR / issues).

**Goal:** The account-B write-isolated verifier **read-and-grade skeleton** — a read-only Cloud Control
deployed-state reader that produces the adapter's `DeployedRead` records, wired through the landed
`normalize` (#35) → `grade_deployment` (#31) → `GradeOutcome`. Proves the structural moat so red-team
vectors **1 (fs-write-to-grader)** + **10 (cross-account-assume-role A→B)** fail by construction.

**Architecture:** New `py/packages/verifier/src/assayops_verifier/read.py` (the one arrow no landed code
covers: boto3 Cloud Control read → `DeployedRead`s). `DeployedStateReader` wraps an **injected** boto3
Cloud Control `BaseClient`, exposes ONLY read ops (`get_resource`/`list_resources`) through a read-only
allowlist guard, per-record fail-closed (`UnreadableResource` on a genuine read error; absence on
`ResourceNotFoundException`), boto3-native bounded retries (no hand-roll). Top-level
`verify_deployment(reader, registry, task, seed, type_names, bridge_registry=None) -> GradeOutcome` wires
read → `normalize` → `grade_deployment`. Optional `role_arn` threads the documented B→A read-only hook.

**Grounding (reconciled — the AI-written issue is stale in two places):**
- Body says `ts/packages/verifier`; the core is **Python** (`py/packages/verifier`) — E17, PROGRAM.md.
- AC "+ CloudFormation drift" is the **CDK/T3 (#66)** path; **Terraform = Cloud Control only** (#80,
  DECISIONS.md §1; #35 already dropped CFN drift). So #30's Terraform read path = Cloud Control only.
- DECISIONS.md §1 (read path), §5 (vectors 1/10/15), §8 (T1, 1C); brain `iac-verification-primitives` +
  `write-isolated-verifier` (Cloud Control under the verifier's OWN creds; optional `RoleArn` = B→A
  read-only role). boto3 `get_resource`/`list_resources` shapes + `RoleArn` primary-doc-verified.

**DEFERS (do NOT build here):** closed-world `deployed set ≡ golden set` exhaustive/paginated/Region-matrix
enumeration + per-property coverage gate + 7A transient/genuine classifier → **#141**; least-priv IAM +
SCP create-allow-list + real cross-account role → **#141/#53/E8**; CFN drift → **#66**; reward→ledger
KMS-sign+WORM → **#32/#37**; the 15-vector automated red-team fixtures → **#56** (`fixture-change`).

**Tech:** Python 3.12 · boto3/botocore (Cloud Control, injected `BaseClient`) · pydantic (existing) · pytest ·
mypy --strict + `disallow_any_explicit` (narrow boto3 boundary to `BaseClient`/`object`, never `Any`) · ruff.

---

## Tasks (test-first; each AC → failing test → green)

- [ ] **T1 — dep + scaffold.** Add `boto3>=1.40` to verifier `dependencies`; `uv lock` + `bun install`
  (verify `--frozen-lockfile`). Create `read.py` skeleton + extend `__init__.py` exports. Mirror
  `infra-local`'s botocore mypy treatment.
- [ ] **T2 — `DeployedStateReader.read_resource(type_name, identifier)`.** RED: a fake CC client returns
  `{"ResourceDescription": {"Identifier", "Properties": "<json str>"}}` → `DeployedResourceRead` with
  `json.loads`-parsed `properties` (assert `dict[str,object]`). GREEN. Then: `ResourceNotFoundException`
  → absence (None); a transient-exhausted `ClientError` → `UnreadableResource(reason=...)`. Read-only
  allowlist guard.
- [ ] **T3 — `list_resource_identifiers(type_name)`.** Paginated `list_resources` discovery (paginator,
  `ResourceDescriptions[].Identifier`, `NextToken`). RED→GREEN with a multi-page fake.
- [ ] **T4 — `read_types(type_names)`.** list+get over in-scope types → `list[DeployedRead]`; per-record
  fail-closed (absence dropped; unreadable → `UnreadableResource`). Comment: closed-world completeness = #141.
- [ ] **T5 — `role_arn` threading.** When set, passed verbatim to `get_resource`/`list_resources` (B→A
  read-only). RED: recording fake captures `RoleArn` kwarg.
- [ ] **T6 — `verify_deployment(...)` wiring → `GradeOutcome`.** read → `normalize` → `grade_deployment`.
- [ ] **T7 — integration (the AC):** clean deploy → `Reward.number_1`; a property-drifted resource → `…0`;
  a missing golden resource → `…0`. (Extra-resource/over-provision detection is closed-world → #141.)
- [ ] **T8 — moat / vectors 1 & 10 (non-tautological):** recording fake proves the *actual* client ops
  invoked ⊆ `{get_resource, list_resources}` (+ `get_paginator`) — no write/STS/assume call (vec 1 fs-write &
  vec 10 A→B both fail by construction); produced state is always `Provenance.DEPLOYED_READ` (agent
  provenance can't enter); the reader has **no** parameter to inject agent-reported state (grade depends only
  on client reads + registry/task/seed); `role_arn` is the only cross-account mechanism and is read-only B→A.
- [ ] **T9 — fail-closed end-to-end:** an `UnreadableResource` in a read → adapter `UnreadableResourceError`
  (never reward 1); unsupported type → `UnsupportedResourceTypeError` (inherited from #35).
- [ ] **T10 — gate + ship:** `bun run verify` green (paste), lockfiles frozen-clean; update PROGRAM.md;
  focused PR `Closes #30` + brief issue comment (path/drift reconciliation); two adversarial reviews
  (`/review`: Claude `code-reviewer` + Codex `gpt-5.5` xhigh, re-review to convergence).

**Smoke decision (flagged):** hermetic fake-client tests are the primary proof, anchored to primary docs +
`infra-local`'s LocalStack proof of the exact Cloud Control read APIs. No new LocalStack smoke for #30 (it
would duplicate `infra-local`'s deploy+read and couple packages); the real-AWS end-to-end harness drive is
T7-gated → #141. Flag in the PR.
