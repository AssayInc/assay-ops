---
name: write-isolated-verifier
description: >
  The AssayOps trust boundary, compiled for the moment you write or review reward-path code. Use it
  whenever you touch the write-isolated verifier or anything feeding it: the verifier core, the
  reward core (diff IR → reward), the per-tool IaC adapters, the reward ledger, the OpenEnv
  env-server boundary, or account A/B wiring — any code that computes, stores, signs, or delivers a
  reward, or reads deployed state. The rule it enforces: the verifier runs in account B with zero
  agent creds/network, grades deployed state read-only, and NEVER runs the agent's `cdk synth` /
  `terraform plan` (or any agent code) — so reward can't be forged. Triggers on "grade the
  deployment", "compute the reward", "diff deployed state", "write the adapter", "sign/store the
  reward record", "cross-account read", "is this a trust break" — even when the boundary isn't named.
  NOT for generic AWS/CDK/Terraform authoring with no reward path (use aws-cdk / aws-iam), NOT for
  the reward record's KMS/JCS/WORM mechanism (use reward-ledger-worm).
compatibility: >
  Self-contained guidance. The AWS primitives are in official AWS / RFC docs (no checkout needed);
  the deeper project rationale is recalled through the co-located assay-brain skill — a sibling skill
  in this same repo (github.com/AssayInc/skills) that resolves the brain wherever it lives and
  degrades gracefully if it isn't checked out. Never hard-code a brain path. Designed for Claude
  Code; portable to any skills-compatible agent.
metadata:
  author: AssayInc
  version: "1.0.0"
  repository: https://github.com/AssayInc/skills
  provenance: "brain concepts/write-isolated-verifier, concepts/iac-verification-primitives, concepts/reward-hacking, projects/assay/eng-architecture, projects/assay/proof-first-plan; official AWS docs (S3 Object Lock, Cloud Control API, CloudFormation drift, KMS Sign) + RFC 8785 (JCS)"
---

# Write-Isolated Verifier — the trust boundary you must not break

This is the **moat**: a grader the trained agent cannot reach. If you are writing or reviewing code
in the reward path, the single most expensive mistake you can make is to quietly reopen a path from
the agent to the grade. This skill compiles the trust boundary into a task-time checklist so you
catch that at write time, not in a red-team post-mortem. The canonical rules and the *why* live in
the **Assay brain** (the compile-don't-retrieve knowledge base, kept apart from harness code so it
outlasts any single build) and in **official AWS / RFC docs** — recall them through the
**assay-brain** skill, a sibling skill in this same repo. This skill is the operational *how to stay
inside them*; when unsure, recall and flag — don't guess.

> **Stance.** A plausible-but-wrong verifier is worse than none. When unsure, **prove it or flag
> it** — never paper over it. If a task looks like it needs you to cross the boundary, **stop and
> flag it; don't code around it.**

## The one rule (everything else serves this)

The boundary is an **AWS Organizations account / trust-domain split** (brain
`[[projects/assay/eng-architecture]]`, decisions 1C/T1; `[[concepts/write-isolated-verifier]]`):

- **Account A** = the agent's sandbox; its creds reach the playground **only**. The agent's
  `synth`/`plan`/deploy all run **here**, treated as **untrusted data**.
- **Account B** = the verifier/reward account. The agent has **zero credentials and zero network
  path** to it. **There is no A→B trust path.**
- The verifier runs **entirely in B**, reads the **deployed resource state read-only** across the
  boundary, compares it to AssayOps's **independently regenerated golden target**, and emits
  `reward ∈ {0,1}` + a diff report. **Reward never depends on executing agent code.**

If you can state why that holds for the code in front of you, you're inside the boundary. If you
can't, stop.

## You're in scope if you're touching…

the **verifier core**, the **reward core** (diff IR → reward), the **IaC adapters / diff IR**, the
**reward ledger**, the **OpenEnv env-server** boundary, **determinism / replay**, or **account A/B
wiring**. Any of these can silently reintroduce an agent→grade path. The invariants below are
non-negotiable across all of them.

## Invariants — preserve every one

Each is a trust-boundary rule, not a style preference. Violating one is a **trust break**. The
rationale for each lives in the brain (`[[concepts/write-isolated-verifier]]`,
`[[concepts/reward-hacking]]`, `[[projects/assay/eng-architecture]]`).

| # | Invariant | Why |
|---|-----------|-----|
| 1 | The verifier **NEVER** runs the agent's `cdk synth` / `cdk diff` / `terraform plan`, **nor invokes the agent's deployed behavior** (its Lambdas, APIs, ECS tasks, SSM commands, custom-resource callbacks, or self-generated reports) — no agent-authored or agent-controlled code in the grading path. It reads **deployed state** and compares to the **independently regenerated** golden. | Executing *or trusting* agent-controlled behavior in the grader *is* the reward-hacking surface — the CDK-synth-escape / Terraform provider-plugin vectors and their generalization. (decision T1) |
| 2 | The verifier runs in **account B**; the agent has **zero creds + zero network** to B; **no A→B trust path**. | The isolation that makes every other invariant hold. (decision 1C) |
| 3 | **Reward never depends on executing agent code.** `reward ∈ {0,1}` from a **normalized** diff vs the golden. | Execution-grounded = un-gameable. (decisions T1/2A) |
| 4 | Reward records are **KMS-signed + S3 Object Lock (WORM)**, append-only, trajectory-keyed — **never a mutable DB row**. | A mutable row breaks the tamper-evident ledger that *is* the product. (decision 4B) → mechanism: **reward-ledger-worm** skill |
| 5 | The agent's role has **no `kms:Sign`** on the signing key and **no `s3:BypassGovernanceRetention`**; at most **read-only** on what the grader reads. | Immutability without isolation is hollow — the agent must not hold the keys to its own grade. |
| 6 | Golden targets / held-out eval / gold trajectories live in a **private store, never committed** to a code repo. | Contamination control + moat. |

## How to grade — read deployed state, never synth/plan

The constructive read-side rule (brain `[[concepts/iac-verification-primitives]]`; official AWS
docs): the agent **deploys**, then the verifier asks AWS *what is actually live* through APIs the
agent's code never touches, and asserts it matches the golden. Three read paths (full API shapes +
caveats in **`references/grading-primitives.md`**):

- **Cloud Control `GetResource` / `ListResources`** — uniform per-resource state by
  `(TypeName, Identifier)`; reads reality "whether or not provisioned via Cloud Control". The
  workhorse — one API shape across the (large but finite) set of **supported** resource types.
- **CloudFormation `DescribeStackResources`** — stack manifest: did every expected logical resource
  converge to `*_COMPLETE`?
- **Drift detection** (`detect-stack-drift` → poll → `describe-stack-resource-drifts`) — AWS computes
  the diff **server-side** (`IN_SYNC`/`MODIFIED`/`DELETED`), so the grader synthesizes nothing. But
  drift only covers types that *support* it and omits unchecked ones, so a stack can report `IN_SYNC`
  with resources never checked — drift is **one input, never the whole grade**.

**Grade against the expected manifest and fail closed:** reward 1 requires every *expected* resource
to be present and **provably correct** — anything `NOT_CHECKED`, omitted, unsupported, or not readable
via Cloud Control is **non-passing** until covered by a per-resource `GetResource` assertion. Silent
coverage gaps are a read-side spoofing surface (deploy nothing checkable, score 1). Read from the verifier's
**account-B identity**, but reach account A's deployed state by using those B credentials to
**STS `AssumeRole` into a pre-provisioned read-only role in A** (a grant from A — no A→B trust)
and **signing the Cloud Control reads with the returned account-A temporary credentials**. The
target account is whichever credentials **sign** the request — not Cloud Control's `RoleArn`, a
same-account CloudFormation service role (assumed by `cloudformation.amazonaws.com`) that only
scopes the operation's permissions. Reward 1 = **zero normalized diff** between the read-back state and the
regenerated golden (decision 2A). Per-tool adapters normalize into **one diff IR**
feeding a **shared reward core** (decision 6A) — keep tool-specific quirks in the adapter, never in
the core.

## How to store the reward — signed + WORM, in B

Summarized here; the mechanism is the **reward-ledger-worm** skill. The isolation invariant (brain
`[[concepts/write-isolated-verifier]]`; official AWS docs + RFC 8785): the reward is written **once**
(conditional write-once — `If-None-Match: *` / DynamoDB `attribute_not_exists`), made **immutable**
(S3 Object Lock **Compliance** mode), and **signed** by a KMS key the agent never holds (sign over
**RFC 8785 JCS** canonical JSON → SHA-256 → **ECDSA P-256**). All three sit under **account-B
credentials the agent's sandbox cannot assume**. A buying lab can verify each record's signature
with the public key — the reward ledger doubles as **portable, tamper-evident proof**.

## Anti-patterns = trust breaks (you will be tempted; don't)

The shortcuts that look efficient and quietly forge the moat open. Each maps to an attack vector in
the brain's threat model (`[[concepts/reward-hacking]]`, `[[projects/assay/eng-architecture]]`).

| Tempting shortcut | Why it's a trust break | Instead |
|---|---|---|
| "Just `cdk synth` the agent's app and diff the templates." | Runs agent-authored code in the grader — the CDK-synth-escape vector. | Deploy A-side; read deployed state in B. |
| "Grade the agent's `terraform plan` output." | A hostile provider plugin runs with the grader's trust — the Terraform provider-plugin vector. | Read live state / CFN drift, not the plan. |
| "Store reward in a DynamoDB row we can update on rerun." | Mutable reward defeats the WORM ledger — the reward-record forgery/overwrite vector. | Conditional write-once + Object Lock; new trajectory_id, never overwrite. |
| "Let the verifier **trust data fed from account A** — agent-reported context, resource IDs, or a role the agent can influence — to 'simplify' the read." | An A-controlled input in the grade path is read-side spoofing; and the cross-account-assume-role vector is the **A→B** direction (the agent reaching into B), which inverts the boundary. | B **`AssumeRole`s a pre-provisioned, agent-immutable read-only role _in A_** (its trust policy pins the account-B verifier; the agent can't modify or select it) and reads deployed **state** itself, scoped to **B-side episode identity** — a sanctioned **B→A read-only** assume; nothing in B trusts A. |
| "Give the env-server / orchestrator the signing key for convenience." | Anything A-reachable holding `kms:Sign` can forge grades — the reward-forgery vector. | Signing key lives in B only; agent role has no `kms:Sign`. |
| "Trust the agent's reported drift/state to save an API call." | Read-side spoofing — the moat-defeating read-path vector. | Read ground truth yourself; regenerate the golden independently. |
| "Smoke-test the deploy by invoking the agent's Lambda / calling its API / running its ECS task / reading its status report." | Executes or trusts agent-controlled behavior in the grading path — same hole as synth/plan, just at runtime. | Assert on read-only deployed **state**; never invoke agent-deployed behavior or trust an agent-generated report. |
| "Find what to grade from the agent's reported account id / region / stack name / tags / resource ids." | Read-side spoofing — the agent points the grader at a pre-existing compliant resource instead of its real (broken) one. | Bind the grader's discovery scope to the **B-side episode identity** (orchestrator-issued), never agent-supplied inputs. |
| "Edit the golden / a red-team fixture so the test passes." | The agent that writes code must never edit what scores it. | Classify the divergence (real bug vs approved rule change); fixtures change only through their owning review, never to green a test. |

## Prove it or flag it

- The **red-team attack list is the Phase-1 exit bar**, and the kill-criterion is absolute: **any
  open vector ⇒ STOP** — make no public/proof claim on a gameable reward (brain
  `[[projects/assay/proof-first-plan]]`, `[[concepts/reward-hacking]]`).
- New cross-account wiring must ship with a **"no A→B path" assertion**; new adapters with
  **conformance fixtures** and a **determinism check** (golden ×K → identical reward).
- This skill **documents** the threat model; it does not reproduce or edit the red-team vectors /
  golden fixtures — those are owner-gated. Cite the threat model; don't copy the fixture.
- If meeting the acceptance criteria seems to require breaking an invariant above, that's a signal
  the task or a decision needs revisiting — **flag it; don't work around the boundary.**

## Going deeper

**Dependency-free anchors (no checkout required).** The AWS primitives are in the **official AWS
docs** — S3 Object Lock, Cloud Control API (`GetResource`/`ListResources`), CloudFormation drift
detection, KMS `Sign` — and the signing canonicalization in **RFC 8785** (JCS canonical JSON). These
ground the mechanism no matter where this skill is installed.

**Project rationale.** The *why* behind the boundary — the locked decisions and the threat model —
lives in the Assay brain (`[[concepts/write-isolated-verifier]]`,
`[[concepts/iac-verification-primitives]]`, `[[concepts/reward-hacking]]`,
`[[projects/assay/eng-architecture]]`, `[[projects/assay/proof-first-plan]]`). Recall it through the
**assay-brain** skill — a sibling skill in this same repo (github.com/AssayInc/skills) that resolves
the brain wherever it lives and degrades gracefully if it isn't checked out. Don't hard-code a brain
path; ask `assay-brain`.
