# todo — E2-1 follow-up (#163): correct cross-account read mechanism + harden read path

> Ephemeral per-session scratchpad (durable records → PROGRAM.md / the PR / issues).

**Context:** A post-merge diverse-lens review of #160 (the E2-1 read skeleton) — a security/reward-forge
red-team + an edge-case/crash sweep + a design/SOTA lens, across Codex gpt-5.5 xhigh + Claude — found three
defects in the merged moat code. The moat holds (no reward-forge); these are a trust-claim correction + two
fail-closed hardenings. Tracked as #163.

**Fixes (TDD, RED→GREEN):**
- [x] **`RoleArn` is not a cross-account hook.** Verified vs the AWS Cloud Control user guide: `RoleArn` is a
  SAME-account CFN service role; the target account is set by the signing creds; cross-account = STS
  `AssumeRole` → account-A creds → client. Removed the `role_arn` field/threading + the test + the fake
  plumbing; corrected the docstrings to STS AssumeRole (#33/E8). Restores DECISIONS §1.
- [x] **`RecursionError` DoS.** `_properties_of` caught only `ValueError`; `json.loads` raises
  `RecursionError` on deeply-nested JSON → raw crash. Now `except (ValueError, RecursionError)`.
- [x] **Empty-page false-crash.** An absent `ResourceDescriptions` is the AWS empty-result shape → treat as
  empty (matches `infra-local`); a present-non-list still fails closed; truncation = #141.
- [ ] **Ship:** `bun run verify` green; PROGRAM.md + lessons.md + the #160 entry's stale `RoleArn` claims
  fixed; PR `Closes #163`; Codex `gpt-5.5` xhigh re-review to convergence.

**Flagged (out of scope — separate fix):** the `write-isolated-verifier` skill + its brain source carry the
same wrong `RoleArn`-as-cross-account claim (the root cause that misled the #160 build). Correct at
AssayInc/skills + the brain so future agents aren't re-misled.
