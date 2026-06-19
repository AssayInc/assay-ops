# Lessons

Shared, committed memory for all agents working in this repo (see **Self-improvement loop** in
`CLAUDE.md`/`AGENTS.md`). After ANY correction from the user, append a lesson written as a rule that
prevents the same mistake. Review at session start; prune entries that stop being true.

Entry format:

```markdown
## YYYY-MM-DD — short-kebab-slug
- **Mistake:** what went wrong
- **Rule:** the rule that prevents it next time
- **Context:** files/commands involved (optional)
```

---

## 2026-06-18 — claude-md-serves-all-agents-no-dedupe
- **Mistake:** When porting Cleno's `CLAUDE.md`, trimmed the gstack skill list + routing out of the
  project constitution, reasoning it duplicated `~/.claude/CLAUDE.md` and was context bloat — the exact
  dedup Cleno's own lessons (`claude-md-serves-all-agents`) warn against.
- **Rule:** Never dedupe the project `CLAUDE.md`/`AGENTS.md` against Claude-only global config or plugin
  skills. `AGENTS.md` is read by non-Claude agents (Codex) that never load `~/.claude/CLAUDE.md`, so
  anything every agent needs — the full gstack skill list + routing, the `/browse`-only rule, operating
  rules — must live in this repo's file. When porting a template constitution, default to **completeness**
  for cross-agent content; only omit what is genuinely specific to the other project's domain (fiscal,
  shadcn/UI, that repo's machine-local gbrain config).
- **Context:** E0-6 (#18) `CLAUDE.md`; the user caught the missing gstack section. The committed skill
  *layer* (skills.sh / `skills-lock.json`) is separate and prefer-official (#85/#86) — that's not what was
  missing; the per-developer gstack workflow layer was.
