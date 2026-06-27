# todo — #141 E2-6: boto3 read-coverage enforcement (FAIL-CLOSED + closed-world + per-property gate)

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md (Recently Landed) + the PR + GitHub #141.

## Scope (grounded: DECISIONS.md §1 "E3-4 read coverage" + §5 vector #15 + §8; brain `iac-verification-primitives`; the #141 **founder scope comment** 2026-06-26; the #45 handoff note)

**In (the in-repo, account-B, moat-critical half — unblocked; its only named dep #45/#159 landed):**
1. **FAIL-CLOSED read policy** — never reward 1 for a resource the verifier can't independently read. Route a **transient** (throttle/5xx/eventual-consistency) read failure through the 7A classifier + K-run (`assayops_replay`); a **genuine** unreadable fails closed (reward 0 / raise); `skip`-and-grade-the-rest forbidden.
2. **Closed-world enumeration** (`deployed set ≡ golden set`) — exhaustive, paginated `list_resources` over the in-scope **type × allowed-Region** matrix, `GetResource`-normalizing each id, **failing closed** on any list/partial error, an **unlistable / context-listable** in-scope type, or a missing region client. The reward core already flags an *enumerated* extra (`added`→0); this makes the enumeration **complete**, so an extra can't hide unenumerated (vector #15).
3. **Per-asserted-property coverage gate** — authoring-time: each golden-diffed property must be one `GetResource.Properties` actually returns (Cloud Control omits write-only props) → else quarantine the task.

**Deferred (blocked on `assay-cloud-org` / a live account — do NOT gate the above; cross-reference, ensure tracked):**
- Real-AWS **coverage-matrix regeneration tool** + `describe-type` IAM read∪list verification (scope 4) — T7-gated corpus-admission tooling.
- The corrected read-only **IAM policy doc** (scope 5; the `cloudformation:` prefix is already in `read.py`/DECISIONS.md §1 — only the real-AWS-derived policy is deferred).
- **SCP primary closure** (#53), **cross-account read-role** (#52/#33). The in-repo enforcement runs on fakes until these land.

**AC for this slice (founder comment):** negative control — an *extra* or *unreadable* B-side resource the golden doesn't have → **reward 0, never 1**. Testable on fakes.

## Reuse (don't rebuild)
- `assayops_replay` (#45/#159): `classify` / `transient_kind` / `TransientGradeError(kind)` (the read path RAISES this) / `reproduce(grade_fn, runs=K) -> Reproducible | Quarantined` / `TransientBudgetExhausted(kind)` (EVENTUAL_CONSISTENCY→reward 0, INFRA→quarantine). **Purpose-built for #141.**
- `read.py` `DeployedStateReader` (#30): per-resource `get_resource`/`list_resources` reads + the recording read-only fake `cloud_control_fakes.py`. The closed-world enumerator builds on this.
- `grade_deployment` (#31) / `normalize` (#35) / `grade` (#34) — the existing read→normalize→grade path + its fail-closed family.

## Module plan (boto3-dependent code stays OUT of the cloud-free top-level `__init__`, like `read.py`)
- **`read_scope.py`** (new, pure): the verifier-side read-coverage matrix — `RegionScope`(GLOBAL|REGIONAL), `Listability`(DIRECTLY_LISTABLE|CONTEXT_LISTABLE|UNLISTABLE), `TypeCoverage`(type, region_scope, listability, write_only_paths), `ReadScope`(per-type coverage + allowed regions; fail-closed on an unregistered type) + the **per-property coverage gate** `assert_golden_readable(golden, scope)`.
- **`read.py`** (modify): the per-resource read **classifies** the boto3 error (transient → raise `TransientGradeError(kind)`; genuine → `UnreadableResource`) + the **closed-world enumerator** `read_closed_world(readers, scope)` over type×region, fail-closed on a list error / unlistable type / missing region.
- **`verify.py`** (new): the closed-world verify entry `verify(...)` = build `grade_fn` → `reproduce(grade_fn, runs=K)` → `VerifyVerdict`; maps `TransientBudgetExhausted` (EVENTUAL_CONSISTENCY→reward 0 fail-closed; INFRA→quarantine). `VerifyVerdict = Reproducible | Quarantined | FailedClosed`.

## Wiring (verifier → replay; acyclic — replay imports contracts+diff-ir only)
- `package.json`: add `"@assayops/py-replay": "workspace:*"` (already a bun member).
- `pyproject.toml`: add `../replay/src` to mypy `mypy_path` + pytest `pythonpath`; add an `assayops_replay.*` mypy override (follow_imports=silent, disallow_any_explicit=false), mirroring the diff-ir/adapter overrides.
- Turbo `dependsOn ^typecheck/^test` already present → the new workspace dep edge is modeled (#31 cache-graph fix). Run `bun install` + `uv lock`/`uv sync`; commit BOTH lockfiles (lesson `bun-lock-and-uv-lock`).

## TDD task list — ALL DONE (test-first, RED→GREEN, commit per task; 102 verifier tests; `bun run verify` green 29/29)
- [x] **T0** — wire the replay dep (package.json + pyproject + Turbo edge `@assayops/py-replay#test` confirmed upstream of verifier#test; lockfiles frozen-clean).
- [x] **T1** — `read_scope.py` ReadScope/TypeCoverage (fail-closed on unregistered type) + RegionScope/Listability.
- [x] **T2** — per-property gate `assert_golden_readable` (write-only property → quarantine; adjacent-correct readable-property test).
- [x] **T3** — transient classification: throttle/5xx/timeout → `TransientGradeError(INFRA)`; list/get-race → `TransientGradeError(EVENTUAL_CONSISTENCY)`; genuine → `UnreadableResource`. Updated the 2 #30 throttle tests + cloud_control_fakes (access_denied/list-error paths).
- [x] **T4** — `read_closed_world(readers, scope)` exhaustive type×region; fail-closed (`ClosedWorldError`) on unlistable/context-listable/missing-region; per-Region matrix (GLOBAL vs REGIONAL).
- [x] **T5** — `verify(...)` + `VerifyVerdict = Reproducible|Quarantined|FailedClosed`; maps `TransientBudgetExhausted` (EVENTUAL_CONSISTENCY→FailedClosed 0; INFRA→Quarantined); genuine propagates (fail closed). The AC negative control: extra-enumerated→reward 0; genuine unreadable→fail closed; never 1.
- [x] **T6** — moat read-only assertion across the K-run multi-Region verify (vectors #1/#10 by construction).
- [x] **T7** — cloud-free `__init__` re-exports the PURE read_scope API; read/verify stay boto3 submodule imports (`import assayops_verifier` pulls no boto3 — asserted).

## Self-validated against primary sources (lesson `a-converged-cross-model-review-is-not-validation`)
- No fail-OPEN: every enumeration gap raises (list error→classified; malformed page→ValueError; unlistable/missing-region→ClosedWorldError; UnreadableResource→adapter raises = whole episode fails closed, never skip-and-grade-rest).
- AccessDenied → genuine → UnreadableResource → raises (loud, never masked, never silent reward 0) ✓ (#45).
- EVENTUAL_CONSISTENCY-exhausted→reward 0, INFRA-exhausted→quarantine ✓ (#45 `TransientBudgetExhausted` doc).
- list-indexing lag → K-run disagreement → Quarantine (not a false reward) ✓.
- **Open design point (watch in review):** verify RAISES on a genuine unreadable (vs returning FailedClosed 0) — chosen so AccessDenied surfaces loudly; the caller maps to reward 0/quarantine. Defensible (fail-closed, never 1).

## Review
- [x] **Codex gpt-5.5 xhigh** (`b5tsr66ov`, banner-confirmed xhigh) — NO false-reward-1 in the new `verify` path (moat holds). 2 findings, BOTH fixed + committed:
  - **F1 (High):** `verify_deployment` was an unsound single-Region reward-emitting bypass → REMOVED; `verify()` is now the only reward entry; coverage migrated; `test_verify.py` dropped.
  - **F2 (Med):** the per-property gate only checked top-level names → a raw JSON-Pointer `write_only_path` would silently miss (false 0) → `TypeCoverage.__post_init__` now fails closed on a "/"-path.
- [x] **Diverse-lens Workflow** (`wewrpk0g1`, 19 agents) — moat holds (forge lens: no agent-controllable false-1). 3 confirmed of 15:
  - **F1 (Low):** classifier.py docstring overstates "boto3's own retry logic" (actually `transient_kind`) — HELD, batch with the read-path doc updates after the Finding-3 decision.
  - **F2 (Low):** ReadScope duplicate-region guard — FIXED + committed.
  - **F3 (Med, the crux):** `verify` RAISES on a genuine unreadable vs the floor's reward=0 — UNDER a 2-review decision (founder asked for Opus 4.8 max + Codex xhigh, grounded).
    - **Opus 4.8 (`acead7cca...`) DONE → Recommendation A, decisive.** CONFIRMED the AWS fact (verifier reads same-account via STS-assume-into-A → an agent resource-policy explicit-Deny, sharpest for KMS key policies in the Phase-1 corpus, overrides the read-role allow → AccessDenied; SCPs gate actions not policy content → dodge is REAL). Per-cause map: UnreadableResourceError (AccessDenied/validation/unparseable/malformed instance) → FailedClosed(reward 0, cause in reason); Unsupported/ClosedWorld/Golden → RAISE; EC→0 + INFRA→quarantine already correct. PRECONDITION: the #60/#52 readiness gate must exercise PER-TYPE read perms (else a per-type read-role hole → false-negative). FLAG: address-bridge errors (AddressBridgeError/DuplicateAddressError) need explicit classification (lean reward 0 IF the `assayops:address` tag is agent-controlled). Also: fix the false "score-0 vs alarm" dichotomy in the docstrings; reconcile the stale errors.py "quarantines" doc. I validated all load-bearing claims against the floor + IAM semantics myself — they hold.
    - **Codex xhigh (`bya6npkjk`) RUNNING** (first launch `bgrs1bflg` hung on stdin; relaunched with `< /dev/null`).
  - Spot-checked the 12 refuted: the only catastrophic-direction one ("GLOBAL mis-declaration fails OPEN") is SOUNDLY refuted (documented T7 boundary, non-agent-reachable config error). Add a cheap `region_scope`-is-moat-load-bearing comment (fail-open asymmetry vs listability) — batch post-decision.
- [ ] **FINAL** Codex xhigh re-review of the fully-fixed diff (after F3 lands) — lesson `re-review-fixed-code-with-codex-xhigh`.

## Review (memory `elevated-rigor-for-moat-features` + `assayops-standing-three-questions`)
- [ ] Diverse-lens adversarial review (forge + crash + design) over the diff — a **Workflow** (moat-focused) + the gstack `/review`.
- [ ] **Codex gpt-5.5 xhigh** pass (paste GitHub content inline — Codex has no network; `git diff` local). Re-review FIXED code to convergence (lesson `re-review-fixed-code-with-codex-xhigh`).
- [ ] Validate load-bearing premises against the **primary sources** myself (DECISIONS.md / skills), not reviewer consensus (lesson `a-converged-cross-model-review-is-not-validation`).

## Finalize
- [ ] Update **PROGRAM.md** (Right Now + Recently Landed) IN the branch (lesson `update-program-state-before-landing`).
- [ ] **Create a tracked issue for the deferred scope-4** real-AWS coverage-matrix regeneration tool + `describe-type` IAM read∪list derivation (NOT covered by #53 SCP / #52 read-role — confirmed); board + parent it; cross-reference #53/#52. Needed before `Closes #141` (narrowed to the in-repo half) loses it.
- [ ] Focused PR `Closes #141` (the issue is narrowed to this in-repo half; deferred layers tracked elsewhere). Wait for explicit founder go to merge (lesson `never-merge-without-explicit-user-approval`).
