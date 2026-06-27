# todo — #63 spike: read-side reward-hacking → vector 15 (E10)

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: #63/#56 comments + PROGRAM.md + the PR.

**Trigger:** implement #63. **Chosen shape (user):** characterize + prove (scratchpad) + hand off (Option 1).

## Grounding (done)
- #63 is a **spike**; AC = characterize read-side attack(s) + promote concrete fixtures **into #56** as vector 15.
- Vector-15 **row already locked** in DECISIONS.md §5 (line 377) + #56 body → "add to the list" half DONE; §5 is locked (`fixture-change`/#56-owned) — **do not edit**.
- `tools/red-team` is **#56-owned, `fixture-change`-only** (§8) + **unbuilt** → I must NOT build the suite (code-writer classifies/proposes/flags; owners land it — red-team-exit-bar).
- Read-path defenses (`read.py`/`adapter.py`/`grading.py`/`reward_core.py`) **built + unit-tested** (`test_verify.py` etc.); the **closed-world half is OPEN** (reads alone can't catch an extra out-of-scope resource — §1 #80) → **#53** (T7 SCP, `assay-cloud-org`) + **#141** (verifier enforcement). Per **R1, any open vector ⇒ STOP** → vector 15 **not closed**; #63 closing = the *spike* resolved.
- Two modes (red-team-exit-bar): mode-1 (reach/redirect grade → isolation) vs mode-2 (coerce read to false in-sync → stronger spec).

## Plan
- [ ] Draft the **characterization** (vector-15 sub-attacks, two-mode, each → defense + build-state + file:line) → scratchpad.
- [ ] **Prove it (scratchpad, test-first):** drive the *real* read→normalize→grade with crafted spoofs.
      baseline control → reward 1; closable spoofs fail-closed/0 (confirm + cite existing unit tests, no committed dupes);
      **NEW: OPEN closed-world gap** (correct deploy + extra out-of-scope-type resource → false reward 1); **NEW: tag-spoof decoy** (A↔B).
- [ ] **Diverse-lens adversarial review** (forge + correctness; Claude + Codex gpt-5.5 xhigh) on characterization + proof; re-review fixes.
- [ ] **Promote fixtures into #56** (comment: red → defended → green specs; open half blocks vector-15 closure on #53/#141).
- [ ] **Decision comment on #63** + wire tracking; **close #63**.
- [ ] Update **PROGRAM.md**; lean PR (`Closes #63`); `/review`; `bun run verify` green.
- [ ] Append a lesson if corrected. Remove scratchpad proof; confirm `git status` clean.

## Must-not (trust-boundary)
- No edit to DECISIONS.md §5 / `contracts/vectors` / `tools/red-team`. No committed parallel red-team suite. Don't claim vector 15 "closed".
