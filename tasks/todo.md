# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done. For parallel work, each git worktree carries its own copy.

---

## E0-6 (#18) — Adopt the Cleno AI-operating layer + verifiable loop

**Goal:** stand up the AI-operating layer — a single auto-loaded constitution + the verifiable-loop
scaffold — mirroring Cleno's structure, adapted to AssayOps's polyglot, verification-infra domain.

- [x] `CLAUDE.md` — title + identity, **Stance banner verbatim**, Project Focus (brain via
      `assay-brain` #73; `DECISIONS.md` settled), Architecture (pointer + moat one-liner), Commands,
      **Agent Operating Loop** ("implement the next ready issue" trigger), Working Guidelines (quality
      bar), Critical rules, Testing (fixtures locked), Toolchain (Bun + UV), Superpowers, Skill routing.
- [x] `AGENTS.md` → **symlink** to `CLAUDE.md` (`readlink AGENTS.md` → `CLAUDE.md`).
- [x] `PROGRAM.md` — Right Now / Recently Landed / Handoff Notes, honest to the E0 state.
- [x] `ISSUES.md` — the real cross-cutting follow-ups (CI=E0-2, `assay-brain`=E0-7, locked-fixture dirs).
- [x] `tasks/todo.md` (this file) + `tasks/lessons.md` (format seeded, no fabricated entries).
- [x] **DRY:** point to `DECISIONS.md` for the trust model / non-negotiables — do **not** restate them.
- [x] **Scope hold:** no `ci.yml` (E0-2/#19); no `HANDOFF.md` (folded into `CLAUDE.md`).
- [x] Verify AC: stance verbatim · `readlink AGENTS.md` · links to `DECISIONS.md` + `assay-brain` (#73)
      · locked-fixtures #28/#56 · no `HANDOFF.md` · `bun run verify` green.

### Review

- **Built:** the AI-operating layer — `CLAUDE.md` (constitution) + `AGENTS.md` symlink, `PROGRAM.md`,
  `ISSUES.md`, `tasks/{todo,lessons}.md`. Mirrors Cleno's `CLAUDE.md` section order and verifiable-loop
  discipline; content rewritten for the polyglot (Bun + UV) verification-infra domain.
- **Key decision — DRY against `DECISIONS.md`:** AssayOps has a frozen-floor `DECISIONS.md` that Cleno
  lacks, so this `CLAUDE.md` is deliberately thinner on domain rules: it **points** to `DECISIONS.md` §1
  (trust model) and §8 (non-negotiables) instead of duplicating them. The constitution owns the
  *operating layer* (the loop, the quality bar, locked-fixtures, toolchain, skill routing); `DECISIONS.md`
  owns the *rules*.
- **Key decision — scope:** `ci.yml` is **not** authored here. `docs/ARCHITECTURE.md` assigns it to
  **E0-2 (#19)** ("two-lane CI + branch protection"), a separate open issue. #18's AC "CI runs verify on
  every PR" is met by *documenting* the invariant (citing E0-2), matching `ARCHITECTURE.md`'s existing
  "CI (E0-2) runs the same gate" convention. Authoring the workflow would poach E0-2 and violate the
  scope discipline this very file establishes.
- **Assumptions:** the `assay-brain` skill (#73) and the locked-fixture dirs (`contracts/vectors` #28,
  `tools/red-team` #56) are referenced as forward dependencies — they don't exist yet; noted in
  `ISSUES.md`. `tasks/lessons.md` starts empty of entries (no real corrections yet to record).
- **Verification:** `bun run verify` green (both lanes); `readlink AGENTS.md` → `CLAUDE.md`; no
  `HANDOFF.md`; stance banner present verbatim.

### Review round 2 (user feedback — completeness pass)

- [x] **Caught:** over-trimmed the gstack skill list/routing (deduped against Claude-global config) —
      recorded in `tasks/lessons.md` (`claude-md-serves-all-agents-no-dedupe`).
- [x] Added the full **gstack** section (browse-only rule + `never mcp__claude-in-chrome__*` + install +
      complete skill list + cross-agent rationale) and adapted **Skill routing** (design/QA/Vercel →
      `assay-web`).
- [x] Added the **Skill layer** section (skills.sh + `skills-lock.json`, **prefer-official**) — maps
      **E0-10 (#85)** + **E0-11 (#86, `AssayInc/skills`)**; mapped **`assay-brain` (E0-7, #73)** and
      removed the "until #73 lands" hedges per user.
- [x] Filled remaining Cleno-universal gaps: "never use Bash for communication", comments policy +
      code-quality, `/review` each PR, read-official-docs-first, gstack `/learn` vs `lessons.md`, Karpathy
      attribution.
- [x] Held scope: did **not** create `.agents/skills/` or `skills-lock.json` (that's #85), nor `ci.yml`
      (E0-2/#19). Kept omitted: shadcn/UI, Mastra/TanStack/Supabase preflight, machine-local gbrain config.
- [x] Re-verified AC + `bun run verify`; updated `PROGRAM.md` / `ISSUES.md` to map #85/#86/#73.
