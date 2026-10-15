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

**Quality bar.** One idea per lesson — if the Rule needs an *and*, split it. The Rule is a *generalizable*
instruction for next time, not a recap of this run. Context is terse refs (issues/PRs/files), not an
outcome narration. Don't duplicate — sharpen the existing lesson instead. The slug should read as the
compressed rule.

---

## 2026-07-03 — background-codex-needs-closed-stdin-and-a-liveness-check
- **Mistake:** Launched a background `codex exec` re-review and only tailed its output file; the
  process died at "Reading additional input from stdin..." (non-TTY stdin) and the run sat silent
  for ~3h until the founder noticed.
- **Rule:** A background `codex exec` gets stdin explicitly closed (`< /dev/null`) and a liveness
  check right after launch (the `reasoning effort:` banner must appear within ~a minute, and the
  process must exist in `ps`) — never infer "still running" from a quiet output file.
- **Context:** #192 / PR #196 re-review. Complements [[codex-reviews-run-at-xhigh-not-the-skill-default-high]].

## 2026-07-03 — continue-on-fail-for-measurement-eval-arms
- **Mistake:** Ran the r4 delta arms with Inspect's fail-fast default; a single 32k serving-window
  overflow episode aborted a whole arm, forcing a re-run — and a fail-fast abort produces a
  `status=error` log that can read as "the arm failed" rather than "one episode errored."
- **Rule:** Run a **measurement** eval arm (a delta/diagnostic where you want the whole grid) with
  `--continue-on-fail`, so a terminal per-episode error becomes a *counted* errored sample instead
  of killing the run. The fail-closed report still refuses a partial/mismatched grid, so honesty is
  preserved either way; you just don't throw away the good episodes.
- **Context:** #197 / PR #198; r4 arms `delta-sft-r4-heldout`, `delta-sft-me-trained-r4-ml100`.

## 2026-06-26 — resolve-a-floor-touching-design-decision-with-two-grounded-reviews
- **Mistake:** Surfaced a moat / frozen-floor-touching design decision (a genuine unreadable → reward 0
  vs. raise) to the founder as a bare `AskUserQuestion` multiple-choice.
- **Rule (founder directive):** Resolve a **moat / floor-touching DESIGN decision** with **two grounded
  adversarial reviews** (Opus 4.8 max + Codex gpt-5.5 xhigh, each grounded in DECISIONS.md + brain +
  official docs + skills) and synthesize — don't punt the choice to the user as a multiple-choice.
  Present the *synthesized* recommendation (or a genuine tie), having validated the load-bearing
  premises against the primary sources yourself.
- **Context:** #141 / PR #172 — the genuine-unreadable→reward-0 call (both reviews → Recommendation A,
  after confirming the agent reward-channel dodge against the AWS IAM docs). Sharpens
  [[diverse-lens-review-for-moat-code-before-merge]] (applies to *decisions*, not just code review) +
  [[a-converged-cross-model-review-is-not-validation]].

## 2026-06-26 — ground-an-issues-relationships-and-sibling-comments-not-just-its-own
- **Mistake:** Grounding #44 I reported "0 comments, no blockers" from `gh issue view --comments` + a
  comments-only graphql — but #44 had a `blocked_by` (#25) and a cross-ref (#159) in its **timeline**, and the
  decisive scoping precedent lived in **sibling** issues' comments (#141, #46), none of which #44 cites. The
  founder had to prompt "did you load the comments?".
- **Rule:** An issue's grounding context lives in its **timeline relationships** (`blocked_by`,
  cross-references, sub-issues — `gh api .../issues/N/timeline` + `.../dependencies/blocked_by`) and in
  **sibling issues in the same epic/area**, not only its own comments. A zero-comment target is not a
  context-free target — check the relationships + a recent founder scoping comment on a sibling before
  concluding "ready / nothing here."
- **Context:** #44 (closed/reconciled, PR #170). Sharpens
  [[re-read-the-target-issues-own-comments-before-finalizing]] +
  [[read-the-related-issues-and-prs-an-issue-cites-not-just-the-issue]].

## 2026-06-26 — review-the-diff-itself-not-just-the-validated-claim
- **Mistake:** Shipped the #165 fix after two reviewers confirmed the *claim* — but neither had seen my edits,
  and the PR's wording re-seeded the original ambiguity about which creds sign the cross-account read (the
  assumed account-A creds, not B's).
- **Rule:** Adversarial review must see the actual **diff**, not just the underlying claim/facts — a correct
  claim can ship with wording that re-introduces the bug.
- **Context:** #165 / AssayInc/skills#10.

## 2026-06-25 — verify-a-trust-mechanisms-exact-semantics-in-the-conceptual-docs
- **Mistake:** #160 used Cloud Control `RoleArn` as the B→A cross-account read hook, but `RoleArn` is a
  SAME-account CFN service role (cross-account = STS `AssumeRole`; the target account is set by the signing
  creds). I grounded it on the boto3 param-ref + the `write-isolated-verifier` skill/brain, not the AWS user
  guide.
- **Rule:** Verify a security/trust mechanism's EXACT semantics against the primary **conceptual** docs (the
  service user guide), not a one-line API-param ref or a brain/skill framing.
- **Context:** #160 → #163; the skill/brain carried the same wrong claim, fixed at the source in #165
  (AssayInc/skills#10 + brain, re-vendored). Pairs with [[diverse-lens-review-for-moat-code-before-merge]].

## 2026-06-25 — diverse-lens-review-for-moat-code-before-merge
- **Mistake:** The #160 `RoleArn` trust-mechanism error passed two **correctness** reviews; only a later
  design-lens review caught it, post-merge (#163).
- **Rule:** Moat / proof-critical code gets **diverse-lens** review — forge + crash + design, not just
  correctness — BEFORE merge. Correctness review alone misses a wrong trust mechanism that is internally
  consistent.
- **Context:** #160 → #163. Pairs with [[verify-a-trust-mechanisms-exact-semantics-in-the-conceptual-docs]].

## 2026-06-25 — re-read-the-target-issues-own-comments-before-finalizing
- **Mistake:** Built #30 from the body alone — my initial `gh issue view 30 --json comments` returned `[]`, but
  the founder posted a detailed pre-start grounding review *during* the session and I never re-checked.
- **Rule:** Re-read the target issue's **own** comments (`gh issue view <N> --comments`) right before opening
  the PR, not just once at fetch — a reviewer may post grounding mid-session that overrides the AI-written body.
- **Context:** #30 / PR #160. Finalize-time complement to
  [[read-the-related-issues-and-prs-an-issue-cites-not-just-the-issue]].

## 2026-06-25 — verify-an-issues-build-state-not-just-its-requirements
- **Mistake:** Started designing a new `py/packages/replay` package for #46 (a P1 "ready" issue) before
  checking its build-state: the check was already done + negative-controlled by a sibling PR, and its one
  unbuilt slice was blocked on an unbuilt harness + policy — a premature abstraction coding around a block.
- **Rule:** Before building an AI-written issue — *even a P1 "ready" small one* — verify its **build-state**,
  not just its requirements: is it already satisfied by a sibling PR (grep the exact behavior the AC names)? do
  the harness/policy its genuine slice needs exist? If the only unbuilt slice depends on unbuilt deps it's
  **blocked → rescope-and-defer + comment, don't build a speculative package**. The issue's milestone/label/epic
  can be stale; the floor + code win.
- **Context:** #46 (done-by #31, blocked by #14 + #45). Native blocked-by:
  `gh api --method POST repos/{o}/{r}/issues/{n}/dependencies/blocked_by -F issue_id=<blocker db id>`. Pairs
  with [[ground-in-decisions-and-brain-not-the-ai-written-issue]] +
  [[spike-output-is-a-decision-not-a-committed-package]].

## 2026-06-25 — classify-by-the-determinism-policy-not-a-library-retry-mechanism
- **Mistake:** Classified a surfaced AWS throttle as GENUINE → reward 0 because "boto3's adaptive retry already
  owns throttle retries" — conflating the retry *mechanism* with the transient/genuine *policy*.
- **Rule:** Decide transient-vs-genuine by the policy question — *is this a wrong answer?* — never by which
  layer owns the retry. A throttle / 5xx / un-propagated read is **transient** (scoring it 0 is a false-negative
  reward, as poisonous to training as a false positive), even when a lower layer already retries it. Own the
  policy; let the library own the mechanism.
- **Context:** #45 / `py/packages/replay/classifier.py`; `deterministic-verification` skill.

## 2026-06-25 — a-converged-cross-model-review-is-not-validation
- **Mistake:** A false-negative-reward premise was accepted (and "hardened") by both the Claude and Codex
  `xhigh` reviews; only a primary-source re-read caught it.
- **Rule:** A converged cross-model review (Claude + Codex agreeing) is not validation of a load-bearing
  correctness premise — reviews surface findings but inherit the assumptions handed to them. Validate the
  premise against the primary source (skill / frozen floor / the consuming issue), not reviewer consensus.
- **Context:** #45 / PR #159. Sharpens [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-25 — spike-output-is-a-decision-not-a-committed-package
- **Mistake:** Resolving the #60 IAM-eventual-consistency spike, I committed the throwaway measurement probe as
  a permanent `py/packages/iam-readiness-probe` workspace member (pyproject + README + nested CLAUDE.md +
  lockfile churn + a forever CI surface), pattern-matching the repo's "reusable thing → package" convention.
  The founder challenged it — was this in the plan, does it help the goal? It wasn't.
- **Rule:** A spike's output is the **recorded decision + numbers** (`DECISIONS.md` on ratification + the issue
  comment as reproducible methodology), **NOT a new committed package**. Apply the "build only the IP / smallest
  change / don't create files the task doesn't need" filter AT THE DECISION POINT: if the artifact isn't on
  `DECISIONS.md` §8's build-list it isn't core IP — scratch/measurement tooling stays in the scratchpad, its
  method in the issue. Committing such a tool is justified only for genuinely-recurring value, as a deliberate
  flagged call with a tracked removal issue — never a silent default bundled into "open the PR."
- **Context:** #60 / PR #151 — package removed, #156 closed; method preserved in the #60 thread, decision in
  `DECISIONS.md` §1. Pairs with [[ground-in-decisions-and-brain-not-the-ai-written-issue]].

## 2026-06-25 — read-the-related-issues-and-prs-an-issue-cites-not-just-the-issue
- **Mistake:** On #31 I read the related issues' *bodies* early but didn't re-read the **comments / state /
  closing-PRs** of the issues its AC cites (#75, #46, #34) before claiming merge-ready — where the load-bearing
  cross-issue contracts actually lived.
- **Rule:** When an issue's description / AC / comments **cite other issues or PRs** (`#NN`), read those cited
  items' **body AND comments AND state/closing-PR** as part of grounding — the cross-issue contract (what a
  dependency guarantees, what a sibling owns, what is still open) often lives in the **comments**, not the body.
  Do it proactively, before claiming done.
- **Context:** #31 cited #75 (CLOSED via #146) + #46 (OPEN) + #34 (CLOSED via #145). Pairs with
  [[ground-in-decisions-and-brain-not-the-ai-written-issue]] +
  [[grounding-is-part-of-done-do-it-before-being-asked]].

## 2026-06-24 — delegate-equality-to-the-signed-canonical-form-but-guard-its-input-domain
- **Mistake:** Refactored the diff-ir reward core (#34) to define value **equality and validity** by RFC 8785
  JCS. Equality was right; validity-as-"does it canonicalize?" was not — `rfc8785.dumps` *coerces* a builtin
  subclass via `int()`/`list()`/…, so `LyingInt(9)` (== 9) with `__int__→1` canonicalizes 9 to `b"1"`: a false,
  nondeterministic reward 1.
- **Rule:** Delegate the *equality semantics* to the system's canonical/signed form (no hand-rolled comparator;
  `90==90.0`, `True≠1` fall out free; grade ↔ digest agree by construction). But guard the *input domain* to
  exact types (`type(x) is T`, never `isinstance`) **before** canonicalizing — a canonicalizer coerces
  adversarial input, it doesn't reject it; never pass an open `object` and rely on undocumented coercion.
- **Context:** #34 / PR #145; rfc8785's subclass coercion is undocumented → guard, don't rely. Caught by the
  xhigh re-review of the *fixed* code ([[re-review-fixed-code-with-codex-xhigh]]); companion to
  [[harden-to-the-precise-domain-semantics-not-an-over-general-rule]].

## 2026-06-24 — harden-to-the-precise-domain-semantics-not-an-over-general-rule
- **Mistake:** Fixing a `True == 1` false-reward-1 in the diff-ir reward core (#34), I over-generalized to full
  type-strictness (`type(a) is not type(b)`), which also made `90` ≠ `90.0` — a **false-negative** (JSON has one
  number type; JCS canonicalizes them identically), as poisonous to training as a false positive. The founder
  caught it ("fix only what's not right").
- **Rule:** When hardening a correctness/trust check, match the **precise domain semantics** — don't reach for
  the broadest rule that covers the failing case. A fix **stricter than the ground-truth semantics is itself a
  bug** (it introduces a new failure class). Keep the genuinely bug-preventing hardening; cut the over-reach.
- **Context:** E3-1 (#34) / PR #145; the value comparison + NORMALIZATION.md. The over-strict cut later drove
  replacing the comparator with JCS delegation
  ([[delegate-equality-to-the-signed-canonical-form-but-guard-its-input-domain]]). Pairs with
  [[lock-the-adjacent-correct-case-with-its-own-test]].

## 2026-06-24 — lock-the-adjacent-correct-case-with-its-own-test
- **Mistake:** The over-strict `90 ≠ 90.0` hardening "passed the failing test" — TDD didn't catch it because the
  *adjacent-correct* case (`90 == 90.0`) was never tested; a reviewer caught it, not the suite.
- **Rule:** **TDD only catches over-reach you enumerate.** When hardening a rule, lock the **adjacent-correct
  case** with its own test (the input that must STAY valid), not just the failing one — otherwise a fix that
  over-generalizes sails through green.
- **Context:** E3-1 (#34) / PR #145. Pairs with
  [[harden-to-the-precise-domain-semantics-not-an-over-general-rule]].

## 2026-06-24 — grounding-is-part-of-done-do-it-before-being-asked
- **Mistake:** Twice (#34, #75) presented a build as done after grounding only against **skills** + TDD + the
  cross-model review — then the founder had to ask the standing grounding questions, and doing the pass *then*
  surfaced real refinements that should have landed before "done."
- **Rule:** The full grounding pass is **part of "done," done proactively** — run it before claiming complete,
  not in reaction to being asked. A skill cite / green test / Codex pass are **secondary** and do not substitute.
  *What* the pass is lives in its canonicals: open the primary docs yourself
  ([[a-subagents-doc-citation-is-secondary-verify-the-primary-source-yourself]] + [[ground-in-official-docs-first]];
  an empirical probe of the pinned lib counts where docs don't cover a behavior) and validate against every
  applicable craft skill, N/A stated ([[validate-against-all-relevant-vendored-skills-not-just-the-api-skill]]).
- **Context:** #34 / PR #145 + #75 / PR #146 — the founder's standing grounding questions, asked post-"done."

## 2026-06-24 — dont-strip-cheap-fail-closed-validations-to-win-an-over-fixing-argument
- **Mistake:** On #75 (the golden generator), asked "are you over-fixing?", I started **removing working
  validations + their tests** because a proportionality reviewer framed them as disproportionate. The founder
  caught it: "if the tests and validations are important, keep them." They were cheap, fail-closed, runtime-free,
  and protect the load-bearing invariant (a deterministic content-address).
- **Rule:** For the proof-critical core, a **cheap fail-closed validation protecting a load-bearing invariant
  STAYS** — "a plausible-but-wrong verifier is worse than none." Don't delete a working safety check + its test
  to lower a test count or win a "proportionality" argument; one that can only reject *pathological* input
  (never a legitimate golden) is pure insurance. The legitimate answer to "over-fixing" is: keep the protective
  checks, clarify intent, and cut only genuine speculative abstraction / true redundancy — never safety.
- **Context:** #75 / PR #146 — reverted; kept all 35 tests + validations. Pairs with
  [[reviewer-verdicts-are-inputs-not-directives]].

## 2026-06-24 — reviewer-verdicts-are-inputs-not-directives
- **Mistake:** On #75 I let reviewers drive me both ways — an adversarial reviewer to "add every validation,"
  then a proportionality reviewer to "cut them all" — instead of holding my own judgment on each finding.
- **Rule:** Reviewer verdicts are **inputs, not directives.** Weigh each finding's cost vs. what it protects
  yourself; don't let an adversarial reviewer ping-pong you to "add everything" and a proportionality reviewer to
  "cut everything." Where two strong reviewers disagree on a real tradeoff, surface it as the user's call; never
  unilaterally strip safety.
- **Context:** #75 / PR #146. Pairs with [[a-converged-cross-model-review-is-not-validation]] +
  [[dont-strip-cheap-fail-closed-validations-to-win-an-over-fixing-argument]].

## 2026-06-24 — negative-control-restore-with-a-file-backup-never-git-checkout
- **Mistake:** Running a negative control on #75 (break code → prove the test fails → restore), I restored with
  `git checkout -- <files>` — which reverts to HEAD, silently wiping all the **uncommitted** fixes from that
  turn, not just the one-line negative-control patch.
- **Rule:** A negative control mutates **uncommitted** code in place; restore it from a **file backup**, never
  from git. Before the patch `cp <file> /tmp/<file>.bak` (out of the repo tree); after, copy it back, or keep
  the original text in the patch script and write it back. **Never `git checkout -- <file>` /
  `git restore` while there are uncommitted changes you want to keep** — it discards them to HEAD. (If you must
  use git, commit the good state first so HEAD *is* the good state.)
- **Context:** #75 / PR #146; recovered by re-`Write`-ing the files. Every later negative control used a
  `cp`-backup restore.

## 2026-06-24 — act-decisively-on-airtight-code-evidence-dont-bounce-it-back
- **Mistake:** On #140 I proved three ways against `origin/main` that a review comment was stale — then still
  **asked the founder to re-confirm before I opened the PR** instead of proceeding. They pushed back ("Why don't
  you just check yourself? I just did it").
- **Rule:** When I've **airtight-verified a fact against the code**, flag the contradiction with receipts and
  then **PROCEED on that evidence** — don't stall asking the founder to re-confirm what I've already proven.
  Reserve "stop and ask" for genuine ambiguity I can't resolve from the code/docs, or an outward irreversible
  action. Opening a PR on verified evidence is not one. Flag-and-proceed, not flag-and-wait.
- **Context:** #140 / PR #144. Pairs with [[never-merge-without-explicit-user-approval]] (the one outward step
  that still waits).

## 2026-06-24 — codex-sandbox-has-no-github-network-paste-content-inline
- **Mistake:** A Codex `gpt-5.5` xhigh review needed issue bodies; every `gh issue view` hit
  `error connecting to api.github.com`, even after I retried steering it to `gh`. Wrong root cause: `gh` works in
  *my* shell, but Codex's `codex exec -s read-only` sandbox has **no network egress** — `gh`, the connector, and
  `curl` all fail there.
- **Rule:** A Codex review run **cannot reach GitHub.** Paste **GitHub-only content** (issue/PR bodies,
  descriptions, review comments) **inline** in the prompt; have Codex obtain the **code diff locally**
  (`git diff origin/<base>...HEAD` under `-C <repo>` — no network). Don't spend a pass instructing it to "use
  `gh`."
- **Context:** #80 / PR #138. [[gh-cli-first-for-pr-workflow]] still holds for my own shell, just not inside
  Codex's sandbox. Pairs with [[codex-reviews-run-at-xhigh-not-the-skill-default-high]].

## 2026-06-24 — todo-md-is-ephemeral-durable-records-go-elsewhere
- **Mistake:** Resolving the #80 spike, I recorded durable outputs (a surfaced requirement, a proposed
  `DECISIONS.md` note) only in `tasks/todo.md` — which is overwritten every session — and treated that as
  tracking. The founder flagged it.
- **Rule:** `tasks/todo.md` is an **ephemeral per-session scratchpad**, never the system of record. Route durable
  outputs to their durable home: a **GitHub issue** (boarded + parented) for actionable follow-up;
  **`DECISIONS.md`** for a settled rule/finding (flag first, land on ratification); **`ISSUES.md`/`PROGRAM.md`**
  for cross-cutting context + handoff. A newly-surfaced requirement becomes a **tracked issue**, not just a
  comment.
- **Context:** #80 / PR #138 — created #141, updated #53, landed the note in `DECISIONS.md` §1. Pairs with
  [[create-and-link-the-tracking-issue-before-opening-a-PR]] + [[update-program-state-before-landing]].

## 2026-06-24 — change-claude-md-with-extreme-caution
- **Mistake:** Two *opposite* errors on the `CLAUDE.md` skill-preflight rule (#116): first **over-added** a clause
  duplicating the preflight table + a meta-aside (bloat the founder flagged); then **over-corrected** by reverting
  the whole clause, including the load-bearing prose that had misdirected me.
- **Rule:** CLAUDE.md changes need **extreme caution** (every-session, every-agent load) — default to leaving it.
  Cut duplication of the preflight table and meta-narration (a correction's backstory belongs in lessons.md). BUT
  a **surgical fix to prose that misdirects an agent IS warranted** — distinguish "duplicating / narrating" (cut)
  from "fixing a misleading instruction" (keep, tightly). Prefer **length-neutral** edits.
- **Context:** #116 / PR #134. Sharpens [[claude-md-is-lean-no-issue-numbers]]; pairs with
  [[claude-md-serves-all-agents-no-dedupe]].

## 2026-06-23 — validate-against-all-relevant-vendored-skills-not-just-the-api-skill
- **Mistake:** Building the LocalStack boto3 smoke (#116) I grounded the boto3 mechanics against
  `aws-sdk-python-usage` but **skipped the Python craft skills the repo vendors**. Validating after the fact
  surfaced real fixes: my `_with_retry` caught broad `Exception` and hand-rolled what boto3's `Config(retries=…)`
  already provides.
- **Rule:** The CLAUDE.md skill-preflight rule covers **all the relevant vendored skills for the surface, not
  just the API/library skill.** Before writing Python in a domain the repo has craft skills for, validate the
  design against the applicable ones FIRST — retry/transient → `python-resilience`; exceptions →
  `python-error-handling`; tests → `python-testing-patterns`; the `Any` boundary → `python-type-safety` — and
  state which apply vs are N/A. A **hand-rolled retry/validation/redaction is the recurring tell** to reach for
  the library's mechanism instead.
- **Context:** #116 / PR #134. Pairs with [[use-the-librarys-official-mechanism-not-a-hand-roll]] +
  [[ground-in-official-docs-first]].

## 2026-06-23 — re-home-built-ts-with-no-consumer-surface-dont-duplicate
- **Mistake:** Asked to "re-home built TS for the Python core" (#116), I defaulted to the additive
  smallest-change — shipping a parallel Python `read-smoke` package while keeping the TS smoke — instead of
  consolidating.
- **Rule:** When built TS has **no genuine consumer surface**, **re-home it** to the Python core; don't ship a
  parallel package that duplicates it. Read the issue title's intent and apply the logger precedent (keep TS only
  for a real consumer surface) — don't default to the additive smallest-change when the intent is consolidation.
- **Context:** #116 / PR #134 — consolidated the smoke into `infra-local`. Pairs with
  [[a-uv-package-belongs-under-py-packages]].

## 2026-06-23 — a-uv-package-belongs-under-py-packages
- **Mistake:** A uv package placed at the repo root was routed to the **no-uv TS lane** by the `./py/**` glob;
  `bun run verify` masked it by running both lanes together, and Codex xhigh caught the CI-lane bug.
- **Rule:** A uv package belongs **under `py/packages/`** so the `./py/**` glob routes it to the Python lane
  automatically. At the repo root it needs special-case `--filter` flags that `bun run verify` hides — place it
  correctly instead of special-casing the lane.
- **Context:** #116 → relocated `infra-local` → `py/packages/infra-local` in PR #136.

## 2026-06-23 — no-any-ban-targets-our-data-not-a-typed-librarys-intentional-any
- **Mistake:** Building the structlog logger (#132), I retyped structlog's `Processor`/`EventDict` (Any-backed
  aliases) to generic `object` to "close a hole in `disallow_any_explicit`." There was no hole —
  `disallow_any_explicit` flags only literal in-module `Any`, never an imported alias — and replacing a
  `py.typed` framework's documented processor types with generic ones is *less* idiomatic, for zero real safety.
- **Rule:** The no-`Any` policy governs **our own data** — open/untrusted payloads (env observations, deployed
  state) get `dict[str, object]` + a runtime narrow. It does **NOT** mean fighting a third-party **`py.typed`**
  library's intentional `Any`: at a **framework-adapter boundary** (a structlog processor, a callback) use the
  library's **own documented types**; reserve `object`+`isinstance` for the internal implementation.
- **Context:** #132 / PR #133; commit `ef22c91` reverted in `4c40e54`. Also: `structlog.types` is deprecated →
  import from `structlog.typing`. Pairs with [[confirm-the-mechanism-before-acting-on-a-hole-or-bug-finding]].

## 2026-06-23 — confirm-the-mechanism-before-acting-on-a-hole-or-bug-finding
- **Mistake:** I acted on a "this is a hole in `disallow_any_explicit`" finding and refactored to close it —
  without confirming what the flag actually flags. There was no hole; mypy was green on both versions. Sixty
  seconds checking the mechanism would have prevented the whole detour.
- **Rule:** **Never act on a "this is a hole / bug" finding** — mine, a review subagent's, or Codex's — **without
  confirming the mechanism first.** Reproduce what the tool actually does before changing code in response.
- **Context:** #132 / PR #133. Sharpens [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-23 — dont-reopen-already-approved-code-for-a-non-blocking-nit
- **Mistake:** The needless structlog retype was a 3rd post-approval commit on already-Ship'd code, for a
  non-blocking P2.
- **Rule:** Don't reopen already-approved code with another commit for a **non-blocking nit** — note it for a
  follow-up instead. Post-approval churn re-risks a settled diff for no gain.
- **Context:** #132 / PR #133.

## 2026-06-23 — create-and-link-the-tracking-issue-before-opening-a-PR
- **Mistake:** For founder-initiated review/improvement work I branched and opened PR #124 with **no tracking
  issue** — no `Closes #N`, not on the board. The founder caught it.
- **Rule:** Even for **ad-hoc / founder-initiated work** (not just the "implement the next ready issue" trigger),
  create the GitHub issue **first** and open the PR with `Closes #N`; the issue details the findings + fixes and
  **joins the board + parent epic** per [[new-issues-must-join-the-board-and-parent-epic]].
- **Context:** PR #124 / issue #125. Extends the CLAUDE.md task-loop to ad-hoc work. Pairs with
  [[patch-pr-body-via-gh-api-not-body-file]].

## 2026-06-23 — patch-pr-body-via-gh-api-not-body-file
- **Mistake:** `gh pr edit --body-file` failed on this repo with a "Projects (classic) … being deprecated"
  GraphQL error.
- **Rule:** Patch a PR body on this repo via the REST API —
  `gh api --method PATCH repos/<o>/<r>/pulls/<n> -F body=@<file>` — not `gh pr edit --body-file`, which hits the
  deprecated Projects-classic GraphQL path.
- **Context:** PR #124.

## 2026-06-23 — a-subagents-doc-citation-is-secondary-verify-the-primary-source-yourself
- **Mistake:** Grounded load-bearing mypy claims via a research **sub-agent's** doc citations + Codex's citation
  rather than reading mypy.readthedocs.io myself; when the skills-review sub-agent **failed**, I backfilled its
  conclusions from skill *descriptions* instead of reading the vendored skills.
- **Rule:** A research/review **sub-agent (or Codex) citing official docs is a SECONDARY source** — for any
  load-bearing claim, open the **primary doc yourself and quote it** (the 60-second check). If a sub-agent that
  was supposed to read the skills/docs **fails**, do that reading yourself; never report "grounded" off a
  description backfill.
- **Context:** PR #124. Sharpens [[ground-in-official-docs-first]] +
  [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-23 — re-review-fixed-code-with-codex-xhigh
- **Mistake:** In the #28 `/review`, after a Codex xhigh pass flagged a canonicalization divergence I committed a
  fix **without re-running Codex xhigh on it**. The re-review then found my fix was incomplete; it took three
  post-fix passes to converge.
- **Rule:** When a cross-model review (Codex **gpt-5.5 xhigh**) finds a real issue and you **change code in
  response, re-run the review on the FIXED code** before claiming done — the fix can be incomplete, mis-scoped, or
  introduce a new defect; iterate to a clean/ship verdict, don't stop at the first fix. Applies to **any** fix
  made in response to a review, a `/review`-initiated one included.
- **Context:** #28; the #114 spike set the precedent. Sharpens
  [[codex-reviews-run-at-xhigh-not-the-skill-default-high]]; pairs with
  [[re-check-a-review-findings-scope-yourself]].

## 2026-06-23 — re-check-a-review-findings-scope-yourself
- **Mistake:** Responding to a Codex finding on `DiffIR.propertyDiffs`, I treated it as "the lone optional field"
  — but `PropertyDiff.expected`/`actual` are optional too; I locked only one of the two sides. The reviewer named
  one instance, not the only one.
- **Rule:** When responding to a review finding, **re-check the finding's SCOPE yourself** — sweep the whole
  schema/type for sibling instances rather than assuming the reviewer named the only one.
- **Context:** #28 JCS canonicalize `/review`. Pairs with [[re-review-fixed-code-with-codex-xhigh]].

## 2026-06-23 — reground-a-spikes-library-usage-against-primary-docs-when-promoting-to-production
- **Mistake:** Building #28, I wrote the production JCS `canonicalize` by reusing the #115 spike's `rfc8785`
  recipe + empirical tests + a shipped `.d.ts` + cached Pydantic knowledge — without reading the **official docs**
  this session. Grounding them after the founder asked confirmed every claim, but the check should have come first.
- **Rule:** A **landed spike's** library usage, an **empirical green**, and a shipped **`.d.ts`** are all
  **secondary** sources. Promoting a spike's external-library usage to production is a **new grounding
  obligation**: read the official docs FIRST and cite them — especially for a security/correctness primitive
  (here, the exact bytes a KMS signature covers).
- **Context:** #28; `rfc8785` / `canonicalize` / Pydantic v2 serialization docs. Sharpens
  [[ground-in-official-docs-first]] +
  [[ground-external-api-contracts-against-primary-docs-when-the-emulator-fakes-them]].

## 2026-06-22 — ground-external-api-contracts-against-primary-docs-when-the-emulator-fakes-them
- **Mistake:** In the ledger spike (#115) I grounded the AWS KMS/S3 crypto specifics via the doc-distilled
  `reward-ledger-worm` skill + empirical `moto`, then reported "grounded." But **moto fakes the KMS crypto** (its
  `Sign` doesn't verify against its own `GetPublicKey`), so the emulator literally cannot confirm the real
  signature/key formats.
- **Rule:** When a feature's correctness rests on an external API's exact contract (signature/key encoding,
  required headers, error semantics) **and the local emulator (moto/LocalStack) fakes or partially implements
  it**, a vendored skill + the emulator is **insufficient** — verify the exact contract against the **primary
  vendor docs** and cite the quote. A faked-emulator green proves the call shape integrates, not that the real
  service behaves as assumed.
- **Context:** #115 / PR #122; AWS KMS `Sign`/`GetPublicKey` + S3 Object-Lock checksum. Sharpens
  [[ground-in-official-docs-first]] + [[local-aws-emulator-must-prove-read-api]].

## 2026-06-22 — bun-lock-and-uv-lock-after-adding-a-py-package
- **Mistake:** Added `py/packages/env-server` (a **Python** package) with a thin `package.json` turbo wrapper, ran
  `uv lock`/`uv sync`, and `bun run verify` was green locally — but **CI failed at `bun install
  --frozen-lockfile`**: the new package is also a bun workspace member (root `workspaces: ["py/packages/*"]`) and
  `bun.lock` never recorded it. Turbo never reinstalls, so it masked the stale lock.
- **Rule:** After adding ANY new `py/packages/*` **or** `ts/**` package with a `package.json`, run **BOTH**
  `bun install` (updates `bun.lock` — even a Python package has a bun wrapper) **AND** `uv lock`/`uv sync`, and
  commit both lockfiles. Verify locally with `bun install --frozen-lockfile` before pushing — `bun run verify`
  does NOT catch it.
- **Context:** #114 / PR #121; `ci.yml` runs `bun install --frozen-lockfile` per lane.

## 2026-06-22 — verifier-grades-ground-truth-not-agent-reported-state
- **Mistake:** In the OpenEnv env-server spike the reward-boundary proof fed the **agent-reachable**
  `observation.deployed_state` into the (mock) account-B grader. Every test passed, but the proof was
  **tautological** — it never showed the verifier reads state independently of the agent. Codex xhigh caught it
  (recommended Block).
- **Rule:** For the AssayOps verifier (real or mocked), the grade input MUST come from **ground truth the agent
  cannot forge**: read from an independent channel (deployed resources via boto3, or a substrate keyed by
  `trajectory_id`), **never** the agent-reachable observation / trajectory / `step()` output — the independent
  read *is* the moat (`DECISIONS.md` §1/§8, vector #15). A passing suite can still encode a tautological
  boundary; run the cross-model `/review` on
  any verifier/boundary code.
- **Context:** #114 / PR #121; fix is `cloud_state.CLOUD`. Pairs with
  [[ground-in-decisions-and-brain-not-the-ai-written-issue]].

## 2026-06-22 — dont-close-an-epic-on-its-first-deliverable-pr
- **Mistake:** Put `Closes #113` on the E17 **decision PR** (#118) and merged — closing #113, an **epic** with
  open sub-issues. The decision PR was only its first deliverable. The founder caught it from the board.
- **Rule:** Use `Closes #N` only when the PR **fully completes** issue N. For an **epic** (or any parent with open
  sub-issues / more deliverables to come), **reference, don't close** — `Part of #N` / `Advances #N` — and let it
  close when its **last sub-issue** closes. Before merging, check whether the `Closes`-targeted number is an epic
  or has open sub-issues; if so, downgrade the keyword.
- **Context:** #113 / PR #118. Pairs with [[update-program-state-before-landing]] +
  [[new-issues-must-join-the-board-and-parent-epic]].

## 2026-06-22 — ground-the-option-set-of-an-inherited-decision-not-just-the-pick
- **Mistake:** "Resolved" the E17 type-checker gate to **mypy** by accepting the AI-written issue's "mypy vs
  pyright" framing + the existing default — without checking the Astral docs or even considering `ty`, the obvious
  same-ecosystem candidate for a uv + ruff repo. The founder caught it.
- **Rule:** When you "resolve" or lock a **tooling/library decision**, ground the **option SET itself** against
  the official docs first — not just the option you picked. An AI-written issue's "X vs Y" framing can silently
  omit the obvious candidate; "resolved in the record" without a primary-source check is the cached-knowledge
  trap. One `/browse` of the vendor docs settles it (here: `ty` is beta/0.0.x → wrong gate for a proof-critical
  lane → mypy --strict now, `ty` tracked adopt-when-stable).
- **Context:** #113 typing gate; Astral `ty`, ruff, uv. Sharpens [[ground-in-official-docs-first]] /
  [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-22 — new-issues-must-join-the-board-and-parent-epic
- **Mistake:** Created follow-up issues with `gh issue create` and stopped — they landed with **no Projects v2
  board membership and `parent: null`**, off the board and outside their epic. The founder caught it twice
  (#114–#117, then #152/#153).
- **Rule:** An issue isn't filed until it's **on the board, categorized, and parented.** After every `gh issue
  create`: (1) **add to the org project** — `gh project item-add 1 --owner AssayInc --url <url>`; (2) **parent
  under the right epic** — the `E{N}-*` title prefix dictates which — as a **native sub-issue**
  (`gh api --method POST repos/AssayInc/assay-ops/issues/<epic>/sub_issues -F sub_issue_id=<child db id>`;
  `gh issue edit` has no parent flag); (3) **set the board single-selects** (Status/Lane/Epic) via `gh project
  item-edit` by **mirroring a sibling** (read option ids with `gh project item-list`, don't guess). The project
  **Epic field is the source of truth** for categorization and has **no E16/E17 option** → toolchain/infra
  follow-ups file under **E0 Infra** (field set, no native parent where that epic is closed); don't leave a
  stale **milestone** — infra ≠ a phase milestone (clear it). Verify with a `subIssues` / `projectItems` read.
  Project #1 = `PVT_kwDOEYppDc4BbCzj`.
- **Context:** #114–#117; #152 → E0 Infra (milestone cleared), #153 → E2 + sub-issue of #3 (Phase 1). Extends
  the CLAUDE.md task-loop —
  "create the issue" is not done at `gh issue create`.

## 2026-06-22 — use-the-librarys-official-mechanism-not-a-hand-roll
- **Mistake:** Built `@assayops/logger` from cached pino knowledge: a hand-rolled `formatters.log` redactor that
  **leaked base/child bindings** and **flattened `Error`s** (lost message/stack), and a hand-rolled `{ write }`
  test capture. The founder caught both (pino's built-in `redact`; the official `pino-test`).
- **Rule:** For a library's **security/correctness primitive** (redaction, signing, canonicalization) **and its
  testing**, read the official docs FIRST and use the library's built-in mechanism — don't hand-roll from memory.
  A hand-rolled security primitive is a defect magnet (cloning the log object breaks Error/Date and misses
  bindings); the library's is battle-tested. The skill-preflight rule applies to **library config + test
  tooling**, not just new API calls.
- **Context:** `@assayops/logger` (PR #110); pino redaction / pretty / `pino-test`. Sharp instance of
  [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-21 — ground-in-decisions-and-brain-not-the-ai-written-issue
- **Mistake:** Started E1-1 (#26) from the issue's prose as if it were the spec, making several under-grounded
  field-level calls — one silently broke a `DECISIONS.md` §8 non-negotiable. The GitHub issues here are authored
  by **another AI agent** and can be wrong, stale, or missing a locked detail.
- **Rule (founder directive):** Before implementing ANY issue, **ground the requirements in `DECISIONS.md` +
  assay-brain + the plans first**, then reconcile issue + floor + brain. **Don't trust the AI-written issue
  blindly** — it's an input, not the spec. When they disagree, the frozen floor wins and you comment on the issue.
- **Context:** Founder feedback on E1-1 (#26). Pairs with [[frozen-floor-invariants-beat-issue-phrasing]] +
  [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-21 — frozen-floor-invariants-beat-issue-phrasing
- **Mistake:** Authored the `reward` field of the contract spine (#26) as a continuous bounded double, following
  the issue + `ARCHITECTURE.md` phrasing "bounded doubles." But `DECISIONS.md` locks **`reward ∈ {0,1}`** (incl.
  the §8 non-negotiables), and the `deterministic-verification` skill names a continuous score as the **gameable
  anti-pattern** — so the schema encoded that anti-pattern into the spine. The cross-model `/review` caught it.
- **Rule:** When a schema / type / constant encodes a domain invariant, ground the *value constraint* against
  `DECISIONS.md`'s frozen floor (especially the §8 non-negotiables) and the domain skills — not just the issue's
  or `ARCHITECTURE.md`'s prose. When the issue phrasing seems to *relax* a frozen-floor invariant, the floor wins:
  encode the **stricter** constraint (`enum:[0,1]` satisfies both — reconcile, don't pick one source). A deviation
  from a §8 non-negotiable is a flag-and-confirm item, not a silent design call.
- **Context:** #26 reward-record schema; `DECISIONS.md` §1/§2A/§8. Pairs with
  [[verify-against-official-docs-and-skills-before-acting]].

## 2026-06-21 — secret-scanning-detection-is-not-push-protection
- **Mistake:** Tested GitHub push protection with a planted `google_api_key`. The push wasn't blocked (only an
  alert), so I concluded enforcement had a propagation lag and proposed adding gitleaks. Wrong premise:
  `google_api_key` is **detection-only** (`hasPushProtection: false`), so it was *expected* to land and alert.
- **Rule:** **Secret-scanning detection ≠ push protection.** Not every detected type is push-protection-enforced
  — GitHub's supported-patterns data carries a per-type `hasPushProtection` flag. To prove push protection, plant
  a fabricated secret of a **supported** type (Stripe `sk_live_…`, SendGrid `SG.…`, Slack `xoxb-…`) and capture
  the `GH013 … Push cannot contain secrets` rejection. An **alert being created means the secret landed** — that
  is detection, the opposite of a blocked push. Don't misread GitHub's free-user account-rollout "week or two"
  note as repo-level enforcement lag.
- **Context:** #21 secret-scanning AC. Reinforces [[verify-against-official-docs-and-skills-before-acting]] +
  [[diagnose-unfamiliar-api-errors-before-theorizing]].

## 2026-06-21 — verify-against-official-docs-and-skills-before-acting
- **Mistake:** Applied two CI "hardening" changes from a Codex review (swap `bunx turbo` for named scripts; drop
  the `.turbo` cache) without first checking the vendored `turborepo` skill + official docs. Grounding it after the
  user pushed twice showed both were refuted — `globalDependencies` is turbo's prescribed mechanism, and turbo
  **recommends** CI caching. The "fixes" were overengineering, reverted.
- **Rule:** Before acting on a review finding or changing config/code in a domain with a vendored skill or official
  docs (turbo, uv, AWS, Inspect AI, …), **verify against the primary source first.** A finding — Codex's, Claude's,
  or your own — is a *hypothesis to confirm*, not a fact. This covers config-soundness questions
  (caching/hashing/idiom), not just new API code. A 60-second primary-source check beats the
  overengineer-then-revert cycle.
- **Context:** #19 CI review; `turborepo` skill + turborepo.dev/docs. Pairs with
  [[local-aws-emulator-must-prove-read-api]].

## 2026-06-21 — never-merge-without-explicit-user-approval
- **Mistake:** Squash-merged PR #101 myself after green CI + the gstack `/review`, reading CLAUDE.md's "merge only
  on green CI verify + `/review`" as standing authorization — but the user had not reviewed the diff or said
  "merge." The user flagged it.
- **Rule:** Merging is an outward, hard-to-reverse action — get **explicit user approval before merging any PR**,
  even on green CI + a passing `/review`. CLAUDE.md's "merge on green + /review" states the *gate conditions*, not
  a blanket pre-authorization: present the PR as merge-ready and **wait for the user's go**. Same bar for
  revert / force-push / branch-protection changes.
- **Context:** #19 / PR #101. Pairs with the harness rule on outward/hard-to-reverse actions.

## 2026-06-21 — codex-reviews-run-at-xhigh-not-the-skill-default-high
- **Mistake:** Ran the gstack `/review` Codex pass with the skill's hardcoded `model_reasoning_effort="high"`,
  silently overriding this repo's **gpt-5.5 xhigh** standard. The model was right; effort dropped a tier. The user
  caught it.
- **Rule:** For Codex passes in this repo (`/review` Step 5.7, `/codex`, or a direct `codex exec`/`codex review`),
  explicitly pass **`-c 'model_reasoning_effort="xhigh"'`** — the gstack templates pin `high`, and `-c` overrides
  the config default. Confirm the run banner shows `reasoning effort: xhigh` before trusting the pass.
- **Context:** #19 CI review; `~/.codex/config.toml` (model=gpt-5.5, effort=xhigh).

## 2026-06-20 — tailor-borrowed-patterns-to-this-environment
- **Mistake:** Added a fork-PR `if:` gate (public-repo boilerplate) to a **private, fork-less** repo where forks
  can't occur. The user cut it.
- **Rule:** Tailor borrowed patterns to THIS environment — don't paste a public-repo idiom into a private repo or
  guard a case that can't occur (YAGNI). Default to shipping less; verify and minimize before adding or asserting.
- **Context:** `.github/workflows/localstack-smoke.yml` (E0-3). Pairs with the YAGNI bar in `CLAUDE.md` +
  [[no-comments-explaining-the-absence-of-something]].

## 2026-06-20 — no-comments-explaining-the-absence-of-something
- **Mistake:** After removing the bogus fork-PR gate, I added a comment narrating its absence ("No fork-PR gate:
  the repo is private…"). The user cut it.
- **Rule:** Never comment to explain the **absence** of something — comments justify what IS present (non-obvious
  boundaries, security/trust rules), not what isn't.
- **Context:** `.github/workflows/localstack-smoke.yml` (E0-3). Pairs with the lean-docs bar in `CLAUDE.md`.

## 2026-06-20 — local-aws-emulator-must-prove-read-api
- **Mistake:** Assumed the current `localstack/localstack` image still provided a free, tokenless community dev
  loop for a private repo, and treated generic "LocalStack replacement" options as plausible substitutes before
  proving the verifier's actual read path.
- **Rule:** Before choosing or wiring a local AWS emulator, verify the exact API the verifier needs against
  current primary docs and a smoke test — for AssayOps, Cloud Control `GetResource`/`ListResources` or the CFN
  read/drift API in the AC, not just "S3 works." Current LocalStack requires an auth token + a paid plan for
  commercial use; Moto, Floci, MiniStack, Testcontainers are not drop-in unless they pass the exact read-path
  smoke. If cost-free conflicts with that, flag the decision instead of silently changing the substrate.
- **Context:** #20; LocalStack 2026 auth/licensing change; Floci/MiniStack passed S3 but failed Cloud Control
  `GetResource`.

## 2026-06-19 — shipped-docs-no-issue-numbers-no-narration
- **Mistake:** The `AssayInc/skills` README + eval `RESULTS.md` carried GitHub issue/PR numbers and
  status-log/AI-chat narration ("All five skills now live here", "more skills are being distilled"). The user cut
  it.
- **Rule:** Shipped **reference** docs others read — READMEs, eval `RESULTS.md`, any non-work-tracker doc — stay
  clean and timeless: **no GitHub issue/PR numbers**, no changelog/status narration, no conversational AI framing.
  State what *is*, factually. **Distinction:** issue numbers DO belong in the **work-trackers** (`PROGRAM.md`,
  `ISSUES.md`, lessons) — just not shipped reference docs or `CLAUDE.md`.
- **Context:** `AssayInc/skills` README + `evals/*/RESULTS.md` (#86). Extends [[claude-md-is-lean-no-issue-numbers]].

## 2026-06-19 — claude-md-is-lean-no-issue-numbers
- **Mistake:** Bloated `CLAUDE.md`'s skills section with a flat enumeration of every source repo + per-skill
  annotations + GitHub issue/epic numbers. The user cut it: issue numbers "do not add any value," and the repo
  list duplicated `skills-lock.json`.
- **Rule:** `CLAUDE.md` is for what an agent can't infer from the repo — short, specific, actionable. **No GitHub
  issue/epic numbers** (`#N`, `E0-N`, `T`/`I` labels); state decisions as plain facts (date if needed) and link a
  real anchor (`DECISIONS.md §N`, `ISSUES.md`) when detail lives elsewhere. The skill inventory lives in
  `skills-lock.json` (source of truth) + auto-loads by description — don't re-list it. Prune `CLAUDE.md` like code.
- **Context:** #85 `CLAUDE.md` skills section. Pairs with [[claude-md-serves-all-agents-no-dedupe]] —
  completeness vs conciseness.

## 2026-06-19 — verify-skill-absence-beyond-the-registry
- **Mistake:** Concluded "no official Inspect AI skill exists" from `npx skills find` (registry) alone, and judged
  officialness by the repo's GitHub org slug. Both wrong: `meridianlabs-ai/inspect-skills` exists (not
  registry-indexed), and Meridian Labs maintains `inspect_ai` even though the repo still sits under
  `UKGovernmentBEIS`.
- **Rule:** Before asserting a tool/skill "doesn't exist" or "isn't official," look beyond the skills.sh registry:
  check the maintaining project's own GitHub org and a `<tool>-skills` repo, and read who actually *maintains* the
  upstream (not the org slug). `npx skills find` indexes a subset — a negative means "not in the registry," not
  "doesn't exist." Phrase absence as "none found in <where I looked>."
- **Context:** #85, the Inspect AI lane. Pairs with [[skills-sync-hygiene]].

## 2026-06-19 — skills-add-default-agent-targeting
- **Mistake:** Installed a skill with `npx skills add <src> -a '*'`, reading `*` as "this project's agents." It
  means **all 72 agents skills.sh knows**, vendoring the skill into dozens of stray per-agent dirs (incl.
  gitignored ones like `.aider`/`.cursor`) instead of the repo's 3-dir layout — and quietly, since many are
  gitignored.
- **Rule:** Add skills with the **default agent targeting** (omit `-a`): it extends the repo's existing
  `.agents/skills/` + `.claude/` + `.hermes/`. **Never `-a '*'`.** After **every** `skills add`, run `git status
  --porcelain` and confirm ONLY `.agents/`, `.claude/`, `.hermes/`, `skills-lock.json` changed; back out any other
  new dir (`npx skills remove <name> -a '*' -y`, then `rm -rf` stragglers) and re-add without `-a '*'`. Preview
  multi-skill repos with `--list` and install only the needed `--skill <name>`.
- **Context:** #85, `npx skills add`. Pairs with [[skills-sync-hygiene]].

## 2026-06-19 — eval-is-part-of-the-skill
- **Mistake:** Built the `assay-brain` skill, verified its CLI by hand, and called it done — scoping `evals/` out
  as a follow-up. That shipped a *verification* skill with no verification that it triggers or improves answers.
  The user caught it.
- **Rule:** A skill is not done until its eval is **authored AND run.** Follow the `skill-creator` loop:
  `evals.json` (3+ realistic cases) + `trigger-eval.json` (~10 should / 10 should-not) + a with/without A/B
  (subagents) + a `claude -p` trigger probe, with the outcome in `RESULTS.md`. Also run `quick_validate.py` and
  check the SKILL.md `description` against the agentskills.io **1024-char limit**.
- **Context:** #86 / `AssayInc/skills#1`. The eval caught a real defect the hand-check + code-review both missed
  (a 1490-char description).

## 2026-06-18 — claude-md-serves-all-agents-no-dedupe
- **Mistake:** Trimmed the gstack skill list + routing out of `CLAUDE.md`, reasoning it duplicated
  `~/.claude/CLAUDE.md` and was context bloat.
- **Rule:** Never dedupe the project `CLAUDE.md`/`AGENTS.md` against Claude-only global config or plugin skills.
  `AGENTS.md` is read by non-Claude agents (Codex) that never load `~/.claude/CLAUDE.md`, so anything every agent
  needs — the full gstack skill list + routing, the `/browse`-only rule, operating rules — must live in this
  repo's file. Default to **completeness** for cross-agent content; only omit what is genuinely irrelevant to this
  repo (UI, machine-local gbrain config).
- **Context:** #18 `CLAUDE.md`; the user caught the missing gstack section.

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
