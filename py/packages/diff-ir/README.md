# assayops-diff-ir — normalized diff IR + shared reward core

The tool-agnostic normalized diff IR and the **shared, write-isolated reward core** (DECISIONS.md 6A) —
the join between the per-tool IaC adapters and the reward the trainer learns from. Part of the
proof-critical core (`py/packages/*`).

## What it does

`grade(deployed, golden)` is the **only** public reward entry. It takes two `NormalizedState`s — the
verifier's read-only read of B-side **deployed** state and the independently regenerated **golden**
target — and returns a `GradeOutcome(reward, diff)`:

- **`reward ∈ {0, 1}`** (the codegen'd `assayops_contracts.Reward`) — `1` iff zero normalized diff.
- **`diff`** — the codegen'd `assayops_contracts.DiffIR`, the per-resource diff report (golden=expected,
  deployed=actual), the thing the reward ledger (E4) digests into `RewardRecord.reportDigest`.

```python
from assayops_diff_ir import grade, NormalizedResource, NormalizedState, Provenance

deployed = NormalizedState(provenance=Provenance.DEPLOYED_READ, resources=(...,))
golden = NormalizedState(provenance=Provenance.GOLDEN_TARGET, resources=(...,))
outcome = grade(deployed, golden)   # GradeOutcome(reward=..., diff=...)
```

## The trust boundary (T1)

The core grades **only** {deployed-state read, golden target}. It **fails closed** (`UntrustedInputError`)
on any other provenance — the agent's `terraform plan`/`show`/state must never reach the grade
(DECISIONS.md T1; the `write-isolated-verifier` skill). This guard is the code-level expression of T1;
it complements, and does not replace, the account-B isolation that is the moat.

## The adapter ↔ core split

Per-tool adapters (Terraform, CDK/CFN; separate packages) and the golden-target generator do the
**tool-specific** normalization and emit `NormalizedState`s; this core owns the **tool-agnostic**,
deterministic diff (resources sorted by address, property paths sorted). The normalization contract —
what the adapter must strip vs keep so "no diff" is deterministic — is in
[`NORMALIZATION.md`](./NORMALIZATION.md).
