# assayops-adapter-terraform — Terraform deployed-state → diff IR

The Terraform half of the per-tool IaC adapters (DECISIONS.md 6A / T2) — the **A-spike engine**. It
normalizes the verifier's read-only B-side **Cloud Control deployed-state read** into the diff-ir
`NormalizedState(DEPLOYED_READ)` that the shared reward core (`assayops_diff_ir.grade`) diffs against the
independently regenerated golden target. Part of the proof-critical core (`py/packages/*`).

## What it does

`normalize(reads, registry)` is the only public entry. It takes already-settled, already-enumerated
Cloud Control read records and returns a `NormalizedState(DEPLOYED_READ)`, or **fails closed**.

```python
from assayops_adapter_terraform import DeployedResourceRead, normalize

read = DeployedResourceRead(
    type_name="AWS::S3::Bucket",
    identifier="assayops-a1b2c3d4",  # the physical id -- diagnostics only, NEVER the diff address
    properties={
        "BucketName": "assayops-a1b2c3d4",
        "VersioningConfiguration": {"Status": "Enabled"},
        "Arn": "arn:aws:s3:::assayops-a1b2c3d4",  # server-computed -> dropped
        "Tags": [{"Key": "assayops:address", "Value": "primary_bucket"}],
    },
)
state = normalize([read])   # NormalizedState(DEPLOYED_READ) with address="primary_bucket"
```

## The address bridge

Cloud Control returns a resource's **physical** id, but the reward core diffs by **logical** `address`
(the golden's key). The deploy carries that address in a reserved, case-sensitive **`assayops:address`**
tag, which the adapter reads from the resource's schema tag property and uses as `NormalizedResource.address`
(dropping only that tag; user tags are kept, sorted). The tag value is **untrusted deployed-state data** —
it is validated as a logical address, never trusted. The Cloud Control `Identifier` and natural keys are
never the address.

> The deploy must tag every graded resource with `assayops:address = <its logical address>`. This is the
> corpus deploy-tagging convention the engine establishes; the golden uses the same logical addresses.

## Fail closed (never a silent reward)

A read the adapter cannot vouch for raises an `AdapterError` (a `ValueError`) rather than emit a state
that could grade in-sync (DECISIONS.md §5 vector #15). It never silently drops a record. Fail-closed cases:
an unreadable record, an unsupported type, a missing / duplicate / malformed `assayops:address`, a stray
reserved `assayops:*` tag, a wrong-shape tag property, a duplicate logical address, a non-JSON property.

## Per-type registry

A `BridgeRegistry` maps each supported CloudFormation type to a `TypeBridge` — its tag property and its
server-computed `readOnlyProperties` to drop. This is the codified read-coverage matrix: a type is
registered only once a LocalStack `infra-local` smoke proves Cloud Control returns the `assayops:address`
tag for it. `default_registry()` ships the Phase-1 set (`AWS::S3::Bucket`). An unregistered type fails
closed. (Order-insensitive set normalization for policy/ingress lands with the CDK adapter, which has the
nested set-bearing types.)

## The trust boundary (T1)

This package is **pure normalization** — it makes no boto3 call and never runs `terraform`, loads a
provider plugin, or reads the agent's `.tfstate` / plan JSON. Those are untrusted agent code/data, the
reward-hacking surface the moat exists to close. Enumeration, pagination, and the closed-world
`deployed set == golden set` coverage check belong to the verifier's read harness, not here.

The normalization contract — what the adapter strips vs keeps so "no diff" is deterministic — is the
diff-ir package's [`NORMALIZATION.md`](../diff-ir/NORMALIZATION.md).
