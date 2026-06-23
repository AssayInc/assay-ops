# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## E1-3 (#28) — JCS canonicalization + golden vectors — IN PROGRESS (branch `feat/e1-3-jcs-golden-vectors`)

**Goal (AC):** (1) **both sides canonicalize identically** — production `canonicalize` from PyPI `rfc8785`
(the Python **signer**) + npm `canonicalize` (the TS **consumer**); a **locked golden-vector corpus**
(`contracts/vectors`, record → expected canonical bytes → sha256), authored via this **`fixture-change`**
PR (the E0-6 exception). (2) **A cross-language test asserts identical canonical bytes** (Python-signer ↔
TS-consumer).

**Validation (issue vs. DECISIONS + brain + code — don't trust the AI-written issue blindly):**
- Grounded in **`DECISIONS.md` I3** (signing path `record → RFC 8785 JCS → UTF-8 → SHA-256 → KMS ECDSA
  P-256, `MessageType=DIGEST`; the optional TS side *verifies* the same bytes → byte-parity is
  **Python-signer ↔ TS-consumer**; Protobuf disqualified; Zod is TS-ergonomics-only) + **§8** (locked
  fixtures: `contracts/vectors` editable **only** in `fixture-change` PRs **from #28** — so this PR is the
  inaugural owner) + **assay-brain** (`[[concepts/write-isolated-verifier]]`, current as of E17/#115:
  "JCS is the load-bearing choice … proven by a golden-vector parity gate"). No brain hit for a
  `reportDigest ↔ canonical diff-IR` relationship and no locked required record-set → `reportDigest` is an
  opaque hex field; corpus coverage is an engineering call (below).
- **Scope split with #29 (ISSUES.md):** #28 = production canonicalize (both sides) + the golden corpus +
  the cross-language **test**. **#29 = the CI regenerate-and-diff / parity *gate*.** So the generator is
  **deterministic** (the #29 precondition) but I do **not** build the CI regen gate here.
- **Reuses the #115 spike** which already proved `rfc8785` byte-exact on the official RFC 8785 vectors **and**
  byte-identical to npm `canonicalize`. The spike's `jcs-canonicalize.ts` comment + its fixtures README
  explicitly defer the *production* canonicalize + the locked `contracts/vectors` to **#28** — exactly this.
- **Pins (grounded):** `rfc8785` 0.1.4 ships `py.typed` (mypy-strict safe); npm `canonicalize@3.0.0` types
  `(input: unknown) => string | undefined` (no `any` — clean to wrap). `canonicalize` is already a
  `ts/packages/contracts` dep; `rfc8785` is a workspace dev dep → **becomes a runtime dep of
  `assayops-contracts`** once `canonicalize` moves to `src` (add to its `[project].dependencies`; `uv lock`).

**Design (smallest change that meets the AC; one source of truth for the signed-byte recipe):**
- **Python production canonicalize** → `py/packages/contracts/src/assayops_contracts/jcs.py`:
  `canonicalize(record: BaseModel) -> bytes` = `rfc8785.dumps(record.model_dump(mode="json"))`;
  `canonical_digest(record) -> bytes` = `sha256(canonicalize(record))` (the I3 signed digest). Re-export
  both from the hand-written `__init__.py`. This is the single definition the E4 ledger imports.
- **TS production canonicalize** → `ts/packages/contracts/src/jcs.ts`: `canonicalize(value: unknown):
  string` wrapping npm `canonicalize` (throws on the not-serializable `undefined` case). Re-export from
  `src/index.ts`. The consumer/verify side's single definition.
- **Locked corpus** → `contracts/vectors/jcs-golden.json` (+ `README.md`): `{vectors:[{name, schema,
  record, canonical, sha256}]}`. `record` = the model's `model_dump(mode="json")` fixed point (exactly the
  bytes the signer canonicalizes); `canonical` = its rfc8785 bytes (UTF-8 string); `sha256` = hex of the
  signed digest. Storing `canonical` (not just sha256) makes a parity break **diagnosable** + the golden
  **auditable** — appropriate for a trust-critical fixture.
- **Generator** → `py/packages/contracts/scripts/gen_vectors.py` + root **`just vectors`** (mirrors
  `just codegen`): authors the records via the Pydantic models (type-safe + valid by construction),
  canonicalizes, writes the manifest **deterministically** (sorted keys, trailing newline). Re-run = no
  diff (#29's precondition). **Edit the record set ONLY in a fixture-change PR.**
- **Corpus coverage (engineering call — no locked set):** the **reward-record** is the signed artifact →
  cover both `reward∈{0,1}` (locks the binary int, never `0.0`/`1.0`) + the ns-timestamp **digit-string**
  (stays quoted, not number-canonicalized) + key-sort + hex fields. Plus one representative vector each for
  **trajectory / diff-ir / task-spec** (nested structures, empty objects, the `tool` enum) to lock the full
  spine's serialization once (cheap now, a fixture-change PR later). Library-level JCS unicode/number
  conformance is already covered by the official vectors in the #115 spike — not duplicated here.
- **Cross-language test** = belt **and** suspenders: (a) **Python lane** (`tests/test_jcs_golden_vectors.py`)
  — each record validates through its model (a `model_dump` fixed point), `canonicalize` reproduces the
  golden `canonical` bytes, `canonical_digest().hex()` == `sha256`; (b) **TS lane**
  (`tests/jcs-golden.test.ts`) — each record validates via ajv against its schema, `canonicalize` ===
  golden `canonical`, sha256 === golden `sha256`. Both pinned to the **same committed bytes** ⇒ identical,
  transitively + drift-locked. Plus (c) one **direct** Python↔TS identity test over the corpus (Python
  `rfc8785` vs the TS harness via `bun`, the #115 subprocess pattern) — the literal "asserts identical
  canonical bytes."
- **DRY the spike onto the production canonicalize** (the spike comments anticipate it): point
  `tests/ledger_spike.py` `canonicalize` and `scripts/jcs-canonicalize.ts` at the new production functions
  (no second definition that must agree). Minimal, verify green; defer if it risks the spike's green.
- **Wiring:** `turbo.json` `globalDependencies += "contracts/vectors/**"` (a vector change busts the
  test cache — mirrors `contracts/schemas/**`); `.github/CODEOWNERS` per-path rule for `/contracts/vectors/`
  (the deferred E0-4 item — activates the locked-fixtures guard); a `fixture-change` label on the PR;
  `docs/ARCHITECTURE.md` brief note; `PROGRAM.md` + `ISSUES.md`.

**Steps (TDD — each AC = a failing test first, watched fail, then minimal green):**
- [x] Branch `feat/e1-3-jcs-golden-vectors`; ground (DECISIONS I3/§8 + brain + the #115 spike + ISSUES #28/#29 split).
- [x] Add `rfc8785` to `assayops-contracts` `[project].dependencies`; `uv lock`; verified `uv sync --locked` + `bun install --frozen-lockfile` (the #114 lockfile lesson) — clean minimal lock change (dependency edge only).
- [x] **RED**: `tests/test_jcs_golden_vectors.py` (Python) → `ModuleNotFoundError: assayops_contracts.jcs`; `tests/jcs-golden.test.ts` (TS) → `Cannot find module ../src/jcs`. Watched both fail.
- [x] **GREEN**: `src/assayops_contracts/jcs.py` (`canonicalize` + `canonical_digest`) + `__init__` re-export; `src/jcs.ts` (`canonicalize`) + index re-export; `gen_vectors.py` + `just vectors` → committed `contracts/vectors/jcs-golden.json` (6 vectors). Both lane tests green. (No README — matches `contracts/schemas/`; documented in ARCHITECTURE.md + the JSON `$comment` + CODEOWNERS + DECISIONS.md §8.)
- [x] **RED→GREEN**: the direct Python↔TS identity test over the corpus (subprocess via `bun`).
- [x] DRY the #115 spike onto the production canonicalize (`jcs-canonicalize.ts` + `ledger_spike.py` → the production recipe); spike green (24 py tests).
- [x] `turbo.json` globalDeps += `contracts/vectors/**`; `.github/CODEOWNERS` `/contracts/vectors/` rule; `docs/ARCHITECTURE.md` ◻→✅ markers; `fixture-change` label created.
- [x] `bun run verify` green (14/14, both lanes, 0 cached — full re-run); `just vectors` deterministic (re-run = identical sha).
- [x] `PROGRAM.md` + `ISSUES.md` updated.
- [ ] PR **`Closes #28`** (#28 is a sub-issue of E1 #2, single deliverable → `Closes` correct; **not** `Closes #2`), labeled **`fixture-change`**; `/review` (Claude + Codex `gpt-5.5` **xhigh**); **await explicit merge approval**.

### Review (`bun run verify` green 14/14, both lanes)

- **Done + proven (both ACs).** The contract spine's canonical-byte recipe is production on **both sides** and
  locked by a golden corpus. **AC1:** `assayops_contracts.jcs.canonicalize` (PyPI `rfc8785`, the account-B
  signer) and `@assayops/contracts` `canonicalize` (npm `canonicalize`, the TS consumer/verify side) emit
  byte-identical RFC 8785 JCS (`DECISIONS.md` I3); the locked **`contracts/vectors/jcs-golden.json`** (record →
  canonical bytes → sha256, deterministic via `just vectors`) covers all four contract records. **AC2:** the
  cross-language byte-parity is asserted three ways — the Python lane + the TS lane each reproduce the
  committed corpus (drift-locked) **and** a direct Python↔TS subprocess identity test.
- **Grounding (issue vs. floor):** confirmed `DECISIONS.md` I3 + §8 (the §8 checklist names **#28** as the
  owning `fixture-change` PR for `contracts/vectors` — so this PR is authorized to create it) and the brain
  (`[[concepts/write-isolated-verifier]]`: JCS load-bearing, Protobuf disqualified, "proven by a golden-vector
  parity gate"). **No brain hit** for `reportDigest ↔ canonical diff-IR` → treated `reportDigest` as an opaque
  hex field (not coupled). **#28/#29 scope split** (ISSUES.md): #28 = canonicalize + corpus + cross-language
  **test**; **#29** = the CI regenerate-and-diff *gate* (kept out; the generator is deterministic as its
  precondition).
- **Corpus coverage (engineering call — no locked set):** reward-record (the signed artifact) gets both
  `reward∈{0,1}` + the ns-timestamp digit string + key-sort + hex; one representative vector each for
  trajectory / diff-ir / task-spec (nested structures, empty objects, the `tool` enum); one non-ASCII vector
  for raw-UTF-8 parity. Library-level JCS conformance is already covered by the #115 spike's official vectors —
  not duplicated.
- **Smallest change + DRY:** the canonicalize recipe is defined **once** per lane and imported; the #115
  spike's two parallel canonicalize implementations are DRY'd onto the production recipe (the spike comments
  anticipated #28 doing this). No separate corpus README (matches `contracts/schemas/`).

### `/review` (Claude adversarial subagent + Codex `gpt-5.5` xhigh) — findings handled

Both models confirmed the core is sound: the cross-language test is **non-tautological** (Claude verified by
mutating the TS output → test fails), determinism holds, the #115 spike DRY refactor changed **no signed
bytes** (Codex confirmed), the trust boundary is intact, and the signed **`RewardRecord` is fully safe** (all
7 fields required). Two real findings, both on the **not-yet-signed** `DiffIR`/`Trajectory`:

- **Number domain (Claude, conf 9).** A large int in an open `Any` field validates, then the Python signer
  (`rfc8785`) **fails closed** while a JS consumer rounds. → Added `diff-ir/numeric-property` (in-domain
  numbers canonicalize identically) + a **fail-closed test** + documented the IEEE-754 / valid-Unicode domain
  on both lanes + flagged the verify-path symmetric reject for **E4/#29**.
- **Optional-field model/schema bug (Codex xhigh, High).** Python canonicalizes the `model_dump` form, a TS
  consumer the raw object; they diverge on `DiffIR.Resource.propertyDiffs` (the one optional field): omitted →
  Python emits `"propertyDiffs":null`, which is **also schema-invalid** (schema requires an array). A real
  **#26/#27 model-vs-schema inconsistency** #28 surfaced — **not #28's to fix**. → Documented the
  materialized-form contract on both lanes; **flagged the root-cause fix** (`propertyDiffs` → non-optional,
  default `[]`) for **E3/#26/#27** in `ISSUES.md`; kept the corpus to **valid records only** (the
  schema-invalid omitted-optional vector was added then reverted). Codex's "Block" is on a real bug **upstream
  of #28**; #28's scope (canonicalize + corpus + parity for valid records) is met and the moat (the signed
  reward-record) is provably safe.

Net code-logic change from the review: **none** (the canonicalize recipe is unchanged) — the review added a
vector, a boundary test, docs, and the flags. `bun run verify` green (14/14) after each round.

**Grounding (founder docs-first rule).** The three load-bearing libraries were grounded against **primary
docs** — post-hoc, after the founder asked "did you ground every implementation from the official docs?"
(lesson [[reground-a-spikes-library-usage-against-primary-docs-when-promoting-to-production]] added):
**`rfc8785`** (Trail of Bits README — RFC 8785 JCS, `dumps(obj)→UTF-8 bytes`, "All APIs raise
`CanonicalizationError`… on serialization failures" = the documented fail-closed), **`canonicalize`**
(erdtman README — "crypto safe… as defined by RFC8785", default export → canonical string, TS types),
**Pydantic `model_dump(mode="json")`** (official docs — "ensure JSON-compatible types are used"). All three
**confirm** the implementation + the committed doc claims; **no corrections**. (The other deps are
low-stakes utilities cross-verified by tests — `hashlib`/`node:crypto` sha256, `json.dumps` — or the
already-grounded #26 `ajv` pattern.)

---

## E17-S2 (#115) — Reward-ledger primitives in Python (rfc8785 · KMS Sign · S3 Object Lock · public verify) — IN PROGRESS (branch `spike/115-reward-ledger-primitives`)

**Goal (AC — the spike, not the E4 build):** a **minimal runnable** proof (+ recorded **go/no-go**) that the
four reward-ledger primitives are real in the Python core, over the canonical `@assayops/contracts`
`RewardRecord` (`reward∈{0,1}`), keyed by `trajectory_id`. Prove:
1. **RFC 8785 JCS** via `rfc8785` (ToB) — conformant (official vectors) **and byte-identical to a TS
   `canonicalize`** (the #29 Python-signer ↔ TS-consumer parity, shown).
2. **KMS `Sign`** — ECDSA P-256, `MessageType=DIGEST` over the JCS→SHA-256 digest (I3), via boto3.
3. **S3 Object Lock WORM** — Compliance (immutable) + conditional write-once (`If-None-Match`); a re-grade
   **appends** a new attempt, never overwrites.
4. **Portable/public verify** — a buying lab verifies the signed record **offline** with just the public key.

**Validation (issue vs. DECISIONS + brain + official docs — don't trust the AI-written issue blindly):**
- Grounded in `DECISIONS.md` **I3 / 4B / §8 / T4** (KMS-signed + Object-Lock WORM, append-only,
  trajectory-keyed; never a mutable row; the agent holds no `kms:Sign`/`s3:BypassGovernanceRetention`; all in
  account B) + the **`reward-ledger-worm`** skill (three properties; the JCS→SHA-256→DIGEST-sign recipe;
  offline verify) + an **assay-brain** recall (top: `concepts/reward-hacking`, `write-isolated-verifier` —
  forgeable reward is the #1 thesis risk; JCS pins cross-runtime bytes where Protobuf is non-canonical).
- **Reconciled the issue:** it says "byte-identical to **the TS `canonicalize`**" — but `#28` (JCS + golden
  vectors) is **unbuilt**, so there is **no production TS `canonicalize` yet**. → prove conformance against
  the **authoritative RFC 8785 vectors** (the language-neutral reference both sides must match) and show
  Python↔JS parity via the **RFC 8785 reference JS impl** (`canonicalize`, erdtman); flag that **#28 owns the
  production TS canonicalize + locked `contracts/vectors`**, **#29 owns the CI byte-parity gate**.
- **Official-docs-first (founder standing rule; I wrote the #114 mock from memory — don't repeat it):**
  `rfc8785` v0.1.4 (Trail of Bits) confirmed on PyPI; `moto` 5.x + `boto3` confirmed; **no AWS creds/CLI**
  here → the proof runs locally (moto + real `cryptography`) with **recorded findings** for the real-AWS
  path (consistent with LocalStack-first / T7-gated). **moto's enforcement fidelity** (KMS asymmetric
  sign→offline-verify; S3 Object Lock Compliance; `If-None-Match`) is **discovered empirically** (a throwaway
  smoke), never assumed — per `local-aws-emulator-must-prove-read-api`.

**Design (smallest change; `py/packages/contracts/tests/`, uv workspace, mypy --strict + Pydantic v2):**
- **Home = `py/packages/contracts/tests/`** (not env-server): imports the **real** `assayops_contracts.RewardRecord`
  (DRY — types ← the schema), reuses the cross-runtime **bun-shell precedent** (`test_roundtrip.py`), is where
  #28 JCS lands, and **keeps all signing/KMS/S3/WORM machinery out of the agent-reachable env-server**
  (reinforces the boundary; env-server runtime stays `openenv`-only).
- **Spike deps in the workspace-root `dev` group** (shared, never A-side runtime): `rfc8785`, `boto3`, `moto`.
  TS parity devDep `canonicalize` (erdtman) → `ts/packages/contracts`. mypy `ignore_missing_imports` override
  for `boto3.*`/`botocore.*`/`moto.*` if needed (mirrors env-server's openenv override).
- **Files:** `tests/ledger_spike.py` (the real primitives: `canonicalize()` via rfc8785; `kms_sign_record()`
  via boto3/moto KMS `Sign(MessageType=DIGEST, ECDSA_SHA_256)`; `verify_offline()` via `cryptography` +
  SPKI public key; `worm_put()` via boto3/moto S3 Object-Lock Compliance + `IfNoneMatch="*"`, key
  `<trajectory_id>#<attempt>`); `tests/test_ledger_primitives_spike.py` (the 4-AC proof);
  `tests/fixtures/rfc8785_vectors.*` (official vectors, spike-scoped — **NOT** the locked `contracts/vectors`);
  `ts/packages/contracts/scripts/jcs-canonicalize.ts` (stdin JSON → erdtman canonicalize → stdout).
- **Out of spike scope (note as E4/#28/#29 follow-ups):** the real account-B `py/packages/reward-ledger`
  package + IAM/key/bucket policies; the locked golden-vector corpus (`contracts/vectors`, #28); the CI
  byte-parity gate (#29); real KMS/S3 against a live account (T7-gated). The spike proves feasibility, not E4.

**Steps (TDD — each AC = a failing test first, watched fail, then minimal green):**
- [x] Branch `spike/115-reward-ledger-primitives`; ground (DECISIONS I3/4B/§8/T4 + skill + brain + issue); set #115 board → In Progress; update PROGRAM.
- [x] Add deps (`rfc8785 boto3 moto` → workspace dev group; `canonicalize` → ts/contracts devDep); `uv lock`+`uv sync`+`bun install`; **verified `bun install --frozen-lockfile` + `uv sync --locked`** (the #114 lockfile lesson); both lockfiles committed.
- [x] Throwaway smoke (scratchpad) learned moto KMS/S3 fidelity + the `rfc8785`/`canonicalize` APIs; then wrote committed tests test-first (RED on missing `ledger_spike` → GREEN).
- [x] **AC1** JCS: `rfc8785` byte-exact on all 6 official conformance vectors; diverges from sorted-key JSON on unicode + small floats (why #114's hand-roll was insufficient); **byte-identical to the TS `canonicalize`** over the vectors + the real record.
- [x] **AC2** KMS Sign: moto KMS `ECC_NIST_P256`/`SIGN_VERIFY`; `Sign(MessageType=DIGEST, ECDSA_SHA_256)` over `sha256(JCS(record))` → returns a sig + a P-256 SPKI public key (call shape proven).
- [x] **AC4** offline verify: `cryptography` verifies the signed record **offline** with only the SPKI public key; tamper → fails; foreign-key sig → fails; malformed → False (no raise).
- [x] **AC3** WORM: `IfNoneMatch="*"` first-writer-wins (2nd → 412 `PreconditionFailed`, original byte-unchanged); Compliance blocks deleting the signed version (`AccessDenied`); version-scoped caveat shown; a re-grade appends `attempt=1` (new key), `attempt=0` intact + still verifies.
- [x] `bun run verify` green (14/14, both lanes); go/no-go + boto3 call map + moto-fidelity findings recorded (Review below + the **#115 comment**; **not** DECISIONS.md — the floor already locks I3/4B/§8, which the spike confirms).
- [ ] Focused PR **`Closes #115`** (sub-issue, single deliverable → `Closes` is correct; **NOT `Closes #113`** — #113 is the epic, per `dont-close-an-epic-on-its-first-deliverable-pr`); `/review` (Claude + Codex `gpt-5.5` **xhigh**); **await explicit merge approval**.

### Review (the spike — `bun run verify` green 14/14)

- **GO — the four reward-ledger primitives are real in the Python core.** A runnable proof in
  `py/packages/contracts/tests/` over the real `@assayops/contracts` `RewardRecord` (15 tests; the suite
  also exercises a real `bun` subprocess for cross-runtime parity). E4 can build on these exact primitives.
- **AC1 — RFC 8785 JCS (`rfc8785`, Trail of Bits).** Byte-exact on all 6 official conformance vectors
  (UTF-16 key sort, surrogate pairs, control escapes, ECMAScript number forms) and **byte-identical to the
  RFC 8785 reference JS impl (`canonicalize`)** over the vectors + the real record — the #29 Python-signer
  ↔ TS-consumer parity, shown. A divergence test pins *why* #114's sorted-key `json.dumps` was only a
  stand-in (it escapes unicode + uses `1e-06`, JCS uses raw UTF-8 + `0.000001`).
- **AC2 — KMS Sign (boto3).** The exact E4 call — `ECC_NIST_P256`/`SIGN_VERIFY`, `Sign(MessageType=DIGEST,
  ECDSA_SHA_256)` over `sha256(JCS)`, `GetPublicKey` → SPKI — integrates against moto.
- **AC4 — portable offline verify.** Proven on real `cryptography`: verify with **only** the SPKI public
  key, offline; tamper/foreign-key/malformed all fail-closed. The full lifecycle (sign → WORM-store →
  read back → offline verify → decode to the contract record) is a capstone test.
- **AC3 — S3 Object Lock WORM (boto3).** moto enforces conditional write-once (`If-None-Match` → 412) and
  Compliance immutability of the signed version (delete → `AccessDenied`); re-grade appends a new attempt.
- **Findings flagged for E4 (prove-it-or-flag-it, not papered over):** (1) **moto's KMS crypto is
  non-functional** — a moto `Sign` does not verify against its own `GetPublicKey`; offline-verify must be
  validated against **real KMS** in E4 (the recipe itself is proven real on `cryptography`). (2) **Object
  Lock is version-scoped** — an unconditioned overwrite makes a new version; the design pins
  `(key, versionId)` + the conditional write, and **E4 adds a bucket policy denying unconditioned PUTs +
  the agent holds no `s3:BypassGovernanceRetention`/`kms:Sign`** (§8). (3) Real KMS/S3/IAM + the key/bucket
  policies + the real account-B `reward-ledger` package are **E4's build**, not this spike.
- **Grounding (founder docs-first rule; I wrote the #114 mock from memory — didn't repeat it):** `rfc8785`
  v0.1.4 + `canonicalize` v3 confirmed against PyPI/npm; the JCS recipe against the **official RFC 8785
  vectors** (committed as a spike fixture, distinct from the locked `contracts/vectors` #28); the
  `MessageType=DIGEST` ↔ `cryptography` `Prehashed` equivalence smoke-verified; moto fidelity discovered
  empirically (`local-aws-emulator-must-prove-read-api`), never assumed.

### `/review` (Claude adversarial + Codex `gpt-5.5` xhigh) — fixes applied (16 spike tests, verify 14/14)

Cross-model split: Claude verified the proofs are sound (not vacuous) → merge-after-wording; Codex (xhigh)
flagged AC3 fidelity → block. Reconciled by **applying the substantive findings** (moat-critical path) after
**empirically confirming each** (not acting on unconfirmed claims):
- **Curve pinning (real fail-closed gap, both models):** `verify_offline` accepted any EC curve — a P-384
  key verified `True` (confirmed). Now pins **`SECP256R1`** (+ a wrong-curve negative test); broadened the
  catch with `UnsupportedAlgorithm`. The recipe is P-256 specifically.
- **Delete-marker survival (Codex P1):** added a test — a simple delete (no `versionId`) inserts a delete
  marker (current key → `NoSuchKey`), but the locked signed version **survives by `versionId`, still
  verifies, and still can't be deleted**. Sharpens the version-scoped finding: key-level write-once rests on
  `(key, versionId)` pinning + an E4 deny policy.
- **Object-Lock checksum (Codex P1):** added `ChecksumAlgorithm="SHA256"` to every Object-Lock `put_object`
  (real S3 requires a checksum; boto3 sends one, but explicit is faithful + documents it for E4).
- **Docstring precision (both):** dropped the "replaces #114's stand-ins" overclaim (the spike doesn't touch
  the env-server mock); AC2 reframed as proving the **call shape / wiring**, not signing correctness; the
  parity test reframed as **demonstrating** the parity #29 will gate (not the gate itself).
- **Envelope binding (Codex P2):** documented that `verify_offline` pins the recipe (curve + ECDSA-SHA-256)
  and never trusts the envelope's `alg`/`keyId`, so envelope-metadata tampering can't downgrade; E4 binds
  key selection. Capstone now asserts the stored `alg`.

---

## E17-S1 (#114) — OpenEnv-native Python env-server feasibility spike — LANDED (PR #121, `b91da87`)

**Goal (AC — the spike, not the E5 build):** a **minimal runnable** OpenEnv-native Python env-server
(`create_app`/FastAPI) + a recorded **go/no-go** (OpenEnv-native Python vs. a TS wire-only server), proving
**4 things** and documenting the reward-boundary wiring (in a #114 comment and/or `DECISIONS.md`):
1. **Concurrent sessions isolated** over HTTP + `/ws`.
2. **Delayed/terminal reward shape** — episode ends → grade fetched from the (mock) account-B verifier, **not** `step()`.
3. **TRL drives the env** via the OpenEnv integration path at the versions we pin.
4. **Reward-boundary preserved** (non-waivable, `DECISIONS.md` §8 + I5): the A-side env-server **never** computes the graded reward.

**Validation (issue vs. DECISIONS + brain + official docs — don't trust the AI-written issue blindly):**
- Grounded in `DECISIONS.md` §1 / I5 / §8 (the non-waivable invariant) + #113/#114 + a brain recall. Brain
  is **stale on "TS env-server"** (pre-E17) — ignore that label; the wire contract + seam port unchanged.
- **Official-docs-first (founder standing rule):** OpenEnv + TRL shapes verified against the **pinned source**
  (`openenv[core]==0.3.1`, `trl==1.6.0` tags), not cached knowledge:
  - `create_app(env_factory, action_cls, obs_cls, env_name=, max_concurrent_envs=)` → FastAPI; per-WS-session
    env instance is the isolation mechanism (`SUPPORTS_CONCURRENT_SESSIONS=True` required for `>1`).
  - `Environment.reset(seed,episode_id,**kw)→Obs` / `step(action,timeout_s,**kw)→Obs` / `@property state`;
    `Observation.reward: bool|int|float|None` (freely settable A-side) — we pin it to **`0.0`** (zero shaping).
  - `EnvClient[Action,Obs,State]` over **WebSocket** (`reset`/`step`/`state` async); endpoints `/health`,`/metadata`,`/schema`,`/ws`.
  - **TRL reward seam:** `GRPOTrainer(rollout_func=…, reward_funcs=…)`; TRL **never auto-reads** `env.step().reward` —
    `rollout_func` forwards extra columns (e.g. `trajectory_id`) to `reward_funcs` as `**reward_kwargs`. → the
    graded reward is supplied **out-of-band by `trajectory_id`**, never from the env. (trl `grpo_trainer.py` L1719-1726/L2153.)
- **Pin call:** `openenv[core]==0.3.1` (canonical PyPI dist `openenv` + `core` extra; `openenv-core` is the
  stale alias stuck at 0.3.0; 0.3.1 clears the TRL doc floor `>=0.3.1` and satisfies I8's `0.3.x`).

**Design (minimal, faithful, provable — `py/packages/env-server`, uv workspace, mypy --strict + Pydantic v2):**
- **A-side env-server ONLY in `src/assayops_env_server/`** (the agent-reachable surface; provably no grade/sign code):
  `models.py` (`DeployAction`/`DeployObservation`/`EnvState`), `environment.py`
  (`DeployVerifyEnv`, `SUPPORTS_CONCURRENT_SESSIONS=True`, mints `trajectory_id` at `reset`, **`reward` always 0.0**,
  no `rubric`), `app.py` (`create_app(…, max_concurrent_envs=N)`), `client.py` (`EnvClient` subclass).
- **B-side is MOCKED, and lives under `tests/` (proof harness, not the shipped surface):**
  `tests/account_b_mock.py` — write-isolated verifier + reward ledger: `grade(trajectory_id, state)→reward∈{0,1}`,
  ECDSA **P-256** sign (KMS analog, I3) over canonical JSON of a faithful local `RewardRecord` (mirrors
  `@assayops/contracts`; canonical type stays there), **WORM** append-only keyed by `(trajectory_id, attempt)`,
  read-only `fetch`. The **private key lives only here**; the A-side holds nothing.
  `tests/trl_drive.py` — the trl-1.6.0-shaped `rollout_func`(returns a `trajectory_id` column, **not** `env_reward`)
  + `reward_funcs(*, trajectory_id, …)` that fetches + signature-verifies the account-B record out-of-band.
- **Out of spike scope (note as E5 follow-ups):** Dockerfile/`openenv.yaml`/HF push; `/schema` serving the real
  `@assayops/contracts` artifacts (I5); real KMS/S3 Object-Lock (E4/#115); full GPU GRPO step (vLLM-bound —
  the boundary lives in the rollout/reward seam, which we exercise CPU-only); the heavy `openenv[core]` footprint
  (gradio/pandas/numpy) — flag for E5 to slim.

**Steps (TDD — each AC = a failing test first, watched fail, then minimal green):**
- [x] Scaffold `py/packages/env-server` (pyproject pin `openenv[core]==0.3.1`; thin `package.json` turbo wrapper); `uv lock` + `uv sync`.
- [x] RED→GREEN **A** `test_environment.py`: env `reset` mints `trajectory_id`, `step` reward **always 0.0**, terminal sets `done`.
- [x] RED→GREEN **C** `test_concurrent_sessions.py` (**AC#1**): N async WS clients → isolated state + distinct `trajectory_id`; HTTP `/health`,`/metadata`,`/schema`.
- [x] RED→GREEN **D** `test_terminal_reward.py` (**AC#2**): drive to terminal, env reward 0.0 throughout; graded reward fetched out-of-band from mock account-B by `trajectory_id`.
- [x] RED→GREEN **E** `test_reward_boundary.py` (**AC#4**): A-side import graph has no grade/sign capability; fuzzed actions never yield reward∈{0,1}; a forged record fails B's signature; WORM append-only.
- [x] RED→GREEN **F** `test_trl_drive.py` (**AC#3**): `rollout_func` drives real env → `trajectory_id` column; `reward_funcs` returns the **out-of-band** {0,1}, ≠ env `step` 0.0; (skip-if-absent) trl `GRPOTrainer` accepts `rollout_func`.
- [x] `bun run verify` green (14/14, both lanes); README + go/no-go recorded; `PROGRAM.md`/`ISSUES.md` updated.
- [ ] Focused PR **`Closes #114`** (single-deliverable spike → `Closes` is correct; #114 is a sub-issue, not the epic); record go/no-go in a **#114 comment**; `/review` (Claude + Codex gpt-5.5 xhigh); **await explicit merge approval**.

### Review (the spike — `bun run verify` green 14/14)

- **GO — OpenEnv-native Python env-server** (vs. a TS wire-only server). Built `py/packages/env-server`:
  a minimal runnable `create_app`/FastAPI env (`DeployVerifyEnv`) + WS `EnvClient`, with the B-side
  **mocked** in `tests/` (write-isolated verifier + ECDSA-P256-signed WORM ledger) and a trl-1.6.0-shaped
  `rollout_func`/`reward_funcs` drive. All 4 ACs proven by passing tests against a **real uvicorn server +
  real WebSocket clients** (13 passed, 1 skipped — the optional trl-installed binding).
- **The reward boundary holds and is natural, not fought.** Grounded against the **pinned source**
  (`openenv[core]==0.3.1`, `trl==1.6.0`): OpenEnv by design "does not dictate rewards" (RFC 006/004), and
  TRL **never auto-reads** `env.step().reward` — reward is user-supplied via `reward_funcs`, and
  `rollout_func` forwards an arbitrary `trajectory_id` column to it (`grpo_trainer.py` L1719-1726/L2153). So
  the graded `reward∈{0,1}` stays out-of-band, joined by `trajectory_id` — exactly `DECISIONS.md` I5 + §8,
  **zero floor deviation** (the spike confirms the locked decision). A TS wire-only server would
  hand-reimplement the OpenEnv HTTP/WS contract **and** still need a Python TRL bridge → strictly more work,
  more drift, no benefit.
- **Grounding caught a pin error** (founder docs-first rule): `openenv-core` tops out at 0.3.0; the TRL
  doc's `openenv[core]>=0.3.1` is a **different** dist (`openenv` + `core` extra) → pinned `openenv[core]==0.3.1`.
- **Caveats flagged (not papered over; E5/E4/E2 follow-ups):** full GPU GRPO step deferred (TRL's generation
  hard-imports vLLM; the boundary lives in the rollout→reward seam, exercised CPU-only); `openenv[core]` is a
  heavy ~100-dep install (web UI off by default — slim in E5); openenv 0.3.1 ships no `py.typed` → mypy-strict
  needs `ignore_missing_imports` + a few `# type: ignore[misc]` subclass seams; the B-side mock stands in for
  real KMS/JCS (#28)/Object-Lock (#115)/regenerated-golden + boto3 read (#80). The `area:env-server` label
  still reads "OpenEnv **TS** env-server" (pre-E17 stale) — board-hygiene nit.

### `/review` (Claude adversarial + Codex `gpt-5.5` xhigh) — fixes applied

The cross-model review confirmed **no A-side path emits a graded reward** (the core boundary holds), and
caught real strengthening work (applied, re-verified green 16 passed / 1 skipped):
- **Independent read (Codex Critical):** the proof originally fed the agent-reachable
  `observation.deployed_state` into the grader — tautological. Added `cloud_state.CLOUD` (a ground-truth
  deploy substrate); **account-B now reads `CLOUD` by `trajectory_id` independently**, never the agent's
  observation. This makes "the agent cannot forge the grade / the read is independent" actually demonstrated.
- **AC#3 framing (both):** `trl` is not a runtime dep (the real-symbol test skips), so the headline was
  softened to "the rollout→reward **seam** is reproduced and run against the real env; the real
  `trl.GRPOTrainer` binding is opt-in (kept out of the gate to avoid torch/vLLM)."
- **Real bugs:** `verify()` now safely rejects malformed-hex signatures (caught `ValueError`) instead of
  raising; terminal is **latched** + the env mints `trajectory_id` in `__init__` (no empty-id / post-commit
  mutation); `cryptography`/`httpx` moved out of the A-side **runtime** deps into the workspace dev group
  (the env-server package now depends on `openenv[core]` only); `max_concurrent_envs` 8→16 (headroom);
  added tamper-after-signing + malformed-signature + terminal-latch tests; dropped one tautological assert.
- Left as documented low-risk: the `_free_port` TOCTOU (session-scoped, startup failures surface as a
  readiness timeout) and the single-threaded mock ledger's non-atomic write (real E4 uses conditional writes).

### Post-fix re-review (founder asked: "did you re-review with Codex xhigh + ground everything?")

Re-ran **Codex `gpt-5.5` xhigh on the FIXED code** + a fresh Claude adversarial pass + **grounded the
`cryptography` ECDSA-P256 signing against the official cryptography.io docs** (the one primitive I'd
written from memory — confirmed correct/idiomatic on `cryptography==49.0.0`). Both re-reviews confirmed the
tautology is genuinely fixed and no A-side path emits/forges the reward; applied the residual hardening:
- **`CLOUD` is now lock-guarded** (`threading.Lock`) — atomic read under the thread-pooled server.
- **Divergence test** added (Codex "request changes"): account-B grades the ground-truth substrate and
  **ignores a fabricated observation** — locks the anti-tautology so it can't regress.
- **Out-of-band join key** (Claude HIGH): the harness now mints `trajectory_id` and passes it via
  `reset(episode_id=...)`, grading by the harness id — never read back from the agent's observation (also
  fixes the silently-ignored `episode_id`).
- **Honest scope** on `cloud_state` (lossless echo, no deploy-vs-requested divergence, test-lifetime),
  serial-execution note on the isolation fixture, and the verify-comment precision fix. `bun run verify`
  green (14/14); env-server **18 passed / 1 skipped**.

---

## E17 (#113) — Rebaseline to a Python-first proof-critical core — IN PROGRESS (branch `feat/e17-python-first-rebaseline`)

**Goal (AC):** a focused **decision PR** that locks **Python-first proof-critical core** (TS kept for
public/web/tooling), **preserves the trust floor untouched**, and **locks the OpenEnv reward-boundary
invariant in writing (non-waivable)**. Scope = floor docs + issue re-scope, **not** a code-migration
sweep — the proof-critical core is unbuilt.

**Validation (issue vs. DECISIONS + brain — don't trust the AI-written issue blindly):**
- Grounded in `DECISIONS.md` (frozen floor) + the brain reconsideration
  (`raw/conversations/assay-polyglot-typescript-vs-python.md`, 2026-06-22): the only hard anchor is
  **Python for train/eval** (TRL/Inspect/OpenEnv); the "CDK forces Node→TS" claim was a **category error**
  (CDK Python is first-class; Node is toolchain); the **moat is language-independent**. Cross-model
  convergence (Claude + Codex) → Python core, TS at the edge.
- **Trust floor preserved:** §1 account A/B split, §2 locked decisions, §3 tasks, §5 15-vector bar,
  §6 eval rigor, §7 risks — untouched (only the §1 *language labels* flip, per founder OK). The pivot
  touches **§4 I1–I7** (the `[impl]` language/tooling calls) + **§8** (env-server label + the new invariant).
- **Reward-boundary invariant** is the one new trust statement the OpenEnv-native Python pivot forces (the
  A-side env-server must never compute the graded reward). Locked in §8 (non-waivable), referenced from I5.

**Design (smallest change that meets the AC):**
- `DECISIONS.md`: §1 labels (TS→Python, surgical, boundary column held); §4 preamble + I2/I3/I5/I7
  rewritten (I1/I4/I6 already Python-anchored/topology — unchanged); §8 env-server relabel + the
  reward-boundary bullet. Provenance cites E17 (2026-06-22) as superseding the implementation-plan's TS-IP split.
- `docs/ARCHITECTURE.md`: package map moves the **unbuilt** proof-critical packages `ts/packages/*` →
  `py/packages/*`; `ts/packages/contracts` = public binding, `py/packages/contracts` = internal core;
  spine + episode diagrams to Python ownership + the reward-boundary note.
- `CLAUDE.md` (minimal, founder OK): top-line Python-core framing; skill-preflight AWS-read row →
  boto3/Python (demote `aws-sdk-js-v3-usage` to the consumer surface). `AGENTS.md` symlinks → auto.
- `PROGRAM.md` / `ISSUES.md`: pivot recorded; E2–E7 gated; migration follow-ups tracked.
- Issues: re-scope epics #3–#8 + contracts #2/#28/#29 (**reframe, not delete**); re-scope #80 (boto3 read
  spike); create blocking follow-ups (OpenEnv/TRL spike, ledger spike, TS re-home, brain/wiki sync); comment #113.

**Steps:**
- [x] Branch `feat/e17-python-first-rebaseline`; ground in DECISIONS + brain conversation + #113.
- [x] `DECISIONS.md` §1 labels + §4 I1–I7 + §8 (incl. the non-waivable reward-boundary invariant).
- [x] `docs/ARCHITECTURE.md` package map + spine + episode flow.
- [x] `CLAUDE.md` top-line + AWS-read row.
- [x] `PROGRAM.md` + `ISSUES.md` + this `tasks/todo.md`; `README.md` top-line (caught by `/review`).
- [x] Re-scope #3–#8 + #2/#28/#29 + #80 (→ Python; reframe-not-delete); create blocking follow-ups (#114–#117); comment on #113.
- [x] `bun run verify` green; PR **#118** (`Closes #113`); `/review` (Claude + Codex xhigh) → README + signing-attribution (verifier computes / ledger signs) fixes applied. **Awaiting explicit go to merge** (never merge unattended).

### Review (`/review` — Claude + Codex `gpt-5.5` xhigh)

- **Claude adversarial:** 1 finding — `README.md` front-line still framed the IP as TypeScript (stale, outside the original 6-file diff). Fixed. Trust floor verified byte-unchanged (§2/§5/§6/§7 outside all hunks); reward-boundary invariant loophole-free; §1 ASCII boundary column holds; anchors + technical claims valid.
- **Codex xhigh (5 findings, all applied):** (1+2) **signing misattributed** to contracts/verifier → corrected to the **reward ledger (E4/T4/4B)**: the verifier *computes* `reward∈{0,1}`, the ledger *signs* (KMS) + *writes* (WORM) — fixed in `ARCHITECTURE.md` (pkg line + spine diagram) and `DECISIONS.md` (I3 + §8 invariant); (3) `PROGRAM.md` Recently-Landed `aws-sdk-js→verifier E2` mapping marked E17-superseded (→ boto3); (4) these step checkboxes synced to reality; (5) `ARCHITECTURE.md` layout note "app-vs-library split per lane" corrected (Python CLIs are `py/packages/*` console-scripts, no `py/apps/`).

---

## E1-2 (#27) — Codegen wiring (quicktype + datamodel-code-generator) — IN PROGRESS (branch `feat/e1-2-codegen-wiring`)

**Goal (AC):** a root **`just codegen`** regenerates **committed** TS types (quicktype) + Pydantic v2
models (datamodel-code-generator) from `contracts/schemas/`; both generators **pinned** + **fixed flags**
→ deterministic (re-run = no diff, the #29 precondition); a **semantic** reward-record round-trip test
(TS serialize → Pydantic parse → Py serialize → deep-equal); `bun run verify` green (tsc strict + Biome;
mypy --strict + ruff).

**Validation (issue vs. DECISIONS + brain + code — don't trust the AI-written issue blindly):**
- Grounded in `DECISIONS.md` **I3 / 5A / §8**: one JSON-Schema source → quicktype (TS) +
  datamodel-code-generator→Pydantic v2 (Py); **never hand-maintain dual types**; artifacts committed.
  assay-brain adds no deeper locked codegen detail (rationale lives in I3). 0 open blockers (#26 landed).
- **Scope = codegen + semantic round-trip ONLY.** JCS canonicalization + golden vectors = **#28**; the CI
  regenerate-and-diff / byte-parity gate = **#29**. Keep both out. **Do not touch `contracts/vectors`**
  (locked, #28) — the round-trip uses a **synthetic inline** instance.
- **Empirical grounding caught two issue errors** (verified vs. the pinned tools' `--help` + output, not
  the issue prose — the skill-preflight rule):
  1. The issue's Python snippet `--input contracts/schemas … --output …/models.py` **fails** ("Modular
     references require an output directory, not a file") — directory input forces **modular dir output**
     → output to `…/assayops_contracts/models/` (4 `*_schema.py` modules + header `__init__.py`).
  2. `datamodel-codegen` default `constr()`/`conint()` annotations **fail `mypy --strict`** → add
     **`--use-annotated`** (emits `Annotated[str, Field(...)]`; verified Success). Ruff-clean wants the
     **`ruff-check ruff-format`** formatters (docs), not just `ruff-format`.

**Design:**
- **`just codegen`** (root justfile recipe; the placeholder comment already anticipates it), fixed flags:
  - TS: `quicktype -s schema --lang typescript --just-types <4 schemas, fixed order> -o
    ts/packages/contracts/src/generated.ts` (pinned `quicktype@23.2.6` → bun.lock).
  - Py: `datamodel-codegen --input contracts/schemas --input-file-type jsonschema --output-model-type
    pydantic_v2.BaseModel --use-annotated --disable-timestamp --formatters ruff-check ruff-format
    --target-python-version 3.12 --output …/assayops_contracts/models` (pinned
    `datamodel-code-generator[ruff]` + `pydantic` → uv.lock). `--disable-timestamp` = no header stamp
    (determinism).
- **Generated `any` (TS) — the #26-deferred call.** quicktype has **no `unknown` option** (confirmed:
  `--help` + README). Open fields (`observation`/`action` → `{[k]:any}`, `expected`/`actual` → `any`)
  emit `any`, which Biome `noExplicitAny:error` rejects. **Decision = option (a):** exclude the generated
  file from Biome (`!…/src/generated.ts` in root `biome.json`); **`tsc` strict still typechecks it.**
  (Rejected (b) refine-schema: touches the #26 source of truth + ripples to #28/#29, and an open/union
  JSON-value schema still emits `any` in quicktype; rejected a regex any→unknown post-process: fragile
  over the "any JSON" comments, a determinism risk for the #29 gate.)
- **Generated lint carve-out (Py).** Long schema-description strings → ruff **E501** (unwrappable);
  mypy --strict passes. → carve the generated `models/` out of ruff **lint** while datamodel's ruff-format
  owns its formatting; **mypy --strict still checks it.** (Symmetric with the TS Biome exclusion — the
  standard treatment for generated code.)
- **Layout / placeholders.** TS: `src/generated.ts` (generated) + `src/index.ts` re-exports it (replaces
  `PLACEHOLDER`); drop placeholder `smoke.test.ts` (round-trip + real types supersede it); `schemas.test.ts`
  (ajv) stays. Py: generated `models/` subpackage + a **hand-written** `assayops_contracts/__init__.py`
  re-export (stable; codegen writes only under `models/`); replace placeholder `test_smoke.py`.
- **Round-trip test (AC behavior).** Cross-language ⇒ runs in the **py lane** (only CI lane with bun+uv).
  `py/packages/contracts/tests/test_roundtrip.py`: `bun run` a tsc-checked emitter
  (`ts/packages/contracts/scripts/emit-reward-record.ts`: `const r: RewardRecord = {…synthetic…}` →
  `JSON.stringify`) → `RewardRecord.model_validate_json` → `model_dump_json` → `json.loads` deep-equal the
  TS emission. The emitter compiling under tsc proves the TS type accepts the instance; the cross-lang
  parse + re-serialize proves the Pydantic model agrees + round-trips.

**Steps (TDD):**
- [ ] Branch `feat/e1-2-codegen-wiring`.
- [ ] Pin generators: quicktype → `ts/packages/contracts` devDeps (`bun install`);
  `datamodel-code-generator[ruff]` + `pydantic` → py deps (`uv sync`).
- [ ] Add `just codegen` recipe (fixed flags, both lanes).
- [ ] RED: `test_roundtrip.py` (+ the emitter) → fails (no generated types).
- [ ] GREEN: run `just codegen` (commit artifacts); emitter + index/`__init__` re-exports; Biome exclude +
  ruff carve-out; drop placeholders/smoke. Round-trip green.
- [ ] `bun run verify` green (both lanes); re-run `just codegen` → `git diff` empty (determinism).
- [ ] Update `PROGRAM.md` (+ `docs/ARCHITECTURE.md` codegen sketch → justfile, drop the never-built
  `contracts/codegen.config`); PR "Closes #27"; `/review`.

### Review

- **Done + proven:** root **`just codegen`** regenerates committed TS interfaces (`quicktype@23.2.6` →
  `ts/packages/contracts/src/generated.ts`) + Pydantic v2 models (`datamodel-code-generator 0.65.0` →
  `py/packages/contracts/src/assayops_contracts/models/`) from `contracts/schemas/`. **`bun run verify`
  green (11/11, FULL TURBO)**; the cross-language reward-record round-trip test passes (TS-serialize →
  Pydantic-parse → Py-serialize → deep-equal). **Deterministic:** re-running `just codegen` is
  byte-identical (sha256-verified) — the #29 gate's precondition.
- **AC coverage:** `just codegen` regenerates both lanes, artifacts committed ✓; both generators pinned
  (`bun.lock` / `uv.lock`) + fixed flags → no-diff re-gen ✓; semantic round-trip test ✓; verify green —
  tsc strict + Biome (TS), mypy --strict + ruff (Py) ✓.
- **Grounding caught two issue errors** (verified vs. the pinned tools, not the issue prose): (1) the
  issue's `--output …/models.py` fails on directory input → **modular dir output** (`models/` package);
  (2) default `constr()`/`conint()` annotations fail `mypy --strict` → **`--use-annotated`** (and ruff
  formatters are `ruff-check ruff-format`, not just `ruff-format`).
- **Decisions settled (the #26-deferred codegen-policy calls):** generated **`any`** (open diff-IR /
  trajectory fields; quicktype has no `unknown` option per `--help` + README) → **Biome exclude** for
  `src/generated.ts` (tsc strict still typechecks). Generated Python **E501** (unwrappable
  description strings) → ruff **per-file-ignore** for `models/*.py` (mypy --strict still typechecks).
  Layout: generated `models/` subpackage + hand-written re-export `__init__.py`; `src/generated.ts` +
  re-export `index.ts`; placeholders + smoke tests dropped (round-trip + real types supersede them).
- **Scope discipline:** codegen + semantic round-trip only. JCS/byte-parity (#28), the CI parity gate
  (#29) **not** pulled in; `contracts/vectors` (locked, #28) **untouched** — the round-trip uses a
  synthetic inline instance.
- **Cross-model `/review` (Claude + Codex gpt-5.5 xhigh) — 3 fixes + 1 documented decision (PR #112):**
  (1) **prune** the `datamodel-codegen --output` dir before regen — it doesn't self-clean, so a removed
  schema left an orphan module the #29 gate would pass green (verified add→appears, remove→pruned);
  (2) the stale "bounded doubles" line in `docs/ARCHITECTURE.md` → binary `{0,1}` (§8); (3) emitter-comment
  precision (`tsc`, not the round-trip, proves TS-type acceptance); (4) **`reward: number` → `0 | 1`** — a
  guarded post-process in `just codegen` pins the §8 binary invariant into the public TS type (quicktype
  can't emit a numeric literal union — verified 4 ways; proven: `reward: 2` is now a tsc error; the Python
  `Reward` enum already encoded it). **Still documented (inherent codegen limit, not a defect):** the
  diff-ir `modified ⟺ propertyDiffs` cross-field conditional is inexpressible in any generated type —
  enforced by ajv (#26) + the reward core (E3); generated types are structural shapes, not full validators.
  `bun run verify` green (11/11); CI green (ts/py/smoke).

---

## E1-1 (#26) — Author the 4 JSON Schemas — IN PROGRESS (branch `feat/e1-1-json-schemas`)

**Goal (AC):** `reward-record`, `trajectory`, `diff-ir`, `task-spec` JSON Schemas (Draft 2020-12) exist;
large IDs/nonces/ns-timestamps modeled as **strings**, rewards as **bounded doubles**, NaN/Infinity
**rejected** (validation test).

**Validation (issue vs. code + deps):**
- #26 was `blocked_by` #25 (T0 team gate); #25 **closed** (founder = interim RL/eval owner + hire opened) →
  #26 now ready (0 open blockers). Within E1: #26 → {#27, #28} → #29 (#29 `blocked_by` #27/#28); #27/#28
  logically need #26's schemas.
- No top-level `contracts/` exists yet (only per-lane shell pkgs). ARCHITECTURE.md §spine: schemas live at
  `contracts/schemas/*.schema.json` (neutral source of truth); `contracts/vectors` = #28, codegen = #27.
- **Scope = schemas + a validation test ONLY.** Codegen (#27), JCS/golden vectors (#28), CI parity (#29)
  are separate issues — don't pull them in (smallest change that meets the AC).

**Design:**
- `contracts/schemas/{reward-record,trajectory,diff-ir,task-spec}.schema.json` — Draft 2020-12, each with
  `$id` + `additionalProperties:false`. Field shapes grounded in the `reward-ledger-worm` +
  `deterministic-verification` skills. Modeling rules (JCS-forced, ARCHITECTURE.md §spine): IDs / nonces /
  ns-timestamps = `string`; reward = `{type:number, minimum:0, maximum:1}` (bounded double, finite).
- Validation test (TS lane, ajv Draft-2020-12) at `ts/packages/contracts/tests/schemas.test.ts`: every
  schema compiles; a good instance validates; reward NaN / Infinity / out-of-range rejected; a numeric ID
  rejected (string rule); an unknown property rejected (tight contract). ajv = dev-only test dep.
- **TS lane chosen** for #26's test: ajv's bounded min/max robustly rejects NaN/±Inf; cross-language
  byte-parity is #28/#29's job, not this issue's.

**Steps (TDD):**
- [x] Add `ajv` dev dep to `ts/packages/contracts`; `bun install`.
- [x] Write failing `tests/schemas.test.ts` (schemas absent → RED).
- [x] Author the 4 schemas → GREEN.
- [x] `bun run verify` green (both lanes).
- [x] Update `PROGRAM.md`; PR "Closes #26"; `/review`.

### Review

- **Done + proven:** `contracts/schemas/{reward-record,trajectory,diff-ir,task-spec}.schema.json` (Draft
  2020-12, `$id` + `additionalProperties:false`) authored as the neutral source of truth. Modeling rules
  applied uniformly: ids / nonces / timestamps / seeds / digests = `string`; `reward` = `enum {0,1}`
  (binary, finite). Validation test `ts/packages/contracts/tests/schemas.test.ts` (ajv Draft-2020-12) — TDD
  RED→GREEN, 16 tests. `bun run verify` green (8/8 tasks, both lanes).
- **AC coverage:** schemas exist ✓; large ids/nonces/ns-timestamps as strings ✓ (test rejects numeric ids);
  reward ∈ {0,1} (binary, finite double) ✓; NaN/Infinity + partial-credit rejected ✓ (enum admits only 0/1;
  test asserts 0.5 / 2 / −0.5 / NaN / ±Inf all rejected).
- **Cross-model `/review` fixes applied (Claude conf 9 + Codex gpt-5.5 xhigh):** (1) **`reward` →
  `enum:[0,1]`.** First modeled as a continuous bounded double `[0,1]`; `DECISIONS.md` §8 (non-negotiables)
  locks `reward ∈ {0,1}` and `deterministic-verification` names a 0.0–1.0 score as the gameable
  anti-pattern — the continuous form was a silent frozen-floor deviation. Corrected (still a finite JCS-safe
  number). (2) **`attempt`/`index` capped at 2^53−1** (the same >IEEE-754 hazard the string-id rule
  prevents). (3) **`diff-ir` `expected`/`actual`** documented as a deliberate any-JSON boundary (precise
  value typing deferred to where the IR is produced).
- **Tightening round (grounded in `DECISIONS.md` + assay-brain, per founder guidance — don't trust the
  AI-written issue blindly):** timestamps (`gradedAt`/`createdAt`) → integer-nanosecond **digit strings**
  (`^(0|[1-9][0-9]*)$`, one canonical no-leading-zeros form, not the RFC-3339-or-ns ambiguity); `task-spec.tool` →
  `terraform | cdk` (the locked T2/T3 authoring tools — CloudFormation is the read *substrate*, dropped);
  `diff-ir` **`modified ⟺ non-empty propertyDiffs`** via `if/then/else`; and `contracts/schemas/**` added to
  turbo `globalDependencies` — a schema change now busts the contracts-test cache (it didn't before: a
  false-green gap, since the test reads schemas from outside its package). Still deferred: unique
  resource-address (not cleanly JSON-Schema-expressible → the E3 reward core). 24 tests, pristine output.
- **Second cross-model review (pre-merge, Claude + Codex xhigh) — fixes:** timestamp pattern →
  `^(0|[1-9][0-9]*)$` (reject leading zeros — `"007"`≡`"7"` was a JCS byte-parity hole on the *signed*
  path); `diff-ir` propertyDiff now requires `expected` **or** `actual` (`anyOf`) so an empty `{path}` diff
  can't validate. Deferred to #27 (a codegen-policy call both reviewers agree on): typing `diff-ir`
  `expected`/`actual` (bare any-JSON → `any` in generated TS) and IR-number JCS precision.
- **Other design calls:** `tool` enum = `terraform | cdk`; field shapes a coherent v1 grounded in the
  `reward-ledger-worm` + `deterministic-verification` skills.
- **Scope discipline:** schemas + validation only. Codegen (#27), JCS canonicalization + golden vectors
  (#28, the locked `contracts/vectors`), CI parity (#29) are their own issues — not pulled in. `contracts/`
  is the neutral source (not a workspace pkg), so it's outside the lint/typecheck graph by design.
- **Validation:** #26 was `blocked_by` #25 (T0 gate) → closed (founder interim owner + hire opened) → ready.

---

## E0-4 (#21) — Repo hygiene (CODEOWNERS, PR template, secret scanning, CONTRIBUTING) — LANDED (PR #108)

**Goal (AC):** CODEOWNERS + PR template + secret-scanning push protection enabled (a planted secret is
blocked on push); the `Closes #` convention documented in the PR template; a `CONTRIBUTING.md` with the
contributor workflow + a pointer to the quality bar, linking (not duplicating) the README **Get started**.

**Validation (issue vs. code):**
- #21 is open, unblocked, Phase 0 — the last ready E0 eng issue (PROGRAM.md). Accurate, not already done.
- Sole collaborator is `@samuelcastro` (no org teams) → CODEOWNERS can only name him; a global rule is the
  right scope. The locked-grader paths (`contracts/vectors` #28, `tools/red-team` #56) **don't exist yet**
  (ISSUES.md) → no speculative per-path rules; they land in those epics' `fixture-change` PRs.
- The org has GitHub Advanced Security → secret scanning + push protection are enable-able on the private
  repo (unlike rulesets, which needed the paid plan).

**Design:**
- `.github/CODEOWNERS`: `* @samuelcastro`; header notes it's the DECISIONS.md §8 trust-rule enforcement arm.
- `.github/pull_request_template.md`: a `Closes #` line (documents the convention) + a lean quality-bar checklist.
- `CONTRIBUTING.md` (root): branch → focused PR (`Closes #`) → `bun run verify` → `/review` → merge on the
  maintainer's explicit go; trust-boundary + secrets sections; links README Get started + DECISIONS.md §8.
- Secret scanning + push protection enabled via the repo API; proven by a planted-secret push (blocked).
- Deferred (flagged in ISSUES.md): require-code-owner-review in the `main` ruleset (single collaborator →
  would deadlock solo PRs) + the per-path grader CODEOWNERS rules (land with #28 / #56).

**Steps (test-first via the planted-secret push + the gate):**
- [x] Enable secret scanning + push protection (repo API); resolve fabricated test alerts.
- [x] Add `.github/CODEOWNERS`, `.github/pull_request_template.md`, `CONTRIBUTING.md`.
- [x] `bun run verify` green (docs/config — no verify-graph impact; FULL TURBO).
- [x] Prove: a planted (fabricated) secret is blocked on push.
- [x] Update `PROGRAM.md` + `ISSUES.md`; PR "Closes #21" (#108); `/review`.

### Review

- **Done + proven:** secret scanning + push protection **enabled** repo-side (org has GitHub Advanced
  Security); `.github/CODEOWNERS` (`* @samuelcastro`), `.github/pull_request_template.md` (documents
  `Closes #`), `CONTRIBUTING.md` (workflow + quality-bar pointer + secrets; links README Get started). PR
  #108 (`Closes #21`); `bun run verify` green (8/8, FULL TURBO).
- **Push-protection proof:** a planted basket of push-protection-supported secrets (Stripe/SendGrid/Slack)
  was **rejected on push** (`GH013 … Push cannot contain secrets`, exit 1, ref rejected; no bypass, nothing
  landed). First attempts used `google_api_key` — **detection-only** (`hasPushProtection: false`), which
  lands + alerts and does NOT test push protection (user-corrected; lesson added).
- **Scope discipline:** no speculative CODEOWNERS rules for the not-yet-existent locked-grader paths
  (`contracts/vectors` #28 / `tools/red-team` #56) — they land in those epics' `fixture-change` PRs; the
  untracked `.env.example` (not this issue) kept out of the diff.
- **Deferred (ISSUES.md):** require-code-owner-review on the `main` ruleset (single collaborator → would
  deadlock solo PRs) + the per-path grader CODEOWNERS rules.
- **/review:** Claude + Codex (gpt-5.5 xhigh) adversarial passes — clean after fixing two doc-precision
  nits (push-protection wording in CONTRIBUTING.md; PROGRAM.md "essentially complete" → "once it lands").
- **Landed:** PR #108 squash-merged into `main`; E0-4 moved to PROGRAM.md *Recently Landed*; #21 closed.

---

## E0-2 (#19) — Two-lane CI (turbo + uv) + branch protection — IN PROGRESS (branch `feat/two-lane-ci`)

**Goal (AC):** `.github/workflows/ci.yml` runs the canonical `verify` gate on every PR across both
lanes, independently cache-keyed + non-blocking, holding zero account-B creds; branch protection on `main`.

**Validation (issue vs. code + dependency graph):**
- #19 has **no blocked-by deps**; project status Todo — ready.
- **Codegen-parity gate (AC#2) deferred to #29**, which is itself blocked-by #27 (codegen wiring) +
  #28 (golden vectors); no top-level `contracts/` schema exists yet. A regenerate-and-diff / byte-parity
  check against a non-existent schema would be an empty verifier — out of scope here (flag, don't fake).
- **Fixture-change guard deferred:** `contracts/vectors` (#28) + `tools/red-team` (#56) don't exist;
  ISSUES.md says "no action until those epics run." Branch protection records the intent now.
- `bun run verify` (= `turbo run typecheck lint test`) green locally; turbo drives BOTH lanes
  (TS via tsc/biome/`bun test`; Python via `uv run --frozen` mypy/ruff/pytest).

**Design — two parallel lanes (drift-proof complement partition):**
- `ts` lane: `bunx turbo run typecheck lint test --filter='!./py/**'` (bun/turbo) — every non-py package.
- `py` lane: `uv sync --locked` then `bunx turbo run typecheck lint test --filter='./py/**'` (bun + uv).
- Verified via `--dry`: `./py/**` = py-contracts only; `!./py/**` = the 4 non-py packages; union = all 5.
- Independent per-lane `.turbo` caches + uv `enable-cache`; no `needs` edge (lanes don't block each other).
- `permissions: contents: read`; no secrets / no OIDC — zero account-B creds (DECISIONS.md §1, §8).
- Actions SHA-pinned (checkout v7.0.0, setup-bun v2.2.0, setup-uv v8.2.0, cache v5.0.5); uv pinned 0.11.8.

**Steps (test-first via the gate + actionlint):**
- [x] Author `.github/workflows/ci.yml` (two lanes).
- [x] Validate: `actionlint` clean; YAML parses; both lane commands green locally; no creds in the workflow.
- [x] Update `PROGRAM.md` + `ISSUES.md` (CI landed; parity #29 + fixture-guard deferred; protection state).
- [x] PR "Closes #19" (#101); `/review` (3 cross-model findings fixed).
- [x] Branch protection on `main` via a repository ruleset (require a PR + the `ts` + `py` checks; block force-push/deletion).

### Review

- **Done + proven:** `.github/workflows/ci.yml` runs the canonical `turbo run typecheck lint test` as two
  parallel lanes — `ts` (`--filter='!./py/**'`) and `py` (`uv sync --locked` + `--filter='./py/**'`); the
  filters are a complement partition (verified by `--dry`: union = all 5 packages / 8 tasks = `bun run verify`).
  Green in real CI (run 27907919479: `ts` 12s, `py` 20s). `actionlint` clean; zero account-B creds
  (`permissions: contents: read`, no secrets/OIDC). Branch protection applied as ruleset `17947941`.
- **/review fixed 3 cross-model findings:** (1) `turbo.json` `globalDependencies` (`bun.lock`/`uv.lock`/
  `pyproject.toml`/`.python-version`) — without it a persisted `.turbo` cache could replay a stale pass and
  skip the Python checks after a dep bump (false green in a gate); fixes local `bun run verify` too.
  (2) `persist-credentials: false` on checkout. (3) `concurrency` + `cancel-in-progress`.
- **Scoped out (flagged, not faked):** the codegen-parity gate (AC#2) → #29 (blocked-by #27/#28; no
  `contracts/` schema yet); the `fixture-change` guard → activates when `contracts/vectors` (#28) /
  `tools/red-team` (#56) exist. A parity/guard against non-existent paths would be an empty verifier.
- **Surprise:** branch protection (classic AND rulesets) is gated behind a paid GitHub plan on private
  repos; going public is barred by DECISIONS.md §8. Founder upgraded the plan → ruleset applied. Recorded
  as a plan dependency in `ISSUES.md`.
- **Landed:** #101 merged (`009643e`); #19 closed; `main` ruleset-protected.

### Follow-up — xhigh re-review (branch `chore/e0-2-xhigh-review`)

The first `/review` Codex pass ran at `high` (the gstack skill hardcodes `-c model_reasoning_effort=high`,
overriding the repo's `gpt-5.5 xhigh` standard). Re-ran at **xhigh**; added three lessons (incl.
verify-against-official-docs-and-skills, the rule from this episode). Re-examined the three findings
against the **official turbo docs + skill** — none warranted a code change:
- **P1** `infra-local#test` `<NONEXISTENT>` → **non-issue** (E0-3 keeps the LocalStack smoke out of the
  Docker-free gate; typecheck+lint still run; the smoke lives in `localstack-smoke.yml`).
- **P2** `bunx turbo` "could fetch registry turbo" → **moot.** `bun install --frozen-lockfile` guarantees
  turbo is present, so `bunx turbo run` never fetches; turbo's CI rule only requires `turbo run` (which it is).
- **P3** `.turbo` cache "could replay a stale pass" → **already handled.** E0-2's `globalDependencies`
  (`uv.lock`/`pyproject.toml`/`.python-version`; the lockfile is auto-hashed) is turbo's prescribed fix —
  confirmed via `turbo --dry` (all four manifests are in the global hash) and the official caching docs.
  Turbo **recommends** CI caching, so dropping it would be contra-guidance.

Net: the merged E0-2 was already sound + turbo-idiomatic; this follow-up adds only the two lessons.
