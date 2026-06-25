# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done. Ephemeral per-session — durable records go to GitHub/PROGRAM.md/DECISIONS.md, not here.

---

## #31 (E2-2): Golden-target regeneration → zero normalized diff = reward 1

**Issue:** E2-2 (M), lane:A, P1, area:verifier, Phase-1 milestone.
**ACs:** (1) Grades real deployed state vs the #75 golden target: zero **normalized** diff = reward 1,
else 0 (integration test on a known pair). (2) Same input ×K → identical reward (#46).

### Grounding (DECISIONS.md + brain + issue — reconciled)
- 2A/6A/T1: verifier **regenerates** the golden (code+seed), grades **deployed state read-only** vs it,
  reward = zero **normalized** diff; per-tool adapters → one normalized IR → shared reward core; never
  runs agent code. Brain eng-architecture confirms "regenerates the AssayOps golden target [2A]" +
  the determinism check golden ×K → identical reward.
- Gates **#34** (CLOSED — `grade(deployed, golden) → GradeOutcome`) + **#75** (CLOSED — `generate(task,
  seed) → GoldenTarget`) are landed. **The seam between them does not exist yet — #31 is exactly it.**
- "real deployed state" is forward-looking (read path #30 unbuilt; real-AWS blocked on T7/#53). The
  *testable* AC is "known pair" → satisfied by a synthetic `NormalizedState(DEPLOYED_READ)`.

### Design (smallest change meeting the AC)
New `py/packages/verifier/src/assayops_verifier/grading.py`:
- `golden_as_normalized_state(target: GoldenTarget) -> NormalizedState` — the bridge: reconstruct each
  `GoldenResource` as a `NormalizedResource` (re-validate + canonicalize via diff-ir's stricter
  validator → fail-closed), tag `Provenance.GOLDEN_TARGET`.
- `GoldenNotGradableError(ValueError)` — a regenerated golden that can't be normalized for grading
  (fail-closed; the grading core is intentionally stricter than the generator — flag the divergence).
- `grade_deployment(registry, task, seed, deployed) -> GradeOutcome` — **regenerate** the golden
  internally (2A/T1; never accept it from the caller), bridge, `grade(deployed, golden_state)`.
- Re-export the three from `assayops_verifier.__init__`; refresh its module docstring.
Wire the diff-ir dep in `verifier/pyproject.toml` (mypy_path + pytest pythonpath + an
`assayops_diff_ir.*` mypy override mirroring the contracts one).

### Tasks (TDD: RED → GREEN per AC)
- [ ] Wire diff-ir into verifier pyproject (paths + mypy override).
- [ ] Extend `tests/synthetic.py` — `deployed_from_golden(target)` + a `none_property` builder.
- [ ] RED: `tests/test_grade_integration.py` — match→1; drifts (changed value / missing / extra / type)→0;
      normalization-equivalent deploy (diff JSON representation)→1.
- [ ] RED: `tests/test_grade_determinism.py` — `grade_deployment` ×K → identical reward + diff;
      cross-hash-seed subprocess determinism (match existing pattern).
- [ ] RED: `tests/test_grade_trust_boundary.py` — deployed AGENT_PLAN/AGENT_STATE/GOLDEN_TARGET →
      UntrustedInputError; golden regenerated internally (no golden param); non-normalizable golden →
      GoldenNotGradableError (fail-closed, never silent reward 1).
- [ ] GREEN: implement `grading.py`; re-export.
- [ ] `bun run verify` green (paste evidence). `/review`. Update PROGRAM.md/ISSUES.md. PR `Closes #31`.

### Out of scope (don't build here)
- The boto3/Cloud-Control deployed-state read path (#30/#141) — `grade_deployment` takes the deployed
  `NormalizedState` as input (what the read path will produce).
- The reward-record/WORM-ledger handoff (#32 → E4). #31 returns reward+diff only.
- The full #46 determinism harness — #31 ships the determinism *test* its AC requires.

### Flag (divergence to note on the PR, not fix here)
The golden generator's value validator (#75) accepts a `None` value and a `$`-prefixed key; diff-ir's
grading validator (#34) rejects both. The bridge therefore fails closed (`GoldenNotGradableError`) on
such a golden. Correct/safe (the grading core is the stricter trust gate); harmonizing the two
validators is a possible follow-up, out of #31's scope.
