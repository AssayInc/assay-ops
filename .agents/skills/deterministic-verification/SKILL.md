---
name: deterministic-verification
description: >
  How to compute a deterministic, execution-grounded reward for the AssayOps verifier — reward in
  {0,1} read from deployed infrastructure state, not a judge model. Use it whenever you build or
  review the reward core (diff IR to reward), the per-tool IaC adapters, the golden-target generator,
  normalization, or the determinism / replay check. The rules: grade deployed state against an
  independently regenerated golden (zero normalized diff = reward 1); normalize away AWS-assigned ids /
  timestamps / suffixes / order or the reward goes flaky; treat a throttle or un-propagated read as
  transient, never a false-negative 0; golden times K must reproduce or the task is quarantined.
  Triggers on "compute the reward", "diff IR", "golden target", "normalize the deployed state", "flaky
  reward", "transient vs genuine failure" — even when not named. NOT for the trust boundary (use
  write-isolated-verifier), NOT for the signed WORM record (use reward-ledger-worm), NOT for generic
  AWS reads (use aws-sdk-js-v3-usage).
compatibility: >
  Self-contained guidance. The AWS read primitives are in official AWS docs (no checkout needed); the
  project rationale and the NSYNC / IaC-Eval citations are recalled through the co-located assay-brain
  skill — a sibling skill in this same repo that resolves the brain and degrades gracefully if it
  isn't checked out. Never hard-code a brain path. Designed for Claude Code; portable to any
  skills-compatible agent.
metadata:
  author: AssayInc
  version: "1.0.0"
  repository: https://github.com/AssayInc/skills
  provenance: "brain concepts/deterministic-verification, references/nsync (arXiv 2510.20211), references/iac-eval, concepts/retries-and-backoff, projects/assay/eng-architecture (decisions 2A/6A/7A); official AWS docs (CloudFormation drift detection, Cloud Control GetResource/ListResources, the CloudFormation resource specification)"
---

# Deterministic Verification — execution-grounded, reproducible reward

The reward comes from **running the work against ground truth** — the deployed infrastructure — not
from a model judging whether it *looks* right. "The reward is a deployment, not an opinion." This
skill is how to compute a reward that is **deterministic** (same deployed state → same reward) and
**reproducible** (golden ×K → identical reward). It is the read-side *computation* layer; the trust
boundary that makes it un-gameable is the **write-isolated-verifier** skill, and the tamper-evident
record is the **reward-ledger-worm** skill. Grounded in official AWS docs + the brain (recall via
**assay-brain**).

> **Stance.** A nondeterministic reward is a flaky grader, and a flaky grader poisons training. When
> unsure, **prove it (golden ×K) or quarantine it** — never ship a reward you can't reproduce.

## Execution-grounded, not judged or compiled

Two regimes — pick the right one:

- **Model-judged (soft).** A VLM/LLM scores whether the output looks correct. Brittle, gameable,
  needs heavy human QA. This is the regime AssayOps exists to replace.
- **Execution-grounded (deterministic).** The environment grades by reading deployed-state **facts** —
  does the resource exist, does the policy validate, is the stack `IN_SYNC`. Binary, hard to fake.
  (This is RLVR applied to cloud infra.)

Use execution-grounded. And **"it compiled" is not execution-grounded**: IaC-Eval found **about half
of IaC that passes the compile/`validate` step is semantically wrong** against intent. Grade
**deployed state**, never `cdk synth` / `terraform validate` success.

## The golden target (2A) — regenerate it; never grade the agent's output

Reward 1 = **zero normalized diff** between the read-back **deployed state** and AssayOps's
**independently regenerated** golden target (a reproducible ephemeral target: code + seed). The
verifier regenerates the golden; it is **never** the agent's submitted config or state (grading the
agent's artifact is grading its self-report — see `write-isolated-verifier`). The canonical predicate
(**NSYNC**, arXiv 2510.20211): a reconciliation is correct when there are **no changes against
ground-truth live state** — the CloudFormation `IN_SYNC` analogue of "`terraform plan` reports no
changes."

But `IN_SYNC` is **not sufficient on its own** — drift detection skips unsupported / `NOT_CHECKED`
resources and nested stacks and only tracks *explicitly-set* properties. **Grade against a coverage
manifest:** every golden resource and intent-bearing property must be verified (drift `IN_SYNC` *or* a
Cloud Control / service read); `NOT_CHECKED` / `UNKNOWN` / `DETECTION_FAILED` / unsupported /
nested-stack omissions are **non-passing**, never assumed-fine.

## The diff IR (6A) — normalize per-tool, reward in the core

Per-tool adapters (Terraform, CDK/CloudFormation, …) normalize read-back deployed state into **one
normalized diff IR**; a shared, **tool-agnostic reward core** computes `reward ∈ {0,1}` from the IR.
Keep every tool-specific quirk in the adapter — the core must never know which tool produced the IR.
The reward is **binary** (zero normalized diff = 1), not a partial-credit / similarity score.

## Normalization — where determinism is won or lost

Read-back state carries fields that differ across *identical-correct* deployments: AWS-assigned
ARNs / physical IDs, generated name suffixes, timestamps, creation/pagination order,
eventual-consistency-dependent values. If the diff includes them, the same correct deployment yields a
**nonzero diff → a nondeterministic reward**. So normalization MUST, before diffing: canonicalize
ordering (sort collections); drop or placeholder **non-intent** AWS-assigned values (the sandbox's own
account id, partition/region where not intent, timestamps, generated name suffixes) and resolve
references **structurally** (logical, not physical id). But **keep intent-bearing ARNs/IDs** — an IAM
policy `Resource`, a principal/trust target, a KMS key, an event target, cross-account wiring — and
normalize only their *variable* segments; dropping the whole ARN would let a permissive or wrong policy
normalize to the golden. Compare the **intent-bearing** properties (validated against the golden's
expected schema — the CloudFormation resource specification is the typed contract). An un-normalized field is a flaky-reward bug, not a
cosmetic one. Details + a per-type checklist: **`references/normalization-and-determinism.md`**.

## Determinism is a property of the grading harness (7A), not just the formula

Live cloud reads hit transients; a deterministic reward depends on the **harness**, not just the diff:

- **Transient vs genuine.** A `ThrottlingException`, a not-yet-propagated IAM role / S3 state
  (eventual consistency), or an in-flight async is **not** a wrong answer. Scoring it 0 emits a
  **false-negative reward** — correct work scored zero, wasting the task's training compute. Classify:
  retry-with-backoff + idempotent reads for transients; only a **settled** mismatch is reward 0.
- **K-run reproduce.** A reward must reproduce: grade K times → identical reward. Variance after
  transient handling means the task is non-deterministic.
- **Quarantine.** Pull non-deterministic tasks (flaky after K-run) **out of the scored set** — never
  ship a flaky reward into training. The determinism check (golden ×K → identical reward) is the gate.

## Anti-patterns = a flaky or gameable reward

| Tempting shortcut | Why it's wrong | Instead |
|---|---|---|
| "Score it with an LLM/VLM judge — does the infra look right?" | Soft, gameable, needs human QA — the regime we replace. | Execution-grounded: grade deployed-state facts. |
| "Grade by `cdk synth` / `terraform validate` / it compiled." | ~50% of compile-passing IaC is semantically wrong (IaC-Eval). | Grade **deployed** state vs the regenerated golden. |
| "Deep-equal the read-back state against the golden JSON." | ARNs / timestamps / suffixes / order → identical-correct deploys diff → flaky reward. | Normalize the IR first (canonical order, drop AWS-assigned/timestamp/suffix). |
| "Grade against the agent's submitted config/state." | Grades the agent's self-report (and reachable code). | Independently regenerate the golden (code+seed); read deployed state. |
| "Any AWS read throws → reward 0, the deploy is broken." | A throttle / un-propagated read is transient → false-negative reward. | Transient/genuine classifier: retry+backoff, tolerate eventual consistency; only a settled mismatch is 0. |
| "Give partial credit / a 0.0–1.0 similarity score." | Fuzzy reward is gameable and not reproducible here. | `reward ∈ {0,1}`: zero normalized diff = 1. |
| "Ship the task even though its reward varies run-to-run." | A non-deterministic reward poisons training. | K-run reproduce; quarantine flaky tasks. |

## Prove it or flag it

- The **determinism check is the gate**: golden ×K → identical reward; any variance (after transient
  handling) ⇒ **quarantine**, don't score.
- Lock normalization with **per-adapter conformance fixtures**: the same deployed state → the same IR
  → the same reward.
- A "deterministic" reward is still **gameable without isolation** — it's only un-gameable if the
  verifier is write-isolated (`write-isolated-verifier`) and the record is WORM-signed
  (`reward-ledger-worm`).
- If a task genuinely can't be made deterministic (a fuzzy signal — incident/SRE health, cost), **flag
  it**: it needs a composite verifier or stays out of the RLVR-clean set — don't force a flaky binary.

## Going deeper

**Dependency-free anchors.** Official AWS docs — CloudFormation **drift detection** (the `IN_SYNC`
predicate), Cloud Control **`GetResource`/`ListResources`**, and the **CloudFormation resource
specification** (the typed assertion schema). The read-API *shapes* live in the
**write-isolated-verifier** skill's `references/grading-primitives.md` — this skill is the
determinism / normalization / golden layer on top, not a re-listing of those APIs.

**Project rationale + citations.** The execution-grounded thesis, the **NSYNC** no-plan-diff criterion
(arXiv 2510.20211), the **IaC-Eval** static-checks-under-grade result, and the determinism policy
(2A / 6A / 7A) live in the brain — `[[concepts/deterministic-verification]]`, `[[references/nsync]]`,
`[[references/iac-eval]]`, `[[concepts/retries-and-backoff]]`, `[[projects/assay/eng-architecture]]` —
recall via the **assay-brain** skill. The trust boundary: **write-isolated-verifier**. The signed
record: **reward-ledger-worm**.
