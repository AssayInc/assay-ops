---
name: eval-rigor
description: >
  How to design and defend the AssayOps eval-to-performance proof so a post-training lead can't dismiss it
  in 60 seconds. Use it whenever you build or review the eval harness, the held-out task set, the lift
  measurement, or the baselines. The discipline: a free-floating lift number is demo-rich, evidence-poor —
  the headline must be lift on an out-of-distribution slice (same-generator held-out is in-generator, not
  transfer), over the strongest honest baseline (not just zero-shot), with ≥30 tasks, ≥3 seeds, clustered
  SEs, and a pre-registered +8–10pt threshold; the eval must be contamination-resistant (post-cutoff
  fresh configs, private state unpublished) or it measures memory, not capability; and the reward underneath
  must be hack- and flake-resistant or the lift is noise. Triggers on "measure the lift", "held-out eval",
  "is this number real", "baseline", "contamination", "eval rigor" — even when unnamed. NOT the reward's
  red-team gate (red-team-exit-bar) or the verifier boundary (write-isolated-verifier).
compatibility: >
  Self-contained guidance. The methodology anchors are public (SWE-InfraBench arXiv:2606.05249, the
  SWE-bench contamination literature, cluster-robust SEs, pre-registration, Inspect AI — no checkout); the
  project proof design + thresholds are recalled through the co-located assay-brain skill, a sibling in this
  same repo that resolves the brain and degrades gracefully if it isn't checked out. Never hard-code a brain
  path. Designed for Claude Code; portable to any skills-compatible agent.
metadata:
  author: AssayInc
  version: "1.0.0"
  repository: https://github.com/AssayInc/skills
  provenance: "brain [[concepts/eval-to-performance-proof]], [[concepts/benchmark-saturation]], [[projects/assay/proof-first-plan]], [[projects/assay/eng-architecture]] (eval design T2); public: SWE-InfraBench arXiv:2606.05249, IaC-Eval, the SWE-bench Verified contamination literature, cluster-robust standard errors, pre-registration, Inspect AI"
---

# Eval Rigor — make the lift number survive a skeptical post-training lead

The whole company rests on **one number**: train an open model on a slice of AssayOps environments, show
**measurable lift** on a held-out infra benchmark it never saw. That number is what a post-training lead
*buys* — and a free-floating lift figure is **demo-rich, evidence-poor**: dismissed in 60 seconds. This
skill is how to design the proof so it **survives the dismissal**. The proof design and thresholds live in
the **Assay brain** (recall via the **assay-brain** skill); the methodology and the cautionary benchmarks
are public. This is the eval half of the claim — the reward half is **red-team-exit-bar**.

> **Stance.** A lift number you can't defend is worse than no number — it burns the one meeting that
> matters. The audience is an adversarial expert who has seen a hundred inflated benchmarks. When unsure
> whether a number holds, **pre-register and measure it honestly, or flag it** — never ship a figure you'd
> have to retract.

## The proof is adversarial — design for the dismissal

A post-training lead dismisses a lift number in 60 seconds with three questions: *lift over **what**?*,
*measured on **what** the model never saw?*, and *is the **reward** under it trustworthy?* (brain
`[[concepts/eval-to-performance-proof]]`). Every choice below answers one of those. If your design doesn't,
the number is demo-rich and evidence-poor — it proves you *built* environments, not that they *work*.

## OOD is the headline; same-generator held-out is secondary

The single most important design choice (brain `[[concepts/eval-to-performance-proof]]`, locked eval design
T2 in `[[projects/assay/eng-architecture]]`):

- **Headline = lift on a private, post-cutoff OOD slice** — hand-authored tasks **structurally different**
  from the generator, built clean (see contamination control). This private held-out carries the capability
  claim.
- **A public external anchor is secondary/contextual, never the headline** — a public set
  (`[[references/swe-infrabench]]` / a public IaC eval) counts as "untouched" only if it is **post-cutoff and
  decontaminated for the *specific evaluated model***. "Training" spans base pretraining, SFT/RL, and agent
  scaffolding — not just the AssayOps SFT — so most public benchmarks are already reachable; cite them as
  context, caveated.
- **Same-generator held-out is *insufficient*, not the headline** — it estimates *in-generator*
  generalization (a real but weaker claim); a reviewer reads a same-generator headline as circular for a
  transfer/capability proof. Report it as a secondary number, never the lede.

Construction details + the circularity argument: **`references/proof-protocol-and-stats.md`**.

## Beat the strongest honest baseline, not zero-shot

"Lift" is meaningless without naming what it is lift *over*. The baseline set (brain
`[[concepts/eval-to-performance-proof]]`):

- the **same model zero-shot** — the floor, never the headline comparator;
- the **same model SFT'd on non-AssayOps infra data** — proves the *environments* helped, not just *more
  infra tokens*;
- **synthetic-task-gen / rejection-sampling** arms — proves AssayOps beats **cheap alternatives**, not just
  no-training.

Headline lift is over the **strongest** of these — but "max over baselines" is itself a *selected* quantity:
don't pick the best-*observed* arm and bolt on a naive two-arm SE (winner's-curse inflation). **Pre-register
the estimand** Δ = (AssayOps − max baseline) and get its interval from a **paired, task-level bootstrap that
resamples all arms together**, or require **every** treatment-vs-baseline gap to clear the bar under a
family-wise rule. Beating zero-shot is table stakes a lead discounts on sight.

## The rigor checklist (all required, not a menu)

A number is *defensible* only with all of these (brain `[[projects/assay/proof-first-plan]]`; eval design):

- **≥30 held-out tasks** — fewer is anecdote.
- **≥3 seeds, n ≥ 8 rollouts/task — and say *which* seed.** *Training/SFT seeds* each yield a different
  model (a crossed axis over all tasks; with only 3, seed variance is barely estimated — report per-seed
  lifts + sensitivity, don't imply it's pinned down). *Inference/rollout seeds* are same-model sampling
  noise. Don't silently average the two together.
- **Cluster the SEs by the dependence structure, not reflexively "by task".** Within-task rollouts are
  correlated (so i.i.d. SEs manufacture false significance) → cluster by task for rollout noise; but
  training-seed is a *second, crossed* variance source handled separately (per-seed estimates + a
  task-preserving paired bootstrap). (Mechanics + the small-cluster caveat in the reference.)
- **A pre-registered threshold *and a decision rule*** — not a bare point estimate. Declare the success
  criterion as a **CI-based rule** (e.g. *the lower 95% CI bound for Δ = AssayOps − max baseline exceeds
  +8 pts*; or the explicitly-weaker *point ≥ +8 pts **and** lower CI > 0*) plus the alpha / CI method, the
  tasks, seeds, and baselines — all **before** the run. A point estimate that clears +8 with a CI crossing
  zero is not a proof; a threshold chosen *after* the result is p-hacking. Pre-registration converts "demo"
  into "evidence".

## Contamination control — or you measure memory, not capability

A high score on a **leaked** benchmark proves nothing. The cautionary tale is the SWE-bench family:
independent audits found **~33% of "solved" patches involved solution leakage** (SWE-bench+,
arXiv:2410.06992) and models recalling the correct **file paths up to ~76%** of the time from the issue text
alone (SWE-bench Illusion, arXiv:2506.12286) — recall, not capability. The brain's record adds the Verified
saturation / task-ID-recall story (recall via **assay-brain**). A lift measured on a benchmark the model has
already seen measures memory, not the capability you're selling.

So the held-out eval is built **clean**:

- **Post-cutoff freshly-authored** configs / regions / names (common AWS/CDK patterns are already in
  pretraining — generate around them).
- **No train/test overlap**; the **private held-out state is never published**.
- **The proof held-out stays private; "open the eval" ≠ publish the proof set.** Publishing task
  prompts/specs makes them trainable and leaderboard-overfittable, so the set you compute the lift on is
  **hidden until retired**; the public-benchmark play (authority) publishes only **aggregate results, a
  dev/example split, or retired tasks**, and hosted grading is contamination-resistant only with **hidden,
  rotating** tasks/gold. The **training corpus, gold trajectories, and verifier** stay private regardless.

## The reward must hold, or the lift is noise

Eval rigor is **half** the claim; the other half is the reward underneath. A lift measured on a **gameable**
or **non-deterministic** reward proves nothing — exactly like a high score on a leaked benchmark. Before any
lift claim:

- **Verifier-determinism check** — golden ×K → identical reward (**deterministic-verification**). A flaky
  reward makes the lift unmeasurable.
- **Red-team gate green** — the reward survives its attack list, R1 (**red-team-exit-bar**). A lift on a
  forgeable reward is a lift on nothing.

**Contamination resistance defends the eval; hack resistance defends the reward — two halves of one claim**
(brain `[[concepts/eval-to-performance-proof]]`). Ship neither half alone. This contamination *methodology*
**does not by itself close** `red-team-exit-bar`'s eval-leakage vector — that stays **OPEN until
documented-to-fail** under the owner-gated red-team process; this skill informs it, it doesn't discharge it.

## Anti-patterns = a dismissible number (you will be tempted; don't)

| Tempting shortcut | Why a lead dismisses it | Instead |
|---|---|---|
| "Headline the same-generator held-out lift." | Measures *in-generator* generalization, not transfer — insufficient for a capability claim. | Headline a private, post-cutoff OOD slice; public anchor secondary. |
| "Lift over the zero-shot baseline." | Beating no-training is trivial; doesn't beat cheap alternatives. | Strongest baseline: non-AssayOps-SFT + synthetic-gen / rejection-sampling. |
| "We hit +12 pts — ship it." (no pre-registration) | A threshold/analysis chosen after seeing results is p-hacking. | Pre-register the threshold, decision rule, tasks, seeds, baselines first. |
| "One seed, big gap." | No across-seed variance; a training-seed gap could be the seed, not the data. | ≥3 seeds (say which kind); per-seed lifts + sensitivity. |
| "Mean ± a naive standard error." | Within-task rollouts are correlated → false significance. | Cluster by task for rollout noise; handle training-seed variance separately. |
| "+9 over the best baseline, naive two-arm SE." | Max-over-baselines is selected → winner's-curse inflation. | Pre-register Δ vs max baseline; paired bootstrap over all arms. |
| "Measure against a public benchmark." | It may be in *pretraining* — you'd measure memory (the SWE-bench leakage audits). | Private post-cutoff held-out, decontaminated for the evaluated model. |
| "Lift is +10 on our verifier — done." | A gameable / flaky reward makes the lift meaningless. | Determinism check (golden ×K) + red-team gate green first. |
| "Publish the proof held-out tasks (or the corpus)." | Published tasks become trainable/overfittable; the corpus leaks the moat. | Keep the proof set private/hidden; publish only retired/aggregate/dev. |

## Prove it or flag it

- The proof is **pre-registered**: baselines, OOD slice, ≥30 tasks, ≥3 seeds, threshold — declared **before**
  the run. A number designed after the fact is dismissible.
- The headline is a **private, post-cutoff OOD held-out**; a public anchor is **secondary** (only if
  decontaminated for the evaluated model), and same-generator held-out is **secondary** — never the lede.
- The eval is **contamination-checked** (post-cutoff fresh, no overlap, private state unpublished) **and** the
  reward is **determinism-checked + red-team-green** — both halves, or the number doesn't ship.
- If the corpus is too thin for low-variance lift (~30–50 tasks is thin), **flag it** and pair the proof with
  the procedural-generation **scaling story** — don't ship an underpowered number as if it were the proof.

## Going deeper

**Dependency-free anchors (no checkout).** Public methodology + benchmarks: **SWE-InfraBench**
(arXiv:2606.05249 — the contamination-resistant infra precedent; best model ~34% on incremental CDK edits),
**IaC-Eval** (NeurIPS 2024 — high static validity ≠ semantic correctness; GPT-4 ~19% pass@1 over 458
scenarios), the **SWE-bench** contamination audits (SWE-bench+ arXiv:2410.06992; SWE-bench Illusion
arXiv:2506.12286), **cluster-robust standard errors** (with small-cluster bootstrap corrections),
**pre-registration**, and **Inspect AI** (the eval harness — the deploy-verifier runs as a `Scorer`). The baseline matrix, the pre-registration template, the
clustered-SE mechanics, and the contamination checklist: **`references/proof-protocol-and-stats.md`**.

**Project rationale.** The proof design, the OOD/T2 decision, the thresholds, and the contamination story
live in the brain — `[[concepts/eval-to-performance-proof]]`, `[[concepts/benchmark-saturation]]`,
`[[projects/assay/proof-first-plan]]`, `[[projects/assay/eng-architecture]]` — recall via the **assay-brain**
skill (a sibling in this same repo; never hard-code a brain path). The two halves of the claim:
**deterministic-verification** + **red-team-exit-bar** (reward), this skill (eval). The boundary:
**write-isolated-verifier**.
