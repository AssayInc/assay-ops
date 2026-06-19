# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Write checkable items here before touching code; mark them as you go; add a short **Review**
when done.

---

## E0-11 (#86) — `AssayInc/skills` repo + the `assay-brain` recall skill

**Goal:** stand up the `AssayInc/skills` compilation repo and author its headline homegrown skill,
`assay-brain` — search/answer from the Assay brain (wiki + raw) from any repo. Adapt the proven
`cleno-brain` template (`Cleno/skills`) to Assay's domain, brain topology, and qmd collections;
**degrade gracefully without the `brain` sibling** (the #73 requirement).

**Scope (this work):** the repo scaffolding + the single `assay-brain` skill. The six domain skills
(`write-isolated-verifier`, `deterministic-verification`, `reward-ledger-worm`, `red-team-15-vectors`,
`eval-rigor`, `localstack-verifier`) and the consumer `skills-lock.json` wiring are **follow-ups** — the
latter blocked on the skills.sh lock format (**E0-10/#85, open**). So **don't close #86**; advance it and
make **#73 (assay-brain)** ready to close.

### Build (fresh clone `~/Projects/Assay/skills`, branch `assay-brain-skill`) — done
- [x] `assay-brain/scripts/assay-brain` — adapted helper (rename, URLs, `assay-brain-wiki/-papers`, env vars); `chmod +x`.
- [x] `assay-brain/SKILL.md` — frontmatter + retrieval protocol/answering/trust boundary; provenance-cited.
- [x] `assay-brain/references/brain-map.md` — Assay cluster map + qmd cheatsheet + `wiki-query` delegation.
- [x] `README.md`, `install.sh` (+x), `.gitignore` — Assay-adapted (org, skill table, clone URLs).

### Verify (against the real brain — qmd 2.1.0, `assay-brain-wiki` live, 108 pages) — green
- [x] `doctor` resolves `~/Projects/Assay/brain`, qmd present, collection live, 108 pages.
- [x] `map` TOC + `map verifier` filter; `search "cloud control api"` → aws-cloud-control-api; `ask "…forge"` → reward-hacking.
- [x] `hot`; `env` exports `assay-brain-wiki`.
- [x] Graceful degradation (#73): no brain → `doctor` NOT FOUND (no crash), `search` clean guidance + exit 1; bogus path warns+falls back.
- [x] `./install.sh` symlinks skill→`~/.claude/skills` + CLI→`~/.local/bin`; idempotent; `bash -n` clean.
- [x] Focused PR on `AssayInc/skills` (#1) — references `assay-ops#86`, completes #73.

### assay-ops bookkeeping (this branch `e0-11-assay-skills-brain`)
- [x] `PROGRAM.md` + `ISSUES.md`: skill layer now partial (`AssayInc/skills` + `assay-brain`); #85 lock + 6 domain skills pending; recall note → `assay-brain`.
- [ ] Comment on #86 (landed / remaining) and #73 (assay-brain shipped → ready to close on merge).

### Review

- **Done:** new repo `AssayInc/skills` (PR #1) with `assay-brain` — `scripts/assay-brain` CLI
  (`doctor/hot/map/search/ask/env/setup`), `SKILL.md`, `references/brain-map.md`, plus `README.md` /
  `install.sh` / `.gitignore`. assay-ops `PROGRAM.md` + `ISSUES.md` updated to the in-flight state.
- **Approach:** faithful adaptation of the eval-tested `cleno-brain` template — proven script logic kept
  intact; only identifiers/URLs/collections/domain changed. The three non-mechanical adaptations (would be
  wrong to copy): qmd collections `assay-brain-wiki`/`-papers` (Cleno's brain coexists on this machine);
  the SKILL.md `description` (cloud/IaC RL-env verification + the DECISIONS.md-is-the-locked-floor note);
  the brain-map clusters. Verified `wiki-query` actually exists in the Assay brain before keeping the handoff.
- **Evidence:** acceptance suite green against the real brain (see PR #1 body); `bash -n` clean; install
  idempotent; #73 graceful-degradation paths exercised.
- **Scope/flag:** #86 deliberately **not** closed — its six domain skills + the #85 consumer-lock wiring
  remain. `assay-brain` (#73) is delivered, ready to close on merge. **Naming:** kept `assay-brain` (not
  `assay-query`) for consistency with #73 / `CLAUDE.md` / the brain's own `assay-brain-wiki` collection /
  the `cleno-brain` precedent — trivially renamable if preferred.
