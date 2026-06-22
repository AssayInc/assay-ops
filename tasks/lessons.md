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

## 2026-06-22 — use-the-librarys-official-mechanism-not-a-hand-roll
- **Mistake:** Built `@assayops/logger` from cached pino knowledge instead of the official docs: (1) a
  hand-rolled recursive `formatters.log` redactor that **leaked base/child bindings** and **flattened
  `Error`s** (lost message/stack), and (2) a hand-rolled `{ write }` capture for the tests. The founder
  caught both ("are you using the official docs?" → pino's built-in `redact`, and the official `pino-test`);
  a Codex `xhigh` re-check confirmed the leaks.
- **Rule:** For a library's **security/correctness primitive** (redaction, signing, canonicalization) **and
  its testing**, read the official docs FIRST and use the library's built-in mechanism — don't hand-roll
  from memory. pino specifically: redaction = the built-in **`redact`** (fast-redact path syntax; runs at
  serialization so it covers bindings + preserves `Error`s); testing = the official **`pino-test`**
  (`sink()` + `once()`); pretty = `transport: { target: 'pino-pretty' }`. A hand-rolled security primitive
  is a defect magnet (cloning the log object breaks Error/Date and misses bindings); the library's is
  battle-tested. The CLAUDE.md skill-preflight rule applies to **library config + test tooling**, not just
  new API calls.
- **Context:** `@assayops/logger` (PR #110); pino docs — redaction / pretty / testing (→ `pino-test`).
  Sharp instance of [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-21 — ground-in-decisions-and-brain-not-the-ai-written-issue
- **Mistake:** Started E1-1 (#26) from the issue's prose as if it were the spec, and made several
  field-level calls (a continuous reward, `RFC-3339-or-ns` timestamps, a `cloudformation` task tool) that
  were under-grounded — the reward one silently broke a `DECISIONS.md` §8 non-negotiable. The GitHub issues
  here are authored by **another AI agent** and can be wrong, stale, or missing a locked detail.
- **Rule (founder directive):** Before implementing ANY issue, **ground the requirements in `DECISIONS.md`
  + assay-brain + the plans first** — read the relevant `DECISIONS.md` sections and recall the brain for the
  rationale, then reconcile issue + floor + brain. **Don't trust the AI-written issue blindly**; it's an
  input, not the spec. When they disagree, the frozen floor wins and you comment on the issue. This is
  CLAUDE.md task-loop §1 ("Validate + ground"), promoted to a standing rule.
- **Context:** Founder feedback on E1-1 (#26). Pairs with [[frozen-floor-invariants-beat-issue-phrasing]]
  and [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-21 — frozen-floor-invariants-beat-issue-phrasing
- **Mistake:** Authored the `reward` field of the contract spine (E1-1 / #26) as a continuous bounded
  double `{type:number, minimum:0, maximum:1}`, following the issue + `ARCHITECTURE.md` phrasing "rewards as
  bounded doubles" — and rationalized it in the PR ("binary-ness is a verifier-compute invariant, the schema
  rule is JCS number-safety"). But `DECISIONS.md` locks **`reward ∈ {0,1}`** in three places incl. the **§8
  non-negotiables checklist**, and the cited `deterministic-verification` skill names a continuous
  "0.0–1.0 similarity score" as the **gameable anti-pattern**. The schema as written encoded that
  anti-pattern into the spine. The cross-model `/review` (Claude conf 9 + Codex gpt-5.5 xhigh) caught it.
- **Rule:** When a schema / type / constant encodes a domain invariant, ground the *value constraint*
  against `DECISIONS.md`'s frozen floor (especially the **§8 non-negotiables**) and the domain skills — not
  just the issue's or `ARCHITECTURE.md`'s prose. When the issue phrasing seems to *relax* a frozen-floor
  invariant ("bounded double" vs "∈ {0,1}"), the floor wins: encode the **stricter** constraint
  (`enum:[0,1]` is still a finite JCS-safe number, so it satisfies both — reconcile, don't pick one source).
  A PR "design call" that deviates from a §8 non-negotiable is a flag-and-confirm item, not a silent choice.
- **Context:** E1-1 (#26) reward-record schema; `DECISIONS.md` §1/§2A/§8; `deterministic-verification` +
  `reward-ledger-worm` skills. Pairs with [[verify-against-official-docs-and-skills-before-acting]] and the
  CLAUDE.md "settled — flag, don't silently deviate" rule.

## 2026-06-21 — secret-scanning-detection-is-not-push-protection
- **Mistake:** Tested GitHub push protection with a planted `google_api_key`. The push wasn't blocked
  (only an alert was created), so I concluded push-protection *enforcement* had a multi-day propagation
  lag — misreading GitHub's 2024 free-user **account**-rollout note ("a week or two") as repo-level — and
  proposed adding gitleaks / marking the AC pending. Wrong premise: `google_api_key` is **detection-only**
  (`hasPushProtection: false` in GitHub's supported-pattern data), so it was *expected* to land and alert.
  Push protection was active the whole time; the test **pattern** was the bug, not the config.
- **Rule:** **Secret-scanning detection ≠ push protection.** Not every detected secret type is
  push-protection-enforced — GitHub's supported-secret-patterns data carries a per-type `hasPushProtection`
  flag (`google_api_key` = false; Stripe / SendGrid / Slack / AWS = true). To prove push protection, plant
  a fabricated secret of a **push-protection-supported** type (checksum-free ones fabricate cleanly: Stripe
  `sk_live_…`, SendGrid `SG.…`, Slack `xoxb-…`) and capture the `GH013 … Push cannot contain secrets`
  rejection (push exit 1, ref rejected). An **alert being created means the secret landed** — that is
  detection, the *opposite* of a blocked push. Verify the per-pattern flag against GitHub's
  supported-patterns docs before testing; don't read the free-user account-rollout "week or two" as
  repo-level enforcement lag.
- **Context:** E0-4 (#21) secret-scanning AC; GitHub push-protection + supported-secret-scanning-patterns
  docs. Reinforces [[verify-against-official-docs-and-skills-before-acting]] and
  [[diagnose-unfamiliar-api-errors-before-theorizing]].

## 2026-06-21 — verify-against-official-docs-and-skills-before-acting
- **Mistake:** Applied two CI "hardening" changes from a Codex review (swap `bunx turbo` for named scripts;
  drop the `.turbo` cache) without first checking the vendored `turborepo` skill + official turbo docs —
  though the skill was already loaded this session. Grounding it only after the user pushed twice showed the
  official guidance refuted both: `globalDependencies` is turbo's prescribed mechanism for non-JS root
  manifests (so E0-2 was already sound) and turbo **recommends** CI caching (so dropping it was contra-idiom).
  The "fixes" were overengineering, then reverted.
- **Rule:** Before acting on a review finding or changing config/code in a domain that has a vendored skill
  or official docs (turbo, uv, AWS, Inspect AI, …), **verify against the primary source first.** A finding —
  Codex's, Claude's, or your own — is a *hypothesis to confirm*, not a fact: load the skill (CLAUDE.md
  skill-preflight table + `skills-lock.json`) and fetch the official docs when the claim is load-bearing,
  then decide. This covers config-soundness questions (caching/hashing/idiom), not just new API code. A
  60-second primary-source check beats the overengineer-then-revert cycle.
- **Context:** E0-2 (#19) CI review; `turborepo` skill + turborepo.dev/docs. Strengthens the CLAUDE.md
  Skill-preflight rule; pairs with [[local-aws-emulator-must-prove-read-api]] and
  [[reference-implementations-are-light-insight]].

## 2026-06-21 — never-merge-without-explicit-user-approval
- **Mistake:** Squash-merged PR #101 (E0-2 CI) myself after green CI + the gstack `/review`, reading
  `CLAUDE.md`'s "merge only on green CI verify + `/review`" as standing authorization. But the user had not
  personally reviewed the diff and never said "merge" — and a foundational change merging unseen (right
  after the review was found to have run at downgraded effort) was presumptuous. The user flagged it:
  "did you merge the PR without my review?"
- **Rule:** Merging is an outward, hard-to-reverse action — get **explicit user approval before merging any
  PR**, even on green CI + a passing `/review`. `CLAUDE.md`'s "merge on green + /review" states the *gate
  conditions*, not a blanket pre-authorization to merge unattended: present the PR as merge-ready and
  **wait for the user's go**. Same bar for revert / force-push / branch-protection changes. When unsure, ask.
- **Context:** E0-2 (#19) / PR #101. Pairs with the harness rule: confirm outward/hard-to-reverse actions
  unless durably + explicitly authorized.

## 2026-06-21 — codex-reviews-run-at-xhigh-not-the-skill-default-high
- **Mistake:** Ran the gstack `/review` Codex adversarial pass with the skill's hardcoded
  `-c 'model_reasoning_effort="high"'`, which silently overrode this repo's Codex standard of **`gpt-5.5
  xhigh`** (the `~/.codex/config.toml` default + the E0-11 two-pass convention). Model was right (gpt-5.5,
  inherited via no `-m`) but effort dropped a tier to `high`. The user caught it.
- **Rule:** For Codex passes in this repo (gstack `/review` Step 5.7, `/codex`, or a direct `codex
  exec`/`codex review`), explicitly pass **`-c 'model_reasoning_effort="xhigh"'`** — the gstack templates
  pin `high`, and `-c` overrides the config default, so xhigh does NOT apply unless you set it. The
  high-stakes-review standard here is **gpt-5.5 xhigh**. Confirm the run banner shows `reasoning effort:
  xhigh` before trusting the pass.
- **Context:** E0-2 (#19) CI review. gstack `/review` Step 5.7 Codex command; `~/.codex/config.toml`
  (model=gpt-5.5, effort=xhigh).

## 2026-06-20 — no-speculative-defense-or-absence-narration
- **Mistake:** On `localstack-smoke.yml` I added a fork-PR `if:` gate (public-repo boilerplate) to a
  **private, fork-less** repo where forks can't occur, then after removing it added a comment narrating the
  absence ("No fork-PR gate: the repo is private..."). The user cut both — speculative defense for a
  scenario that can't happen, then narration of a non-decision.
- **Rule:** Tailor borrowed patterns to THIS environment — don't paste a public-repo idiom into a private
  repo or guard a case that can't occur (YAGNI). And never comment to explain the **absence** of something;
  comments justify what IS present (non-obvious boundaries, security/trust rules), not what isn't. Default
  to shipping less. Same root as over-stating the LocalStack licensing and deferring to a reviewer without
  checking the primary source: **verify and minimize before adding or asserting.**
- **Context:** `.github/workflows/localstack-smoke.yml` (E0-3). Pairs with the YAGNI / lean-docs bar in
  `CLAUDE.md`/`AGENTS.md`.

## 2026-06-20 — local-aws-emulator-must-prove-read-api
- **Mistake:** Assumed the current `localstack/localstack` image still provided a free, tokenless
  community dev loop for a commercial/private repo, then treated generic "LocalStack replacement"
  options as plausible substitutes before proving the verifier's actual read path.
- **Rule:** Before choosing or wiring a local AWS emulator, verify the exact API the verifier needs
  against current primary docs and a smoke test. For AssayOps that means Cloud Control
  `GetResource`/`ListResources` or the specific CloudFormation read/drift API in the AC, not just
  "S3 works" or "Terraform/CDK compatible." Current LocalStack requires an auth token and commercial
  use needs a paid plan; Moto, Floci, MiniStack, fakecloud, and Testcontainers are not drop-in
  replacements unless they pass the exact read-path smoke. If cost-free conflicts with that, flag the
  issue/decision instead of silently changing the substrate.
- **Context:** E0-3 local AWS dev loop / issue #20; LocalStack 2026 single-image auth/licensing change;
  Floci and MiniStack passed S3 smoke but failed Cloud Control `GetResource`.

## 2026-06-19 — shipped-docs-no-issue-numbers-no-narration
- **Mistake:** The `AssayInc/skills` README (and the eval `RESULTS.md`) carried GitHub issue/PR numbers
  (`AssayInc/assay-ops#86`, `spike #61`) and status-log / AI-chat narration ("All five skills now live here",
  "more skills are being distilled"). The user cut it: don't mention issues inside READMEs, and remove
  AI-chat/status narration from committed docs.
- **Rule:** Shipped **reference** docs others read — READMEs, eval `RESULTS.md`, any doc that isn't a
  work-tracker — stay clean and timeless: **no GitHub issue/PR numbers**, no changelog/status narration
  ("now live here", "being distilled"), no conversational AI framing. State what *is*, factually; let the
  table/content be the record. When a finding *is* that something leaked such refs, describe it generically.
  **Distinction:** issue numbers DO belong in the **work-trackers** (`PROGRAM.md`, `ISSUES.md`, lessons) —
  just not in shipped reference docs or `CLAUDE.md`. Extends [[claude-md-is-lean-no-issue-numbers]] beyond
  the constitution.
- **Context:** `AssayInc/skills` README + `evals/*/RESULTS.md` (the E0-11 / #86 homegrown skills).

## 2026-06-19 — claude-md-is-lean-no-issue-numbers
- **Mistake:** Bloated `CLAUDE.md`'s skills section with a flat enumeration of every source repo + per-skill
  annotations + GitHub issue/epic numbers (`E0-10/#85, landed`, `#86`, `#73`, `T7`). The user cut it: issue/epic
  numbers "do not add any value" in `CLAUDE.md`, and the repo list just duplicated `skills-lock.json`.
- **Rule:** `CLAUDE.md` is for what an agent can't infer from the repo — short, specific, actionable. **No GitHub
  issue/epic numbers** (`#N`, `E0-N`, `T`/`I` labels); state decisions as plain facts (date if needed) and link a
  real anchor (`DECISIONS.md §N`, `ISSUES.md`) when detail lives elsewhere. The skill inventory lives in
  `skills-lock.json` (source of truth) and auto-loads by description — don't re-list sources in `CLAUDE.md`. For
  fast-moving APIs use a **Domain → Skill → Surface preflight table** (Cleno pattern). Prune `CLAUDE.md` like code.
  Pairs with [[claude-md-serves-all-agents-no-dedupe]] — completeness vs conciseness; aim for high signal, low noise.
  (Issue numbers DO belong in work-tracking files — `PROGRAM.md`, `ISSUES.md`, lessons — just not the constitution.)
- **Context:** E0-10 (#85) `CLAUDE.md` skills section. Refs: `brain/raw/articles/The File That Turns Claude Code
  Into Your Best Engineer`, Cleno `CLAUDE.md` (`#skill-preflight-fast-moving-apis`).

## 2026-06-19 — verify-skill-absence-beyond-the-registry
- **Mistake:** Concluded "no official Inspect AI skill exists" from `npx skills find` (registry) searches
  alone, and judged a repo's officialness by its GitHub org slug. Both wrong: `meridianlabs-ai/inspect-skills`
  exists (not registry-indexed — found only by checking the maintainer's GitHub directly), and Meridian Labs
  now maintains `inspect_ai` even though the repo still sits under `UKGovernmentBEIS`. The user flagged the
  framing ("what do you mean no official skills exist") and `/review` caught the concrete miss.
- **Rule:** Before asserting a tool/skill "doesn't exist" or "isn't official," look beyond the skills.sh
  registry: check the maintaining project's own GitHub org and a `<tool>-skills` repo, and read who actually
  *maintains* the upstream (not just the repo's org slug) to judge first-party. `npx skills find` indexes only
  a subset; a negative there means "not in the registry," not "doesn't exist." Phrase absence as "none found
  in <where I looked>," and prefer under-claiming a gap (flag for verification) over asserting one.
- **Context:** E0-10 (#85), the Inspect AI (E13) lane. Pairs with [[skills-sync-hygiene]] + the prefer-official rule.

## 2026-06-19 — skills-add-default-agent-targeting
- **Mistake:** Installed a skill with `npx skills add <src> -a '*'`, reading `*` as "this project's
  agents." It means **all 72 agents skills.sh knows**, so it vendored the skill into dozens of stray
  per-agent dirs (`agent/`, plus gitignored ones like `.aider`/`.cursor`) instead of the repo's 3-dir
  layout — and quietly, since many of those dirs are gitignored and never show in a plain `git status`.
- **Rule:** Add skills with the **default agent targeting** (omit `-a`): on a project that already has
  `.agents/skills/` + `.claude/` + `.hermes/`, the default extends those exact dirs (a real
  `.agents/skills/<name>` dir + mode-`120000` symlinks in `.claude/`+`.hermes/`). Never `-a '*'`. After
  **every** `skills add`, run `git status --porcelain` and confirm ONLY `.agents/`, `.claude/`, `.hermes/`,
  and `skills-lock.json` changed; any other new dir is an overshoot — back it out
  (`npx skills remove <name> -a '*' -y`, then `rm -rf` stragglers) and re-add without `-a '*'`. Preview
  multi-skill repos with `--list` first and install only the needed skill(s) (`--skill <name>`), not the
  whole repo.
- **Context:** E0-10 (#85), `npx skills add` (the committed skill layer). Recurs for the remaining
  official packs (AWS / Terraform / OpenEnv + `skill-creator`). Pairs with [[skills-sync-hygiene]].

## 2026-06-19 — eval-is-part-of-the-skill
- **Mistake:** Built the `assay-brain` skill, verified its CLI by hand, and called it done — scoping the
  `evals/` tree out as a "follow-up." That shipped a *verification* skill with no verification that it
  actually triggers or improves answers. The user caught it ("you missed the eval... it validates the
  skill is working").
- **Rule:** A skill is not done until its eval is **authored AND run**. Follow the `skill-creator` loop:
  `evals.json` (3+ realistic cases + expectations) + `trigger-eval.json` (≈10 should / 10 should-not) +
  a with-skill/without-skill A/B (subagents) + a `claude -p` trigger probe (`probe_precise.py`), with the
  measured outcome in `RESULTS.md`. For verification-infra especially, an unvalidated skill violates
  "prove it or flag it." Also run `skill-creator/scripts/quick_validate.py` and check the SKILL.md
  `description` against the agentskills.io **1024-char limit** before claiming done.
- **Context:** E0-11 (#86) / `AssayInc/skills#1`. The eval also caught a real defect the hand-check and
  code-review both missed — the `description` was 1490 chars (over 1024); `quick_validate.py` rejected it.

## 2026-06-18 — claude-md-serves-all-agents-no-dedupe
- **Mistake:** Trimmed the gstack skill list + routing out of `CLAUDE.md`, reasoning it duplicated
  `~/.claude/CLAUDE.md` and was context bloat.
- **Rule:** Never dedupe the project `CLAUDE.md`/`AGENTS.md` against Claude-only global config or plugin
  skills. `AGENTS.md` is read by non-Claude agents (Codex) that never load `~/.claude/CLAUDE.md`, so
  anything every agent needs — the full gstack skill list + routing, the `/browse`-only rule, operating
  rules — must live in this repo's file. Default to **completeness** for cross-agent content; only omit
  what is genuinely irrelevant to this repo (UI, machine-local gbrain config).
- **Context:** E0-6 (#18) `CLAUDE.md`; the user caught the missing gstack section. The committed skill
  *layer* (skills.sh / `skills-lock.json`) is separate and prefer-official (#85/#86) — that's not what was
  missing; the per-developer gstack workflow layer was.

---

### Durable lessons seeded at bootstrap

The lessons below were seeded at bootstrap (not yet earned from a correction here) — general doc-hygiene,
operating-layer, strict-TS, and debugging rules that apply to this repo. Prune any that stop being true.

## 2026-06-18 — reference-both-constitution-names
- **Mistake:** Shared docs referenced sections "in `CLAUDE.md`" only.
- **Rule:** When a shared/committed file points at the constitution, write `CLAUDE.md`/`AGENTS.md` — Codex
  knows it only as `AGENTS.md`. This repo is multi-agent; never write docs as if Claude is the only reader.
- **Context:** Pairs with [[claude-md-serves-all-agents-no-dedupe]] above.

## 2026-06-18 — committed-docs-are-standalone
- **Mistake:** Wrote "Option A / Option B" and chat rationale ("as we discussed", "I'd lean") into a
  committed runbook — framing that only meant something inside the chat that produced it.
- **Rule:** Committed docs (`DECISIONS.md`, `docs/`, `CLAUDE.md`, runbooks) are standalone — the reader
  has no conversation context. State the decision and the steps; cut option-menus, hedging, and
  already-rejected alternatives. Once a choice is made, write it as the practice, not a comparison.
- **Context:** Applies to all of assay-ops's committed docs (`DECISIONS.md`, `docs/`, runbooks).

## 2026-06-18 — reference-implementations-are-light-insight
- **Mistake:** Turned a reference repo's patterns into prescriptive "borrow / avoid" guidance in a
  committed doc.
- **Rule:** Analog products and reference implementations (RL-env companies, leaderboards, repos under
  `../brain`) are **light insight only** — they may not follow current official docs. Build from the
  **official skills/docs + `DECISIONS.md`** as the source of truth (prefer-official, #85); cite an analog
  only as "one possible shape, verify against official docs." Don't encode their patterns as rules.
- **Context:** Reinforces the prefer-official skill layer (#85/#86).

## 2026-06-18 — no-social-links-in-agent-docs
- **Mistake:** Cited an X/Twitter post as a markdown link in the constitution.
- **Rule:** Agent-facing docs (`CLAUDE.md`/`AGENTS.md`, `DECISIONS.md`, `tasks/`) don't carry login-walled
  or rot-prone external links (X, LinkedIn, etc.) — agents can't resolve them and they decay. Name the
  source in plain text; keep the real citation in the vendored artifact (skill, brain page) it attributes.
- **Context:** Why `CLAUDE.md` attributes the Karpathy guidelines in plain text, not a link.

## 2026-06-18 — gh-cli-first-for-pr-workflow
- **Mistake:** Reached for the GitHub connector/MCP for PR work even though the repo's working path is
  `gh`; got a 404 and an avoidable fallback step.
- **Rule:** For PR creation, inspection, check-watching, and body edits, use the **`gh` CLI** as the
  primary tool. Try connector/MCP GitHub tools only when a task explicitly asks or `gh` is unavailable.
- **Context:** Issues + PRs are gh-driveable.

## 2026-06-18 — contextual-typing-over-array-assertions
- **Mistake:** Refactored inline empty literals into a factory whose inferred return type dropped the
  value-type context, forcing `[] as T[]` — a bare assertion where none was needed.
- **Rule:** An empty collection literal gets its element type from an explicit annotation on its container
  (a `Map` value type, a variable type, or a function's declared return type), never an `as T[]`
  assertion. A factory with an inferred return type loses that context — annotate its return or keep the
  literal inline. Assertions belong only at I/O boundaries behind a runtime check (`CLAUDE.md` → Toolchain).
- **Context:** Strict-TS, never-`any` repo (`CLAUDE.md` → Toolchain).

## 2026-06-18 — update-program-state-before-landing
- **Mistake:** Merged a PR while `PROGRAM.md` still described the branch as an open follow-up, leaving the
  handoff stale immediately after landing.
- **Rule:** Before merging a state-changing PR, update `PROGRAM.md` **in the branch** — remove the landing
  `Right Now` entry and add the final `Recently Landed` entry with the PR number + merge commit. Don't
  rely on a main-only cleanup after merge.
- **Context:** The task loop's "update `PROGRAM.md` in the same PR" step.

## 2026-06-18 — skills-sync-hygiene
- **Mistake:** A skills.sh upstream sync silently dropped security-relevant excludes/validation from a
  vendored skill's `resources/*`; the lock file hashes only `SKILL.md`, so nothing flagged it.
- **Rule:** After any **skills.sh** install or sync (the committed skill layer arriving in #85/#86),
  `git diff` the skill's full vendored dir (all non-`SKILL.md` files) — especially executable scripts — before committing. Treat reduced
  excludes or validation in vendored scripts as a regression to restore and report upstream, never a
  neutral update.
- **Context:** Directly relevant to the incoming skill layer (E0-10/E0-11, #85/#86).

## 2026-06-18 — held-out-data-residency-includes-derived-uses
- **Mistake:** Sensitive ground-truth values get copied into in-repo tests/docs/PR bodies, reasoned as
  "precedent" — then need a git history rewrite to scrub.
- **Rule:** The residency rule for **gold trajectories + held-out eval** (private, never committed —
  `DECISIONS.md` I11; contamination control + the moat) covers **every in-repo surface** — tests, docs,
  comments, commit messages, PR bodies — and **derived values** that reconstruct held-out content. In-repo
  tests use synthetic fixtures; real/held-out data stays in the private store. Scrub **before** the first
  push — a history rewrite after publication is damage control, not prevention.
- **Context:** The data-hygiene expression of the §6 contamination check.

## 2026-06-18 — diagnose-unfamiliar-api-errors-before-theorizing
- **Mistake:** An unfamiliar vendor error string (e.g. a `400`) gets read literally, a wrong cause
  theorized, and the user sent on an external errand — when a differential probe would have located the
  real failure layer.
- **Rule:** Before theorizing from an unfamiliar API/cloud error string — and **especially** before
  sending the user on an external errand based on it — run a **differential diagnostic** (vary
  headers/inputs/permissions/region, compare responses) to locate the real failure layer. Don't
  over-interpret an error's literal text; confirm the mechanism with evidence.
- **Context:** AssayOps touches AWS / Cloud Control / LocalStack / OpenEnv across an account boundary —
  many unfamiliar error surfaces, and the verifier reads B-side state.

## 2026-06-18 — nested-workspace-claude-md-stays-minimal
- **Mistake:** A per-workspace `CLAUDE.md` restated root facts and narrated harness merge behavior.
- **Rule:** If a nested workspace `CLAUDE.md`/`AGENTS.md` is ever added (e.g. under `ts/`, `py/`, or a
  package), it carries **only** workspace-specific, non-inferable guidance. Never narrate harness behavior
  (Claude Code merges cwd→root; Codex merges `AGENTS.md` up-tree) and never restate cross-cutting facts
  that live in root — those belong in root's Architecture/Toolchain, stated once.
- **Context:** AssayOps is polyglot (`ts/` + `py/`) — nested constitutions are plausible; keep them minimal.
