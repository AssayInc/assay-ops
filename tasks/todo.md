# todo — #45 E6-2: Transient/genuine classifier + K-run reproduce + quarantine [locked 7A]

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md (Recently Landed) + the PR + GitHub #45.

## Status — DONE (committed; PR #159 open, `Closes #45`); awaiting founder go to merge
- [x] Grounded: DECISIONS.md §1/7A + brain + deterministic-verification / write-isolated-verifier / python-resilience / error-handling / type-safety skills + **#141's scope read directly** (not via a stale subagent summary).
- [x] TDD RED→GREEN, 27 tests; `bun run verify` green 29/29; both lockfiles frozen-checked.
- [x] Cross-model review (Claude + Codex gpt-5.5 **xhigh**, re-reviewed to convergence) + a founder-prompted primary-source re-validation that **caught a real false-negative bug** (see below).
- [ ] **Merge** — waits for explicit founder go (never merge without approval).

## What landed (new `py/packages/replay`, the E6/T8 home — ARCHITECTURE.md:69; shared with #44 replay; #46 is the E13 eval-gate that CONSUMES this policy)
- `classifier.py` — the **7A transient policy**: **transiently unreadable** (throttle / 5xx / read-after-create eventual consistency) = TRANSIENT (retry within the small read budget, then FAIL-CLOSED). A throttle is NOT a wrong answer — scoring it 0 is a false-negative (deterministic-verification skill; #141 scope 1 routes a surfaced throttle through the 7A classifier + K-run). **Policy vs mechanism:** boto3 adaptive owns the SDK throttle/5xx RETRY; #45 owns the POLICY + the K-run gate #141 routes a surfaced transient into. AccessDenied (isolation alarm, never masked) / Validation / bug = GENUINE. boto3-free (error code + a `TransientGradeError` marker for any routed transient).
- `reproduce.py` — `reproduce(grade_fn, *, runs=3, …) -> Reproducible | Quarantined`: drive K times, absorb transients via a bounded deterministic backed-off retry (injectable `sleep`, no jitter), quarantine a non-reproducing (flaky) task. `Quarantined` has **no reward attribute**; a genuine failure / exhausted transient budget → fail closed (raise). `Reproducible` carries the verified `GradeOutcome` so the ledger signs what the gate certified. Signature = `(reward, JCS canonical diff bytes)`.
- Generic over the grade callable → depends on diff-ir + contracts only (NOT verifier) → cycle-free when #141 reuses the classifier. K is an unlocked parameter (default 3; flagged).

## The bug the founder's questions surfaced (lesson logged)
- An over-narrowing during botocore grounding had made a **surfaced throttle GENUINE → fail-closed → reward 0** — the false-negative the deterministic-verification skill explicitly names. Both code reviews accepted the wrong premise; only re-reading the **skill + #141 scope 1** (primary sources) caught it. Reverted: throttle is a TRANSIENT; boto3 owns the retry *mechanism*, #45 owns the *policy*.

## Handoff (durable home: the PR)
- **#141 read path:** configure boto3 **adaptive** retry (the throttle/5xx retry mechanism); route a surfaced transient through this classifier + K-run; map a settled-absent NotFound → reward 0, a sustained infra transient (throttle) → quarantine/episode-retry (never reward 0 — a false-negative). `TransientBudgetExhausted` carries the cause.
- **Corpus/eval owner (#46, E13):** the eval-gate runs `reproduce` golden×K over the corpus and excludes Quarantined tasks; tune **K** for the production scored set (3 is a dev default).
