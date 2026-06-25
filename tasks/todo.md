# tasks/todo.md — #60 Spike: IAM eventual consistency / readiness gate

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Ephemeral per-session — durable records go to GitHub/PROGRAM.md/DECISIONS.md, not here.

## Decision (founder, this session)
**"Measure now (real AWS)"** — a bounded engineer probe (NOT an agent episode, so T7's cost-bomb gate
doesn't bind; cost ~ $0), in a throwaway/dev account. Authorized one-off exception to "LocalStack-only until T7".

## Status — DONE (PR #151, `Closes #60`)
- [x] Grounded vs DECISIONS §1/§3/§5/§8 + eng-arch 7A + impl-plan §9.2 + brain + skills.
- [x] Built + ran the probe (`py/packages/iam-readiness-probe`, fenced from `verify`); measured n=20, us-east-1.
- [x] Recorded methodology + numbers + readiness-gate recommendation on #60; ratified note in `DECISIONS.md` §1.
- [x] Consumers updated: #45 (7A classifier), #141 (read-coverage), #52/#33 (cross-account assume).
- [x] Cross-model `/review` (Claude + Codex gpt-5.5 xhigh, converged to ship): hardened probe (leak-proof
      teardown, tag-checked cleanup, per-signal timing, fail-loud reads, `--yes` gate, BotoCoreError);
      re-measured n=20 with the fixed probe; synced numbers across probe/DECISIONS/README/PROGRAM.
- [x] PROGRAM.md updated; merged latest main; `bun run verify` green.
- [ ] **Awaiting founder go to merge** (never merge without explicit approval).

## Result (n=20, us-east-1, fixed probe)
Reads (iam_read/cc_get/cc_list) resolve on the first poll, sub-second (cc_get p99 ~0.76s, 0 bound-exceeded) —
verifier read path insulated. assume p50 ~7.1s; perm p50 ~7.7s, tail to ~42s — the provision-then-use delay.
Readiness gate = bounded (~60s) FAIL-CLOSED 7A-budget calibration on the E8 setup path, isolated from the grade.
