# Issues

Durable open problems and external follow-ups — the kind that outlive a single PR. Day-to-day work is
tracked in **GitHub Issues + Projects v2** ([`DECISIONS.md` I4](./DECISIONS.md#4-implementation-decisions-i1i11));
this file is for cross-cutting context a GitHub issue doesn't capture.

## Open Follow-Ups

- **CI + branch protection are E0-2 (#19).** `bun run verify` is the canonical gate and runs locally,
  but the two-lane GitHub Actions workflow (turbo + uv, independent cache-keyed lanes) that runs it on
  every PR — and branch protection on `main` — land in E0-2. Until then nothing *technically* blocks a
  direct push to `main`; the `CLAUDE.md` merge rule (**PR + verify-green + `/review`**) is the gate.
  E0-1 deliberately shipped no `ci.yml`, and E0-6 (#18) only *documents* the invariant — it does not
  author the workflow (that would poach E0-2's scope).
- **The committed skill layer is E0-10 / E0-11 / E0-7 (#85, #86, #73).** `assay-ops` has no
  `.agents/skills/` yet: skills.sh + `skills-lock.json` (**prefer-official** — AWS / Terraform / OpenEnv
  + bun / turborepo / skill-creator) lands in **#85**; the homegrown AssayOps domain skills in
  `AssayInc/skills` (`write-isolated-verifier`, …) in **#86**; the `assay-brain` deep-recall skill (must
  **degrade gracefully** without the `brain` sibling) in **#73**. `CLAUDE.md` documents the layer as the
  design; **never bulk-copy Cleno's skills**. Until then, query `../brain/wiki` via the brain-side
  `wiki-query` skill / `qmd`.
- **Locked-fixtures directories don't exist yet.** `contracts/vectors` (#28, E1-3) and `tools/red-team`
  (#56, E10-1) are scaffolded by their owning epics; the locked-fixtures rule in
  `CLAUDE.md`/`DECISIONS.md` binds the moment they do. Listed so the rule isn't mistaken for stale config
  pointing at nothing — no action until those epics run.
