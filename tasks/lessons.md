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

_No entries yet — this log accrues from real corrections, not pre-seeded guidance. Durable conventions
that aren't tied to a specific mistake belong in `CLAUDE.md` (operating layer) or `DECISIONS.md` (rules)._
