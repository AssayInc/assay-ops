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
- **The committed skill layer is E0-10 / E0-11 / E0-7 (#85, #86, #73).** The skills.sh lock + consumer
  `.agents/skills/` wiring is **bootstrapped** (PR #89: `skills-lock.json` + `bun` / `turborepo` /
  `karpathy-guidelines` + the **`assay-brain`** recall skill, vendored and symlinked into
  `.claude/`+`.hermes/`; `assay-brain` built in **#73 + #86**, closed). Still open in **#85**: the
  prefer-official cloud/IaC packs — AWS (`agent-toolkit-for-aws`) / Terraform (`hashicorp/agent-skills`) /
  OpenEnv (`meta-pytorch/openenv`) + `skill-creator`. The six homegrown AssayOps domain skills
  (`write-isolated-verifier`, …) are **#86**. `CLAUDE.md` documents the layer as the design (prefer-official;
  author homegrown only for gaps). Recall also works from any repo via the per-developer `assay-brain`
  install (or `../brain/wiki` via `qmd` / the brain-side `wiki-query`).
- **Locked-fixtures directories don't exist yet.** `contracts/vectors` (#28, E1-3) and `tools/red-team`
  (#56, E10-1) are scaffolded by their owning epics; the locked-fixtures rule in
  `CLAUDE.md`/`DECISIONS.md` binds the moment they do. Listed so the rule isn't mistaken for stale config
  pointing at nothing — no action until those epics run.
