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

## 2026-06-24 — delegate-equality-to-the-signed-canonical-form-but-guard-its-input-domain
- **Mistake:** Refactored the diff-ir reward core (#34) to define value **equality and validity** by RFC 8785
  JCS (`rfc8785.dumps` — the form the record is signed with). Equality was right; validity-as-"does it
  canonicalize?" was not. A Codex xhigh re-review found `rfc8785.dumps` canonicalizes a builtin **subclass** by
  calling `int()`/`list()`/… on it (USER code), so `LyingInt(9)` (== 9) with `__int__→1` canonicalizes 9 to
  `b"1"` — a false reward 1, nondeterministic. A canonicalizer **coerces** adversarial input, doesn't reject it.
- **Rule:** Delegate the *equality semantics* to the system's canonical/signed form (no hand-rolled comparator;
  `90==90.0`, `True≠1` fall out free, grade ↔ digest agree by construction). But guard the *input domain* to
  exact types (`type(x) is T`, never `isinstance`) **before** canonicalizing — restrict to the library's
  documented domain; never pass an open `object` and rely on undocumented coercion. Still less code, and safe.
- **Context:** #34 / PR #145; `_require_exact_json`/`_canonical_bytes`/`_values_equal`. rfc8785's subclass
  coercion is **undocumented** (verified vs its docs) → guard, don't rely. Caught only by the xhigh re-review of
  the *fixed* code ([[re-review-fixed-code-with-codex-xhigh-and-recheck-the-finding-scope]]); companion to
  [[harden-to-the-precise-domain-semantics-not-an-over-general-rule]].

## 2026-06-24 — harden-to-the-precise-domain-semantics-not-an-over-general-rule
- **Mistake:** Fixing the value-type-collapse false-reward-1 in the diff-ir reward core (#34), the real bug
  was Python `==` collapsing `True == 1` (a JSON **boolean** graded equal to a **number**). I
  over-generalized the fix to **full type-strictness** (`type(a) is not type(b)`), which also made `int`
  ≠ `float` — so `90` vs `90.0` graded as a **drift**. But JSON has one number type and RFC 8785 JCS
  canonicalizes `90` and `90.0` identically, so that's a **false-negative** (a correct deploy scored 0),
  not a real divergence. The founder caught it ("no over-engineering, right? fix only what's not right") —
  I'd flagged it myself once asked, but shipped it over-strict first.
- **Rule:** When hardening a correctness/trust check, match the **precise domain semantics** — don't reach
  for the broadest rule that happens to cover the failing case. For JSON-value equality: `bool` is distinct
  from numbers (a boolean is not `1`), but `int`/`float` of the same value are **equal** (one JSON number
  type; JCS-canonical). The broadest rule (all-types-strict) "passes the failing test" but introduces a NEW
  failure class (false negatives), which poisons training just like a false positive — **a fix stricter than
  the ground-truth semantics is itself a bug.** Keep the genuinely bug-preventing hardening; cut the
  over-reach (defense-in-depth that prevents real bugs vs strictness beyond the correct semantics). And
  **TDD only catches over-reach you enumerate** — it "passed the failing test" because the *adjacent-correct*
  case wasn't tested, so a reviewer (not the suite) caught it; when hardening a rule, lock that adjacent case
  with its own test (`90 == 90.0` is in-sync), not just the failing one.
- **Context:** E3-1 (#34) / PR #145; the value comparison + NORMALIZATION.md. The over-strict cut later
  triggered replacing the hand-rolled comparator entirely with JCS delegation
  ([[delegate-equality-to-the-signed-canonical-form-but-guard-its-input-domain]]). Pairs with KISS/YAGNI.

## 2026-06-24 — proactive-primary-docs-and-all-craft-skills-are-part-of-done-not-a-founder-prompt
- **Mistake:** Presented the #34 reward core as done after grounding against the **skills** + TDD + 6 review
  passes — but had NOT (a) opened the **primary** Pydantic docs myself for the load-bearing behaviors
  (after-mode `field_validator` returns-and-stores the value; `frozen` doesn't deep-freeze a dict), nor (b)
  validated against two applicable craft skills (`python-error-handling`, `python-design-patterns`). The
  founder asked the standing three questions; closing the gaps surfaced real refinements
  (`UntrustedInputError(ValueError)`; explicit `mode="after"`).
- **Rule (recurring founder directive):** The grounding pass is **part of "done," done proactively** — not when
  asked. Before claiming a build complete: open the **primary docs yourself** for each load-bearing library
  behavior (a skill / green test / Codex pass are all **secondary**), and **validate against every applicable
  craft skill**, stating which are N/A and why. Cross-model review hardens correctness; it does **not**
  substitute for either. Pairs with [[ground-in-official-docs-first]] +
  [[validate-against-all-relevant-vendored-skills-not-just-the-api-skill]].
- **Context:** E3-1 (#34) / PR #145; primary Pydantic v2 docs (validators "return the validated value"; "Faux
  immutability" Caution; `exclude_none`).

## 2026-06-24 — dont-strip-cheap-fail-closed-validations-to-win-an-over-fixing-argument
- **Mistake:** On #75 (the golden generator — a proof-critical content-addressed verifier) I first **piled on**
  validations chasing every Codex adversarial finding, then, when the founder asked "are you over-fixing?",
  started **removing working validations + their tests** because a proportionality reviewer (Opus) framed them
  as disproportionate. The founder caught it: "if the tests and the validations are important, keep them — why
  did you remove them?" Both moves were the same error in opposite directions — letting a reviewer's verdict
  drive me instead of holding judgment. The validations (reject a `set`/subclass/surrogate/non-finite float in
  a property; re-check after construction) are **cheap, fail-closed, runtime-free, and protect the load-bearing
  invariant** (a deterministic content-address) — they belong, even though each defends a low-probability or
  trusted-corpus input.
- **Rule:** For the proof-critical core, a **cheap fail-closed validation protecting a load-bearing invariant
  STAYS** — "a plausible-but-wrong verifier is worse than none" (DECISIONS.md stance). Do **not** delete a
  working safety check + its test to lower a test count or win a "proportionality" argument; a check that can
  only reject *pathological* input (never a legitimate golden) costs ~nothing and is pure insurance. Reviewer
  verdicts are **inputs, not directives** — don't let an adversarial reviewer ping-pong you to "add everything"
  and a proportionality reviewer ping-pong you to "cut everything"; weigh each finding's cost vs. what it
  protects yourself. The legitimate answer to "over-fixing" is: keep the protective checks, **clarify intent**
  so they aren't silently weakened later, and cut only genuine speculative abstraction / true redundancy — not
  safety. Where two strong reviewers disagree on a real tradeoff, surface it as the user's call; never
  unilaterally strip safety.
- **Context:** #75 / PR #146 — founder flagged removing validations/tests after an over-fixing question.
  Reverted; kept all 35 tests + validations. Pairs with
  [[ground-and-validate-craft-skills-before-claiming-done-not-when-asked]] (don't over-defer to reviews).

## 2026-06-24 — negative-control-restore-with-a-file-backup-never-git-checkout
- **Mistake:** Running a negative control on #75 (temporarily break code → prove the test fails → restore),
  I restored with `git checkout -- src/assayops_verifier/models.py src/assayops_verifier/golden.py`. That
  reverts to **HEAD (the last commit)**, not to my working tree — so it silently wiped **all the uncommitted
  fixes** from that turn (two rounds of adversarial-review fixes), not just the one-line negative-control
  patch. I only caught it because the harness flagged the files as reverted, then had to reconstruct both
  files from memory and re-`Write` them.
- **Rule:** A negative control mutates **uncommitted** code in place; restore it from a **file backup**, never
  from git. Before the patch: `cp <file> /tmp/<file>.bak`; after: `cp /tmp/<file>.bak <file>` (or keep the
  original text in the patch script and write it back). **Never `git checkout -- <file>` / `git restore` while
  there are uncommitted changes you want to keep** — it discards them to HEAD. (If you must use git to revert
  a negative-control patch, commit the good state first so HEAD *is* the good state.) Pairs with the
  negative-control discipline ([[no-any-ban-targets-our-data...]] and the structlog/redaction negative
  controls) — the control is only safe if the restore is non-destructive.
- **Context:** #75 / PR #146, the Opus-4.8-max + Codex-xhigh adversarial-review fixes; the `git checkout`
  reverted models.py/golden.py to `d35cf3c`, dropping that turn's fixes. Recovered by re-`Write`-ing the final
  files. Forward fix: every subsequent negative control used `cp`-backup restore.

## 2026-06-24 — ground-and-validate-craft-skills-before-claiming-done-not-when-asked
- **Mistake:** Presented #75 (the golden generator) as merge-ready after grounding only against the
  **API/feature skills** (`pydantic-v2`, `uv`) + the empirical gate + the cross-model `/review`. I had **not**
  proactively (a) validated the implementation against the applicable **Python craft skills** the repo vendors
  (`python-type-safety` / `python-error-handling` / `python-testing-patterns` / `python-design-patterns`), nor
  (b) opened the **primary docs** for the load-bearing library behaviors (pydantic's `model_dump(mode="json")`
  inf/nan→`null` default, strict `list`→`tuple` rejection, the rfc8785 integer domain). The founder had to ask
  "did you ground on official docs and skills? did you use the python skills available?" — only then did I. It
  paid off (confirmed the design is skill-aligned, surfaced a `parametrize` test improvement, and proved my JCS
  int bound is **exactly** rfc8785's `_INT_MAX = 2**53−1`), but it should have come **before** I claimed done.
- **Rule:** Validating against **all applicable vendored craft skills** + grounding **load-bearing library
  behavior against primary docs (or an empirical probe of the pinned lib)** is a **pre-completion / pre-PR
  checklist item — proactive, not a reaction to being asked**. The API skill is necessary, not sufficient: for
  Python in a domain with craft skills, load + validate against the applicable ones and **state which apply vs
  N/A** (here N/A with reasons: resilience/async/configuration/observability — pure sync compute, no
  I/O/secrets/logging yet). A green gate + a skill's doc-citation are **secondary** — for the bytes a
  content-address covers / what serializes to `null` / a coercion rule, open the primary source yourself or
  probe the pinned library and cite it. "I ran the cross-model review" is not a substitute for that pass.
- **Context:** #75 / PR #146 — founder's three grounding questions after the PR was presented ready. Sharpens
  [[validate-against-all-relevant-vendored-skills-not-just-the-api-skill]] + [[ground-in-official-docs-first]] +
  [[a-subagents-doc-citation-is-secondary-verify-the-primary-source-yourself]] with the proactive/pre-PR trigger.

## 2026-06-24 — act-decisively-on-airtight-code-evidence-dont-bounce-it-back
- **Mistake:** Grounding #140 against `origin/main`, I proved **three ways** that quicktype is already globbed
  (`git show origin/main:justfile` → `contracts/schemas/*.schema.json`; PR #139's squash `e641784` diff =
  explicit-list → glob; `a4be645` not an ancestor of main) — contradicting the founder's correction comment.
  But after laying out the receipts I still **asked the founder to re-run the check and "confirm before I open
  the PR," and held the PR.** The founder pushed back ("Why don't you just check yourself? I just did it") —
  they'd already verified it and wanted me to proceed on my own airtight evidence, not bounce the verification
  back to them.
- **Rule:** When I've **airtight-verified a fact against the code** (especially after being told to "ground
  from the code"), **flag the contradiction with receipts and then PROCEED on that evidence** — don't stall
  asking the founder to re-confirm what I've already proven. Confirmation-seeking on a settled, triple-checked
  fact reads as not trusting my own grounding and wastes the founder's time. Reserve "stop and ask" for genuine
  ambiguity I **can't** resolve from the code/docs (a real scope/judgment call) or an outward irreversible
  action (a **merge** still needs the explicit go — [[never-merge-without-explicit-user-approval]]). Opening a
  PR on verified evidence does **not**. Flag-and-proceed, not flag-and-wait.
- **Context:** #140 / PR #144 — the quicktype-glob status (the review comment was stale vs `origin/main`).
  Sharpens [[ground-in-decisions-and-brain-not-the-ai-written-issue]] +
  [[verify-against-official-docs-and-skills-before-acting]] (verify, *then act*); pairs with
  [[never-merge-without-explicit-user-approval]] (the one outward step that still waits).

## 2026-06-24 — codex-sandbox-has-no-github-network-paste-content-inline
- **Mistake:** A Codex `gpt-5.5` xhigh review needed the bodies of issues #141/#53; every run hit
  `error connecting to api.github.com` — first with a `gh issue view ...` prompt, and **again after I retried
  steering it to `gh`**. I first logged the cause as "didn't tell it to use `gh`." **Wrong root cause:** `gh` is
  authenticated and works in *my* shell, but **Codex's `codex exec -s read-only` sandbox has no network
  egress** — `gh`, the GitHub connector/MCP, and raw `curl` to api.github.com all fail there. Telling Codex to
  "use `gh`" cannot fix a missing network; only its `--enable web_search_cached` worked (it AWS-fact-checked
  fine, just couldn't read the GitHub artifacts).
- **Rule:** A Codex review run **cannot reach GitHub** (no api.github.com egress in the sandbox). So:
  - **GitHub-only content** — issue/PR **bodies**, descriptions, review **comments** — must be **pasted inline**
    in the Codex prompt. That is the reliable method, not `gh` / the connector / `curl`.
  - The **code diff** Codex CAN obtain **locally** (no network): have it run `git diff origin/<base>...HEAD` /
    `git log` under `-C <repo>` (it did this successfully for the `DECISIONS.md` diff). Prefer local git for the
    diff; inline for anything GitHub-resident.
  - Don't spend a review pass instructing Codex to "use `gh`" — up front, hand it the diff via local git and
    paste any GitHub-only bodies inline.
- **Context:** #80 / PR #138 final pre-merge re-review (4 Codex xhigh passes; the inline pass returned "merge
  as-is"). **Supersedes** the earlier "tell it to use `gh`" framing — that was the wrong diagnosis.
  [[gh-cli-first-for-pr-workflow]] still holds for *my own* shell (gh is the right PR tool there); it just
  doesn't apply inside Codex's sandbox. Pairs with [[codex-reviews-run-at-xhigh-not-the-skill-default-high]].

## 2026-06-24 — todo-md-is-ephemeral-durable-records-go-elsewhere
- **Mistake:** Resolving the #80 spike, I recorded durable outputs (a surfaced T7 requirement, the proposed
  `DECISIONS.md` note) in `tasks/todo.md` (+ ISSUES.md) and treated that as sufficient tracking. The founder
  flagged it: `tasks/todo.md` is **overwritten/regenerated every session**, so anything living only there is
  lost; and a durable decision/requirement left only in an issue **comment** gets missed too.
- **Rule:** `tasks/todo.md` is an **ephemeral per-session scratchpad** — never the system of record. Route
  durable outputs to their durable home every time: a **GitHub issue** (created, grounded with how-to-fix, and
  wired to the board + parent epic per [[new-issues-must-join-the-board-and-parent-epic]]) for actionable
  follow-up work; **`DECISIONS.md`** for a settled rule/finding (flag first, land it on founder ratification —
  don't leave a floor-refining result as a proposal buried in a comment); **`ISSUES.md`/`PROGRAM.md`** for
  cross-cutting context + handoff. A spike's conditions and any newly-surfaced requirement (e.g. a new T7
  responsibility) become **tracked issues**, not just comments or an ISSUES.md bullet.
- **Context:** #80 / PR #138 — founder feedback. Created #141 (verifier-side read-coverage enforcement) +
  updated #53 (T7 closed-world create-allow-list) + landed the resolved-`[spike]` note in `DECISIONS.md` §1.
  Pairs with [[create-and-link-the-tracking-issue-before-opening-a-PR]] + [[update-program-state-before-landing]].

## 2026-06-24 — change-claude-md-with-extreme-caution
- **Mistake:** Two *opposite* errors on the `CLAUDE.md` skill-preflight rule (#116). (1) **Over-added** — a
  clarity clause PLUS the 4 craft-skill names the preflight **table already lists** (duplication), atop a
  pre-existing meta-aside (*"a repeated correction — see lessons.md"*). CLAUDE.md loads **every session for
  every agent (Claude Code AND Codex)**, so that compounds into bloat; the founder flagged it. (2) Then
  **over-corrected** — reverted the *whole* clause, including the load-bearing bit: the rule's prose read
  library-only, which is what misdirected me into checking just the boto3 API skill and not the craft skills.
  The founder wanted that clarity KEPT.
- **Rule:** CLAUDE.md changes need **extreme caution** (every-session, every-agent load) — default to leaving
  it. Cut bloat: **duplication of the preflight table** and **meta-narration** (a correction's backstory
  belongs in `tasks/lessons.md`, not the constitution). BUT a **surgical fix to prose that misdirects an agent
  IS warranted** — distinguish "duplicating what's already there / narrating" (cut) from "fixing a misleading
  instruction" (keep, tightly). Prefer **length-neutral** edits (drop a low-value bit when adding a needed
  one); the *preventing rule* itself still lives in lessons.md.
- **Context:** #116 / PR #134 — final state: re-added the clause naming only the craft *dimensions* (the
  table resolves them to skills) + dropped the meta-aside. Sharpens [[claude-md-is-lean-no-issue-numbers]]
  with a change-bar; pairs with [[claude-md-serves-all-agents-no-dedupe]].

## 2026-06-23 — validate-against-all-relevant-vendored-skills-not-just-the-api-skill
- **Mistake:** Building the LocalStack boto3 smoke (E17-F1 / #116) I grounded the boto3 mechanics against
  `aws-sdk-python-usage` (the API skill) but **skipped the Python craft skills the repo vendors**
  (`python-resilience`, `python-error-handling`, `python-testing-patterns`, `python-type-safety`). The founder
  caught it ("did you validate the implementation against our python skills?"). Validating after the fact
  surfaced real fixes: my `_with_retry` caught **broad `Exception`** (a resilience/error-handling anti-pattern)
  and **hand-rolled what boto3 already provides** (`Config(retries=...)`), so I dropped it for the library's
  bounded retries; `python-testing-patterns` → pytest fixtures; `python-type-safety` confirmed the
  `Any`-at-untyped-boto3-boundary is idiomatic (best practice #9).
- **Rule:** The CLAUDE.md skill-preflight rule covers **all the relevant vendored skills for the surface, not
  just the API/library skill.** Before writing Python in a domain the repo has craft skills for, validate the
  design against the applicable ones FIRST — retry/transient logic → `python-resilience` (+ the verifier's
  `deterministic-verification` transient/genuine rule); exceptions → `python-error-handling`; test structure →
  `python-testing-patterns`; the `Any` boundary → `python-type-safety` — and state which apply vs are N/A
  (with reasons). A **hand-rolled retry/validation/redaction is the recurring tell** to reach for the library's
  mechanism instead ([[use-the-librarys-official-mechanism-not-a-hand-roll]]). Pairs with
  [[ground-in-official-docs-first]].
- **Context:** E17-F1 (#116) / PR #134; the boto3 LocalStack smoke. The founder also steered the structure:
  **"re-home built TS for the Python core"** (the issue title) + the logger precedent (keep TS only for a
  genuine consumer surface) meant the smoke should be **consolidated TS→Python in `infra-local`**, not shipped
  as a parallel `read-smoke` package with the TS smoke kept. When built TS has **no consumer surface, re-home
  it (don't duplicate)** — read the issue title's intent and apply the precedent, don't default to the
  additive smallest-change. (Consolidating then exposed a CI-lane bug Codex xhigh caught: a uv package outside
  `py/**` was routed to the no-uv TS lane — see PR #134. **Forward rule:** a uv package belongs **under
  `py/packages/`** so the `./py/**` glob routes it to the py lane automatically; at the repo root it needs
  special-case `--filter` flags that `bun run verify` masks by running both lanes together. Resolved
  structurally in PR #136 by relocating `infra-local` → `py/packages/infra-local`.)

## 2026-06-23 — no-any-ban-targets-our-data-not-a-typed-librarys-intentional-any
- **Mistake:** Building the structlog logger (E17-F4 / #132), a `/review` subagent flagged that
  `redact_secrets` used structlog's `WrappedLogger`/`EventDict` (which are `Any`-backed aliases), and I
  "fixed" it by retyping to generic `object`/`MutableMapping[str, object]` to "close a hole in
  `disallow_any_explicit`." Both premises were wrong: (1) there was **no hole** — `disallow_any_explicit`
  flags only **literal in-module `Any`**, never an imported alias that happens to contain `Any`, so using a
  library's typed aliases passes the ban *by design* (mypy was green on both versions — I never confirmed
  the mechanism); (2) replacing a **`py.typed`** framework's **documented processor types** with generic
  ones at the adapter boundary is *less* idiomatic, made the package inconsistent (`config.py` still needs
  structlog's `Processor`/`FilteringBoundLogger`), and bought zero real safety (the internal recursion
  already narrows `object` via `isinstance`). It was also a needless **3rd post-approval commit** on
  already-Ship'd code. The founder pushed back and a Codex `gpt-5.5` xhigh second opinion both said revert.
- **Rule:** The no-`Any` policy (`disallow_any_explicit`; `object`-not-`Any`) governs **our own data** —
  open/untrusted payloads (env observations, deployed cloud state) get `dict[str, object]` + a runtime
  narrow. It does **NOT** mean fighting a third-party **`py.typed`** library's intentional `Any`: at a
  **framework-adapter boundary** (a structlog processor, a callback signature) **use the library's own
  documented types** — their `Any` is deliberate API design (a processor's logger + event-dict are open by
  nature), and `disallow_any_explicit` doesn't flag them. Reserve `object`+`isinstance` for the **internal**
  implementation. Operationally: don't reopen already-approved code with another commit for a non-blocking
  P2, and **never act on a "this is a hole/bug" finding** (mine, a review subagent's, or Codex's) **without
  confirming the mechanism first** — 60 seconds checking what `disallow_any_explicit` actually flags would
  have prevented the whole detour.
- **Context:** E17-F4 (#132) / PR #133; `py/packages/logger` `redaction.py`/`config.py`; commit `ef22c91`
  (the mistake) reverted in `4c40e54`. Also surfaced `structlog.types` is deprecated since 22.2.0 (its own
  module docstring) → import from `structlog.typing`. Sharpens
  [[verify-against-official-docs-and-skills-before-acting]] +
  [[use-the-librarys-official-mechanism-not-a-hand-roll]].

## 2026-06-23 — create-and-link-the-tracking-issue-before-opening-a-PR
- **Mistake:** For founder-initiated review/improvement work (the Python type-safety parity) I branched and
  opened PR #124 directly with **no tracking issue** — so it had no `Closes #N` and wasn't on the board. The
  founder caught it: "we forgot to create an issue first, so create an issue so we can link to this PR."
- **Rule:** Even for **ad-hoc / founder-initiated work** (not just the "implement the next ready issue"
  trigger), create the GitHub issue **first** (or before opening the PR) and open the PR with `Closes #N`.
  The issue must detail the findings + fixes and **join the board + parent epic** (the
  [[new-issues-must-join-the-board-and-parent-epic]] steps: `gh project item-add 1 --owner AssayInc`,
  GraphQL `addSubIssue` under the right epic, `gh project item-edit` to mirror the parent's Status/Lane/Epic).
  Gotchas seen here: (1) `gh pr edit --body-file` fails on this repo with a "Projects (classic) … being
  deprecated" GraphQL error — patch the body via `gh api --method PATCH repos/<o>/<r>/pulls/<n> -F body=@file`
  instead; (2) the board **Epic field has no E17 option** (E17 #113 lives under E0), so E17 sub-issues mirror
  the parent — Lane "A · Core IP", Epic "E0 Infra".
- **Context:** PR #124 / issue #125 (E17 Python type-safety parity). Extends the CLAUDE.md task-loop
  "update PROGRAM/ISSUES + GitHub issues" step to ad-hoc work.

## 2026-06-23 — a-subagents-doc-citation-is-secondary-verify-the-primary-source-yourself
- **Mistake:** On the same PR I (1) grounded the load-bearing mypy claims (`--strict` excludes
  `disallow_any_explicit`; the per-module override precedence) via a research **sub-agent's** doc citations +
  Codex's citation rather than reading mypy.readthedocs.io myself; (2) had the **skills-review sub-agent
  fail** and backfilled its conclusions from skill *descriptions* instead of reading the vendored skills; and
  (3) applied a `/review` fix without re-running Codex xhigh on it. The founder asked all three: "did you
  ground all your decisions by official docs and skills? did you re-review codex gpt-5.5 xhigh?"
- **Rule:** A research/review **sub-agent (or Codex) citing official docs is a SECONDARY source** — for any
  load-bearing claim, open the **primary doc yourself and quote it** (the 60-second check). If a sub-agent
  that was supposed to read the skills/docs **fails**, do that reading yourself; never report "grounded" off
  a description backfill. And [[re-review-fixed-code-with-codex-xhigh-and-recheck-the-finding-scope]] applies
  to **any** fix made in response to a review — a `/review`-initiated fix too, not only issue implementation:
  re-run Codex **xhigh** on the fixed code and re-sweep the finding's scope before claiming done.
- **Context:** PR #124. Confirmed after the fact, verbatim from mypy.readthedocs.io: the `--strict` flag list
  (no `disallow-any-explicit`), "Disallows explicit `Any` in type positions…", and the well-structured-wildcard
  precedence (more-specific wins, per-module beats top-level); the xhigh re-review returned ship/zero-findings.
  Sharpens [[ground-in-official-docs-first]] + [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-23 — re-review-fixed-code-with-codex-xhigh-and-recheck-the-finding-scope
- **Mistake:** In the E1-3 (#28) `/review`, after a Codex xhigh pass flagged the `DiffIR.propertyDiffs`
  canonicalization divergence I implemented a fix and committed it **without re-running Codex xhigh on the
  fix**. The founder asked "did you call gpt-5.5 xhigh to re-review it after changes?" The re-review I then
  ran caught that my fix's **diagnosis was under-scoped** — I'd called `propertyDiffs` "the lone optional
  field," but `PropertyDiff.expected`/`actual` are optional too; a further pass caught I'd locked only one of
  the two optional sides. It took three post-fix passes to converge to "ship."
- **Rule:** When a cross-model review (Codex **gpt-5.5 xhigh**) finds a real issue and you **change code in
  response, re-run the review on the FIXED code** before claiming done — the fix can be incomplete,
  mis-scoped, or introduce a new defect; iterate to convergence (a clean/ship verdict), don't stop at the
  first fix. And when responding to a finding, **re-check the finding's SCOPE yourself** — sweep the whole
  schema/type for sibling instances rather than assuming the reviewer named the only one (Codex named
  `propertyDiffs`; the same class also hit `expected`/`actual`). A single pass on the pre-fix code is not the
  bar. Sharpens [[codex-reviews-run-at-xhigh-not-the-skill-default-high]].
- **Context:** E1-3 (#28) JCS canonicalize `/review`; the #114 spike already set the "re-review the FIXED
  code with xhigh" precedent (the founder asked the same there — see the #114 post-fix re-review). Pairs with
  [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-23 — reground-a-spikes-library-usage-against-primary-docs-when-promoting-to-production
- **Mistake:** Building E1-3 (#28), I wrote the production JCS `canonicalize` by **reusing the #115 spike's
  `rfc8785` recipe + empirical testing + the shipped `canonicalize` `.d.ts`**, and cached knowledge for
  Pydantic `model_dump(mode="json")` — without reading the **official docs** for any of them this session.
  The founder asked "did you ground every implementation from the official docs?" Grounding them after the
  fact (rfc8785.py README, erdtman/canonicalize README, Pydantic serialization docs via `/browse`)
  **confirmed every claim** — but the primary-source check should have come first, not in response to the
  question.
- **Rule:** A **landed spike's** library usage, an **empirical green**, and a shipped **`.d.ts`** are all
  **secondary** sources. Promoting a spike's external-library usage to production code is a **new grounding
  obligation**: read the **official docs FIRST** and cite them, even when the spike already proved the
  behavior and the tests pass — especially for a **security/correctness primitive** (here, the exact bytes a
  KMS signature covers). The cheap primary-source pass settles it (rfc8785: "All APIs raise
  `CanonicalizationError`… on serialization failures" → the documented fail-closed; canonicalize: "crypto
  safe… as defined by RFC8785"; `model_dump(mode="json")`: "ensure JSON-compatible types are used"). Don't
  let "the spike already did it" or "the tests are green" substitute for [[ground-in-official-docs-first]].
- **Context:** E1-3 (#28) JCS canonicalize; `rfc8785` (Trail of Bits) / `canonicalize` (erdtman) / Pydantic
  v2 serialization docs. Sharpens [[ground-in-official-docs-first]] +
  [[ground-external-api-contracts-against-primary-docs-when-the-emulator-fakes-them]] with the
  spike→production re-grounding trigger.

## 2026-06-22 — ground-external-api-contracts-against-primary-docs-when-the-emulator-fakes-them
- **Mistake:** In the E17-S2 ledger spike (#115) I grounded the AWS KMS/S3 specifics — KMS `Sign` returns a
  DER ECDSA sig + `MessageType=DIGEST` doesn't re-hash, `GetPublicKey` returns SPKI DER, the S3
  Object-Lock-put checksum requirement — via the doc-distilled `reward-ledger-worm` skill + empirical
  `moto`, **not the primary AWS docs**, then reported "grounded." The founder probed ("did you ground
  everything with official docs?"). The gap was load-bearing because **moto fakes the KMS crypto** (its
  `Sign` doesn't verify against its own `GetPublicKey`), so the emulator literally cannot confirm the real
  signature/key formats, and a vendored skill is a secondary distillation.
- **Rule:** When a spike/feature's correctness rests on an external API's exact contract (signature/key
  encoding, required headers, error semantics) **and the local emulator (moto/LocalStack) fakes or only
  partially implements that behavior**, grounding via a vendored skill + the emulator is **insufficient** —
  verify the exact contract against the **primary vendor docs** and cite the quote before claiming
  "grounded." A faked-emulator green proves the call shape integrates, not that the real service behaves as
  assumed. Browsing the AWS docs confirmed all three and showed the S3 checksum is **required** for
  Object-Lock puts (validating the `/review` fix as doc-mandated, not optional). Sharpens
  [[ground-in-official-docs-first]] + [[local-aws-emulator-must-prove-read-api]] with the explicit
  emulator-fakes-it → primary-docs trigger.
- **Context:** E17-S2 (#115) / PR #122; AWS KMS `Sign` / `GetPublicKey` + S3 `PutObject` API references
  (verified via `/browse`). Pairs with [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-22 — bun-lock-and-uv-lock-after-adding-a-py-package
- **Mistake:** Added `py/packages/env-server` (a **Python** package) with a thin `package.json` turbo
  wrapper, ran `uv lock`/`uv sync`, and `bun run verify` was green locally — but **CI failed at
  `bun install --frozen-lockfile`** ("lockfile had changes, but lockfile is frozen"): the new package
  is also a **bun workspace member** (root `package.json` `workspaces: ["py/packages/*"]`) and
  `bun.lock` never recorded it. `bun run verify` (turbo) never reinstalls, so it masked the stale lock.
- **Rule:** After adding ANY new `py/packages/*` **or** `ts/**` package with a `package.json`, run
  **BOTH** `bun install` (updates `bun.lock` for the bun-workspace member — even a Python package has a
  bun wrapper) **AND** `uv lock`/`uv sync` (uv.lock), and commit both lockfiles. The CI install step is
  `bun install --frozen-lockfile`, which rejects a stale `bun.lock`; **verify locally with `bun install
  --frozen-lockfile` before pushing** — `bun run verify` does NOT catch it.
- **Context:** E17-S1 (#114) / PR #121; `ci.yml` runs `bun install --frozen-lockfile` per lane.

## 2026-06-22 — verifier-grades-ground-truth-not-agent-reported-state
- **Mistake:** In the OpenEnv env-server spike the reward-boundary proof fed the **agent-reachable**
  `observation.deployed_state` into the (mock) account-B grader. Every test passed, but the proof was
  **tautological** — it never showed the verifier reads state independently of the agent. Codex
  `gpt-5.5` xhigh caught it in `/review` (recommended **Block**).
- **Rule:** For the AssayOps verifier (real or mocked — E2/E4/E5), the grade input MUST come from
  **ground truth the agent cannot forge**: read from an independent channel (deployed cloud resources
  via boto3, or a ground-truth substrate keyed by `trajectory_id`), **never** the agent-reachable
  observation / trajectory / `step()` output. Feeding agent-reported state to the grader makes a green
  boundary test prove nothing — the independent read *is* the moat (`DECISIONS.md` §1/§8, vector #15).
  A passing suite can still encode a tautological boundary; run the cross-model adversarial `/review` on
  any verifier/boundary code.
- **Context:** E17-S1 (#114) / PR #121; the fix is `cloud_state.CLOUD` (env deploys, account-B reads it
  by `trajectory_id`). Pairs with [[ground-in-decisions-and-brain-not-the-ai-written-issue]].

## 2026-06-22 — dont-close-an-epic-on-its-first-deliverable-pr
- **Mistake:** Put `Closes #113` on the E17 **decision PR** (#118) and merged — which closed #113. But
  #113 is an **epic** with open sub-issues (#114/#115 spikes, #80, #116/#117/#119); the decision PR was only
  its **first** deliverable. The founder caught it from the board ("do we need to reopen any of those closed
  issues?"). Reopened #113 + reset its board Status to In Progress.
- **Rule:** Use `Closes #N` only when the PR **fully completes** issue N. For an **epic** (or any parent
  with open sub-issues / more deliverables to come), **reference, don't close** — `Part of #N` / `Advances
  #N`, and let the epic close when its **last sub-issue** closes (the GitHub sub-issue rollup tracks it —
  cf. E1 #2 staying open while #28/#29 are open). Before merging, check whether the `Closes`-targeted number
  is an epic or has open sub-issues; if so, downgrade the keyword.
- **Context:** E17 (#113) / PR #118. Pairs with [[update-program-state-before-landing]] +
  [[new-issues-must-join-the-board-and-parent-epic]] — the GitHub issue/epic graph is part of "done."

## 2026-06-22 — ground-the-option-set-of-an-inherited-decision-not-just-the-pick
- **Mistake:** "Resolved" the E17 type-checker gate to **mypy** by accepting the AI-written issue's
  framing ("mypy vs pyright") + the existing E0-1 default — **without checking the official Astral docs and
  without even considering `ty`** (Astral's type checker), the obvious same-ecosystem candidate for a repo
  already on uv + ruff. Recorded it "resolved in the decision record" with zero doc-grounding. The founder
  caught it ("did you ground every decision by official docs? like astral ty?").
- **Rule:** When you "resolve" or lock a **tooling/library decision**, ground the **option SET itself**
  against the official docs first — not just the option you picked. An AI-written issue's "X vs Y" framing
  can silently omit the obvious candidate; "resolved in the record" without a primary-source check is the
  cached-knowledge trap [[ground-in-official-docs-first]] exists to stop. One `/browse` of the vendor docs
  settles it (here: ty's README → **beta, 0.0.x, no stable API, breaking changes expected** → wrong gate
  for a proof-critical lane, so **mypy --strict** now + `ty` tracked adopt-when-stable). Cached "mypy is the
  default" reasoning does not.
- **Context:** E17 (#113) typing gate; Astral `ty` (docs.astral.sh/ty · github.com/astral-sh/ty), ruff
  (lint/format only), uv. Sharpens [[ground-in-official-docs-first]] /
  [[verify-against-official-docs-and-skills-before-acting]] — it applies to *which options exist*, not only
  a chosen library's API.

## 2026-06-22 — new-issues-must-join-the-board-and-parent-epic
- **Mistake:** Created the E17 follow-up issues (#114–#117) with `gh issue create` and stopped there —
  they landed with **no Projects v2 board membership and `parent: null`**, off the AssayOps board and
  outside the E17 epic. The founder caught it ("#116 is not under any project … should be under the
  correct epic").
- **Rule:** An issue isn't tracked until it's **on the board AND parented**. After every `gh issue create`
  here (`DECISIONS.md` I4 = GitHub Issues + Projects v2, epics-as-sub-issues), do three steps and verify:
  (1) **add to the org project** — `gh project item-add 1 --owner AssayInc --url <issue-url>`; (2) **parent
  under the right epic** via GraphQL **`addSubIssue`** (`gh issue edit` has **no** parent flag) — the
  `E{N}-*` title prefix dictates the parent (`E17-*` → the E17 epic **#113**, itself under **#1/E0**);
  (3) **set the board single-selects** (Status/Lane/Epic) with `gh project item-edit` to **mirror the
  parent epic** (a bare item shows in "No Status"/no epic swimlane). Confirm with a `subIssues` /
  `projectItems` GraphQL read before claiming done. Project #1 = `PVT_kwDOEYppDc4BbCzj`.
- **Context:** E17 (#113) follow-ups #114–#117. Extends the CLAUDE.md task-loop "update PROGRAM/ISSUES +
  GitHub issues" step — "create the issue" is not done at `gh issue create`.

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
