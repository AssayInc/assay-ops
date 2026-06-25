# iam-readiness-probe — real-AWS IAM eventual-consistency probe

A measurement tool that quantifies how long a freshly-created IAM role takes to become **readable**
(the verifier's path) and **usable** (the provision-then-assume path), so the verifier's read-path
retry budget (E2) and the episode/account-setup readiness gate (E8) can be calibrated rather than
guessed. Resolves spike #60; the ratified finding lives in [`DECISIONS.md` §1](../../../DECISIONS.md).

## Why this is not LocalStack

`infra-local` proves the read path on LocalStack, whose `CreateBucket` is synchronous — it **cannot**
reproduce eventual consistency. Propagation delay is a real-AWS phenomenon, so this probe runs against
real AWS.

> **It MUTATES real AWS.** Each trial creates and deletes one IAM role + inline policy (cost ~ $0) and
> assumes the role. Run **only** against a throwaway/dev account, never prod or an Orgs-pool account.
> It is a bounded engineer measurement, not an agent episode (so the T7 cost-bomb gate does not bind).

## What it measures

Per fresh role, the wall-clock delay from `CreateRole` to first success of five signals:

| signal | call | surface it calibrates |
|--------|------|-----------------------|
| `iam_read` | `iam.get_role` | IAM control-plane baseline |
| `cc_get` | `cloudcontrol.get_resource` | the verifier's read path (T1/E2) |
| `cc_list` | `cloudcontrol.list_resources` | enumeration lag → closed-world |
| `assume` | `sts.assume_role` | trust-policy propagation (E8 provision-then-use) |
| `perm` | gated call with the assumed role's creds | STS-cred + authz propagation (deepest) |

Poll clients run with SDK retries disabled so botocore's backoff can't skew the timing; a signal not
seen within `--max-wait-seconds` is a bound-exceedance — the datum that sets the fail-closed budget.

## Baseline result (n=20, us-east-1, `AWS::IAM::Role`)

- Reads (`iam_read` / `cc_get` / `cc_list`): resolve on the first poll, **sub-second** (`cc_get` p99
  ~0.76s, 0 bound-exceeded) → the verifier read path is largely insulated from IAM eventual consistency;
  a small fail-closed retry budget suffices.
- `assume`: **p50 ~7.1s** (tight). `perm`: **p50 ~7.7s with a tail to ~42s** → the delay is on
  provision-then-use; gate first use of a fresh cross-account role behind a bounded (~60s), fail-closed
  readiness poll, isolated from the grade. Measured **same-account** (one session) — re-measure
  cross-region and cross-account once the account pool (E8) lands.

## Run it

1. Wire a throwaway/dev-account profile (e.g. `assay-iam-spike`) into `~/.aws/credentials`; the caller
   needs IAM create/read/delete-role, `sts:AssumeRole`, and `cloudformation:GetResource`/`ListResources`
   (the Cloud Control prefix is `cloudformation`). `AdministratorAccess` on a throwaway account is
   simplest and avoids a missing permission being misread as propagation lag.
2. `bun run --filter @assayops/iam-readiness-probe probe -- --profile assay-iam-spike --yes` (or
   `uv --directory <repo> run python iam_propagation_probe.py --profile assay-iam-spike --yes`). The
   `--yes` flag is required: it gates every mutating path so a forgotten `--profile` can't silently
   create/delete roles in whatever account the default credential chain resolves to.
3. Sweep any orphan from a crashed run: append `--cleanup-only --yes` (matches the name prefix AND the
   probe tag, so it never touches an unrelated role).

Flags: `--trials` (default 12), `--region` (default us-east-1), `--max-wait-seconds`, `--poll-interval`,
`--skip-list`, `--trust-principal`, `--yes`.
