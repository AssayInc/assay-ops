# tasks/todo.md — #60 Spike: IAM eventual consistency / readiness gate

> Ephemeral per-session scratchpad (lessons.md: durable records go to GitHub/PROGRAM/DECISIONS, not here).

## Decision (founder, this session)
**"Measure now (real AWS)"** — a bounded engineer probe (NOT an agent episode, so T7's cost-bomb gate
doesn't bind; cost ~ $0), in a throwaway/dev account. Strict floor is "LocalStack-only until T7"; this is a
conscious one-off measurement exception the founder authorized.

## Grounding (reconciled: DECISIONS §1/§3/§5(#15)/§8 + eng-arch 7A + impl-plan §9.2 + brain + skills)
- #60 = impl-plan §9 item 2, verbatim. NOT stale/invented. AC: measure IAM propagation + record a
  readiness-gate recommendation (feeds E2 verifier read-path + E8 episode/account setup).
- The "readiness gate" = **calibrate the 7A transient-retry budget for IAM propagation**, not a new
  mechanism. `deterministic-verification`: a not-yet-propagated IAM role is the canonical *transient* —
  scoring it 0 is a false-negative reward; retry-with-backoff, only a *settled* mismatch is reward 0.
- #80 (landed) already locked read-after-create -> 7A transient, FAIL-CLOSED on genuine; #141 (open) =
  verifier-side read-coverage enforcement. The gate is an INPUT to those, must stay **bounded + FAIL-CLOSED**
  (vector #15: never wait-forever, never skip; timing only from the verifier's independent reads).
- brain `retries-and-backoff`: AWS SDKs class `ResourceNotFoundException` as **non-retryable** -> boto3's
  built-in retry will NOT retry a read-after-create 404 -> the gate is a **purpose-built bounded poll on top**.
  Full-jitter `random(0,1) x min(20000ms, base x 2^n)`, base 50ms transient/1000ms throttle; adaptive mode
  for single-API high-volume AI workloads. No measured propagation number exists anywhere (genuine gap).
- `aws-iam`: canonical IAM-propagation tell = instance-profile "waiter + time.sleep(10)" (~10s slow case);
  verify exact behaviors vs AWS docs. Cloud Control's IAM action prefix is `cloudformation` (DECISIONS §1/#80).
- No verifier/replay pkg exists -> output is a recorded recommendation + a reproducible probe, not wired code.

## Plan
- [x] Ground vs deterministic-verification + brain retries-and-backoff + aws-iam + aws-sdk-python-usage.
- [x] Build the probe (scratchpad `iam_propagation_probe.py`) — boto3, 5 signals, bounded+fail-closed, teardown.
- [ ] **Founder wires a dev/throwaway AWS profile** (no creds in env; no aws CLI — boto3 reads `~/.aws`).
      Verify with read-only `get_caller_identity` (account/ARN only, no secret).
- [ ] Run probe (us-east-1 baseline) -> p50/p95/p99/max per signal; tear down all created roles/policies.
- [ ] Record durably: methodology + script + numbers + readiness-gate recommendation as a **comment on #60**;
      propose the calibrated note for **DECISIONS.md §1** (the 7A read-after-create line) — land on ratification.
      Reconcile explicitly with 7A/#80/#141. Close the spike.
- [ ] Update PROGRAM.md.

## Probe — 5 signals measured per fresh role (delay from CreateRole to first success)
- `iam_read` : iam.get_role                         — IAM control-plane read-after-write (baseline)
- `cc_get`   : cloudcontrol.get_resource            — the verifier's REAL read path (T1/E2) [most important]
- `cc_list`  : cloudcontrol.list_resources contains — enumeration lag -> closed-world (#80/#141)
- `assume`   : sts.assume_role                       — trust-policy propagation (E8 "provision-then-use")
- `perm`     : policy-gated call w/ assumed creds    — authz propagation (deepest; the sleep(10) horizon)

Correctness: poll clients run `retries={"total_max_attempts": 1}` (no hidden SDK backoff skewing timing);
own monotonic clock; typed not-ready exceptions = keep polling, throttle = keep polling, unknown = raise;
unique role name per trial (per-NEW-resource propagation); region pinned; bounded max-wait = the fail-closed
datum. Single region (us-east-1) v1 + caveat: re-measure in the verifier's real region once E8 lands.
