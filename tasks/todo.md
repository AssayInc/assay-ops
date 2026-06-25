# tasks/todo.md — #60 Spike: IAM eventual consistency / readiness gate

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Ephemeral per-session — durable records go to GitHub/PROGRAM.md/DECISIONS.md, not here.

## Decision (founder, this session)
**"Measure now (real AWS)"** — a bounded engineer probe (NOT an agent episode, so T7's cost-bomb gate
doesn't bind; cost ~ $0), in a throwaway/dev account. Authorized one-off exception to "LocalStack-only until T7".

## Status — DONE (PR #151, `Closes #60`); probe kept PROVISIONAL, disposition tracked in #156
- [x] Grounded; built + ran the probe (fenced from `verify`); measured n=20, us-east-1.
- [x] Recorded numbers + readiness-gate recommendation on #60; ratified note in `DECISIONS.md` §1.
- [x] Consumers updated: #45 (7A classifier), #141 (read-coverage), #52/#33 (cross-account assume).
- [x] Cross-model `/review` (Claude + Codex gpt-5.5 xhigh, converged to ship): hardened probe; re-measured.
- [x] Founder review: probe is not core IP (§8) — kept for plausible future value, removal/graduation = #156;
      added ISSUES.md note + provisional marker + lessons.md entry.
- [ ] **Awaiting founder go to merge** (never merge without explicit approval); main is hot — may need a final sync.

## Result (n=20, us-east-1, fixed probe)
Reads sub-second (cc_get p99 ~0.76s, 0 bound-exceeded) — verifier read path insulated. assume p50 ~7.1s;
perm p50 ~7.7s, tail to ~42s — provision-then-use. Gate = bounded (~60s) FAIL-CLOSED 7A calibration (E8), grade-isolated.
