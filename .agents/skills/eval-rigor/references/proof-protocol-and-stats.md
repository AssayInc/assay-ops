# Proof protocol & statistics — the details

Load this when you are actually designing the held-out eval, choosing baselines, computing the lift, or
writing the pre-registration. `SKILL.md` is the discipline; this file is the protocol, the statistics, and
the contamination checklist. Grounded in public methodology + the brain
(`[[concepts/eval-to-performance-proof]]`, `[[concepts/benchmark-saturation]]`,
`[[projects/assay/proof-first-plan]]` — recall via **assay-brain**).

- [The baseline matrix](#the-baseline-matrix)
- [The OOD slice + the circularity objection](#the-ood-slice--the-circularity-objection)
- [Pre-registration template](#pre-registration-template)
- [Clustered standard errors — why, and by what](#clustered-standard-errors--why-and-by-what)
- [Contamination checklist](#contamination-checklist)
- [Precondition: the reward must be trustworthy](#precondition-the-reward-must-be-trustworthy)

## The baseline matrix

"Lift" is a *difference*, so the baseline is half the claim. Run the same eval on every arm; the headline is
lift over the **strongest** arm, not the weakest — but the *max over arms is a selected quantity*, so define
the estimand as **Δ = AssayOps − max_b baseline_b** and bound it with a **paired, task-level bootstrap that
resamples all arms together** (or pass every pairwise gap under a family-wise rule). Don't pick the
best-*observed* arm post-hoc and attach a two-arm SE.

| Arm | What it controls for | What beating it proves |
|---|---|---|
| Same model, **zero-shot** | the floor | only that *some* training helps — table stakes, never the headline |
| Same model, **SFT'd on non-AssayOps infra data** | "more infra tokens" | the lift is from the **environments**, not just domain exposure |
| Same model, **synthetic-task-gen / rejection-sampling** | "cheap data" | AssayOps beats **cheap alternatives** a lab would try first |
| Same model, **SFT'd on AssayOps environments** | — | the treatment arm |

A lift reported only over zero-shot is the single most common way an otherwise-real result gets discounted on
sight.

## The OOD slice + the circularity objection

The headline metric is lift on a **private, post-cutoff out-of-distribution** slice. A same-generator
held-out set estimates *in-generator* generalization — a real but weaker claim — and is **insufficient** for
a transfer/capability proof: a reviewer reads a same-generator headline as circular (train and eval drawn
from one generator can reflect the generator's regularities — templates, naming, resource shapes — not
transferable capability). The OOD slice carries the claim:

- **Hand-authored tasks structurally different from the generator** — different task shapes, services, and
  intents than the generator emits — and **built clean** (post-cutoff configs/regions/names; contamination
  checklist below).
- **A public external anchor is secondary/contextual, not the headline.** `[[references/swe-infrabench]]`
  (arXiv:2606.05249, NeurIPS 2025 Workshop: incremental CDK edits graded by held-out tests; best model ~34%,
  a specialized reasoner ~24%) or a public IaC eval is "untouched" **only if post-cutoff and decontaminated
  for the *specific evaluated model***. "Training" includes the base model's pretraining, SFT/RL, and agent
  scaffolding — not just the AssayOps SFT — so most public sets are already reachable. Cite-only, caveated;
  **no task reuse** into training.
- **Same-generator held-out → secondary**, always labeled as such.

The deploy-grounded extension AssayOps adds over SWE-InfraBench's unit-test grading: success is
*reconciliation against live cloud state* (`[[concepts/deterministic-verification]]`), which is harder to
game and harder to leak than recallable gold patches.

## Pre-registration template

Write this **before** the run and don't edit it after seeing results. It is what converts "demo" into
"evidence":

- **Estimand** — Δ = pass-rate(AssayOps-SFT) − pass-rate(**max** baseline) on the private OOD slice
  (max-selection defined up front; computed inside the bootstrap, below).
- **Success rule** — a **CI-based** criterion, not a bare point: e.g. *lower 95% CI bound of Δ > +8 pts*
  (or the weaker *point ≥ +8 pts and lower CI > 0*), with the **threshold ≈ +8–10 pts**, the alpha, and the
  CI method all named **before** any result is seen.
- **Tasks** — the private held-out set (**≥30**), frozen; the OOD construction recipe; any public anchor as
  a labeled secondary.
- **Baselines** — the full matrix above.
- **Seeds + rollouts** — **≥3 seeds** (state **training vs inference** seeds), **n ≥ 8 rollouts/task**; the
  aggregation (pass-rate per task → mean) and how seed variance is handled (per-seed lifts + sensitivity).
- **Standard errors** — clustered by the dependence structure (task; training-seed separately) with the
  resampling method named (below).
- **Stopping rule** — no peeking-and-extending; the task set and seed count are fixed up front.

A threshold or task set chosen *after* the number is known is p-hacking, and a trained reviewer will assume
it unless the pre-registration predates the result.

## Clustered standard errors — why, and by what

Two **crossed** sources of dependence, handled differently — not one "cluster by task" knob:

- **Within-task rollout correlation.** Each task contributes **n ≥ 8 correlated rollouts** (same difficulty,
  same golden, same resources). Treating them as i.i.d. understates uncertainty — the effective sample size
  is closer to the **number of tasks** than the rollout count, so a naive SE is too small and manufactures
  false significance. **Cluster by task** (cluster-robust SEs, a task-level bootstrap, or a per-task random
  effect).
- **Across training-seed variance.** If the **≥3 seeds are training/SFT seeds**, each is a *different model*
  — a second, **crossed** axis affecting all tasks, and 3 seeds barely estimate it. So don't fold it into the
  task clustering: **report per-seed lifts**; for a **pooled** task-clustered interval, resample **task IDs
  once** and carry each task's full seed × arm cells together (a *per-seed* bootstrap is a separate,
  conditional interval); and treat **seed generalization as sensitivity-only** — with n = 3 it isn't
  estimated, only bounded. The paired bootstrap keeps each task's per-arm pairing throughout. If the seeds
  are only *inference/rollout* seeds (same model), say so — they're extra within-task replicates, not a
  second axis, and 3 is not "3 independent models".
- **Selected baseline.** Compute Δ against **max baseline inside the bootstrap** (resample all arms together)
  so max-selection is reflected in the interval — never picked first, then a two-arm SE bolted on.
- **Report the interval, not the point.** "+9 pts (95% CI [+4, +14], task-clustered, 3 training seeds,
  paired bootstrap)" survives scrutiny; "+9 pts" does not.
- **Few clusters → small-sample correction.** With ~30 task-clusters (and only 3 seed-clusters), asymptotic
  cluster-robust SEs are optimistic — prefer a task-level **bootstrap** or a small-cluster correction
  (wild-cluster bootstrap / CR2 + Satterthwaite).

## Contamination checklist

A lift measured against an eval the model already trained on measures **memory, not capability**. The public
SWE-bench audits make it concrete: **~33% of "solved" patches involved solution leakage** (SWE-bench+,
arXiv:2410.06992) and file paths were recalled **up to ~76%** of the time from the issue text alone
(SWE-bench Illusion, arXiv:2506.12286); the brain's record adds the Verified saturation / task-ID-recall
story (`[[concepts/benchmark-saturation]]`). Build the eval clean:

- [ ] **Post-cutoff freshly-authored** configs / regions / names — common AWS/CDK patterns are already in
      pretraining; author around them so the task isn't recallable.
- [ ] **No train/test overlap** — held-out tasks (and their generator seeds) never appear in training; check
      for near-duplicates, not just exact matches.
- [ ] **Private held-out state never published** — the deployed-state golden the verifier reconciles against
      stays in the private store (also the moat).
- [ ] **The proof set itself stays private/hidden** — publishing the *task prompts/specs* makes them
      trainable and leaderboard-overfittable, so the set the lift is computed on is hidden **until retired**.
      The public-benchmark play publishes only **aggregate results, a dev/example split, or retired tasks**;
      hosted grading is contamination-resistant only with **hidden, rotating** tasks/gold. The training
      corpus / gold trajectories / verifier stay private regardless. (Open the eval ≠ publish the proof set.)
- [ ] **Expect the lab's own private eval** — labs will demand generalization to *their* held-out, not just
      AssayOps-authored tasks; an honest proof anticipates it.

This contamination methodology defends the **eval**; it does **not** discharge `red-team-exit-bar`'s
owner-gated eval-leakage vector, which stays OPEN until documented-to-fail under the red-team process.

## Precondition: the reward must be trustworthy

Eval rigor is necessary but not sufficient — it defends the **eval**; the **reward** underneath is defended
separately, and a lift on an untrustworthy reward is as empty as a high score on a leaked benchmark:

- **Determinism** — golden ×K → identical reward (**deterministic-verification**); a flaky reward makes the
  lift unmeasurable, not just noisy.
- **Hack resistance** — the reward survives its red-team attack list, R1 any-open-vector⇒STOP
  (**red-team-exit-bar**).

Contamination resistance + hack resistance are the **two halves of one claim** — ship neither alone.

## Corpus-scale spike (flag, don't paper over)

A ~30–50-task held-out set is **thin** for a low-variance lift, and a lab will ask whether the result scales.
Don't ship an underpowered number as if it were the proof: pair the first proof with the
**procedural-generation scaling story** (how the corpus grows to thousands of tasks at constant verifier
trust). If the variance is too high to clear the pre-registered threshold honestly at current scale, that is
a **flag-the-issue** moment, not a reason to drop a seed or cherry-pick the slice.

## Pointers

- **The proof + why it converts a lab:** `[[concepts/eval-to-performance-proof]]`.
- **The contamination cautionary tale:** `[[concepts/benchmark-saturation]]`.
- **The locked thresholds + success criteria:** `[[projects/assay/proof-first-plan]]`,
  `[[projects/assay/eng-architecture]]`.
- **The two halves of the reward:** **deterministic-verification**, **red-team-exit-bar**. Recall the brain
  via **assay-brain**; never hard-code a path.
