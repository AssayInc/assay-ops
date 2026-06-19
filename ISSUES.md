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
- **The committed skill layer is E0-10 / E0-11 / E0-7 (#85, #86, #73).** `AssayInc/skills` now exists
  with the **`assay-brain`** deep-recall skill — it degrades gracefully without the `brain` sibling
  (verified) and is the substance of **#73** (PR `AssayInc/skills#1`, in review). Still open: skills.sh +
  `skills-lock.json` (**prefer-official** — AWS / Terraform / OpenEnv + bun / turborepo / skill-creator)
  and the consumer `.agents/skills/` sync in **#85**; the six homegrown AssayOps domain skills
  (`write-isolated-verifier`, …) in **#86**. `CLAUDE.md` documents the layer as the design
  (prefer-official; author homegrown only for gaps). Until #85 wires it in, recall via the per-developer
  `assay-brain` install (or query `../brain/wiki` via `qmd` / the brain-side `wiki-query`).
- **Locked-fixtures directories don't exist yet.** `contracts/vectors` (#28, E1-3) and `tools/red-team`
  (#56, E10-1) are scaffolded by their owning epics; the locked-fixtures rule in
  `CLAUDE.md`/`DECISIONS.md` binds the moment they do. Listed so the rule isn't mistaken for stale config
  pointing at nothing — no action until those epics run.
