#!/usr/bin/env python3
"""IAM eventual-consistency propagation probe -- AssayOps spike #60.

Per freshly-created IAM role + inline policy, measures the wall-clock delay from CreateRole until
each readiness signal first succeeds:

  iam_read : iam.get_role -- IAM control-plane read-after-write (baseline)
  cc_get   : cloudcontrol.get_resource -- the verifier's REAL read path (T1/E2); primary signal
  cc_list  : cloudcontrol.list_resources -- enumeration lag -> closed-world (#80/#141)
  assume   : sts.assume_role -- trust-policy propagation (E8 provision-then-use)
  perm     : gated call with assumed creds -- authz propagation (deepest; the sleep(10) case)

Reports p50/p95/p99/max across N trials. Bounded + fail-closed: a signal not seen within the
--max-wait-seconds bound is recorded as a bound-exceedance (None) -- the datum that calibrates the
readiness gate's retry budget. Creates one role + one inline policy per trial in the target
(throwaway/dev) account; tears them down in a finally.

This MUTATES real AWS (creates/deletes IAM roles + policies; STS/Cloud Control reads). Cost ~ $0. It
is a bounded engineer measurement, not an agent episode. Run only against a dev/throwaway account.

Baseline result (n=20, us-east-1, AWS::IAM::Role): reads (iam_read/cc_get/cc_list) effectively
immediate (p99 < 0.2s); assume p50 ~7.1s; perm p50 ~7.2s with a tail to ~41s. See issue #60.

Usage:
  uv --directory <repo> run python iam_propagation_probe.py --profile assay-iam-spike
  uv --directory <repo> run python iam_propagation_probe.py --profile assay-iam-spike --cleanup-only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from collections.abc import Callable

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

# Identifying tag + name prefix so any orphaned role from a crashed run is findable and sweepable.
_TAG_KEY = "assay-spike"
_TAG_VALUE = "iam-eventual-consistency-60"
_NAME_PREFIX = "assay-iam-spike-"
_INLINE_POLICY_NAME = "probe-inline"
_SIGNALS = ("iam_read", "cc_get", "cc_list", "assume", "perm")
_ROLE_TYPE = "AWS::IAM::Role"

# A benign, free, account-scoped read granted by the inline policy, to measure authz (perm)
# propagation from the assumed role's creds. s3:ListAllMyBuckets has no resource and is free.
_GATED_ACTION_POLICY = {
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Action": "s3:ListAllMyBuckets", "Resource": "*"}],
}

# Poll clients must NOT retry internally: botocore's backoff would inject hidden sleeps and skew the
# measured propagation time. We poll on our own monotonic clock instead.
_NO_RETRY = Config(retries={"total_max_attempts": 1}, connect_timeout=5, read_timeout=10)


def _trust_doc(principal_arn: str) -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Principal": {"AWS": principal_arn}, "Action": "sts:AssumeRole"}
            ],
        }
    )


def _percentile(sorted_vals: list[float], q: float) -> float:
    """Nearest-rank percentile (q in [0,1]); sorted_vals must be non-empty and sorted ascending."""
    if not sorted_vals:
        raise ValueError("empty")
    k = max(0, min(len(sorted_vals) - 1, int(round(q * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def _try(call: Callable[[], object], not_ready: tuple[type[BaseException], ...]) -> bool:
    """Run a read call; True on success, False on a not-ready/throttle signal, else re-raise."""
    try:
        call()
        return True
    except not_ready:
        return False
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        # Throttling and the access/not-found family are "still propagating" -> keep polling.
        if code in {
            "Throttling",
            "ThrottlingException",
            "TooManyRequestsException",
            "RequestLimitExceeded",
            "AccessDenied",
            "AccessDeniedException",
            "ResourceNotFoundException",
            "ResourceNotFound",
            "NoSuchEntity",
        }:
            return False
        raise  # unknown error: fail loud (mis-scoped perms, bad region, etc.)


def probe_once(
    iam: BaseClient,
    cc: BaseClient,
    sts: BaseClient,
    session: boto3.Session,
    region: str,
    account: str,
    trust_principal: str,
    trial: int,
    max_wait: float,
    poll_interval: float,
    skip_list: bool,
) -> dict[str, float | None]:
    """One trial: create a fresh role+policy, poll each signal to first-success, tear down."""
    role_name = f"{_NAME_PREFIX}{trial:02d}-{uuid.uuid4().hex[:8]}"
    signals: dict[str, float | None] = {k: None for k in _SIGNALS}
    if skip_list:
        signals["cc_list"] = -1.0  # sentinel: not measured this run
    perm_client: BaseClient | None = None

    iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=_trust_doc(trust_principal),
        Description="AssayOps spike #60 -- IAM eventual-consistency probe (safe to delete)",
        MaxSessionDuration=3600,
        Tags=[{"Key": _TAG_KEY, "Value": _TAG_VALUE}],
    )
    t0 = time.monotonic()
    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=_INLINE_POLICY_NAME,
            PolicyDocument=json.dumps(_GATED_ACTION_POLICY),
        )
        role_arn = f"arn:aws:iam::{account}:role/{role_name}"
        deadline = t0 + max_wait

        while time.monotonic() < deadline and any(signals[k] is None for k in _SIGNALS):
            elapsed = time.monotonic() - t0

            if signals["iam_read"] is None and _try(
                lambda: iam.get_role(RoleName=role_name), (iam.exceptions.NoSuchEntityException,)
            ):
                signals["iam_read"] = elapsed

            if signals["cc_get"] is None and _try(
                lambda: cc.get_resource(TypeName=_ROLE_TYPE, Identifier=role_name),
                (cc.exceptions.ResourceNotFoundException,),
            ):
                signals["cc_get"] = elapsed

            if signals["cc_list"] is None and not skip_list and _cc_list_has(cc, role_name):
                signals["cc_list"] = elapsed

            if signals["assume"] is None:
                creds = _try_assume(sts, role_arn)
                if creds is not None:
                    signals["assume"] = elapsed
                    perm_client = session.client(
                        "s3",
                        region_name=region,
                        config=_NO_RETRY,
                        aws_access_key_id=creds["AccessKeyId"],
                        aws_secret_access_key=creds["SecretAccessKey"],
                        aws_session_token=creds["SessionToken"],
                    )

            if signals["perm"] is None and perm_client is not None and _try_perm(perm_client):
                signals["perm"] = elapsed

            if all(signals[k] is not None for k in _SIGNALS):
                break
            time.sleep(poll_interval)
        return signals
    finally:
        # Idempotent best-effort teardown -- never leak resources, even on an unexpected raise.
        try:
            iam.delete_role_policy(RoleName=role_name, PolicyName=_INLINE_POLICY_NAME)
        except iam.exceptions.NoSuchEntityException:
            pass
        try:
            iam.delete_role(RoleName=role_name)
        except iam.exceptions.NoSuchEntityException:
            pass


def _try_assume(sts: BaseClient, role_arn: str) -> dict[str, str] | None:
    try:
        creds = sts.assume_role(RoleArn=role_arn, RoleSessionName="assay-spike-60")["Credentials"]
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"AccessDenied", "AccessDeniedException", "Throttling", "ThrottlingException"}:
            return None  # trust policy not yet propagated -> keep polling
        raise
    return {
        "AccessKeyId": creds["AccessKeyId"],
        "SecretAccessKey": creds["SecretAccessKey"],
        "SessionToken": creds["SessionToken"],
    }


def _try_perm(client: BaseClient) -> bool:
    """A policy-gated call with the assumed role's creds. False while creds/authz still propagate.

    Two eventual-consistency effects collapse here: fresh STS creds are transiently
    InvalidAccessKeyId/SignatureDoesNotMatch, and the granted policy is transiently AccessDenied.
    """
    try:
        client.list_buckets()
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
            "TokenRefreshRequired",
            "AccessDenied",
            "AccessDeniedException",
            "Throttling",
            "ThrottlingException",
        }:
            return False
        raise


def _cc_list_has(cc: BaseClient, role_name: str) -> bool:
    try:
        for page in cc.get_paginator("list_resources").paginate(TypeName=_ROLE_TYPE):
            for desc in page.get("ResourceDescriptions", []):
                if desc.get("Identifier") == role_name:
                    return True
        return False
    except ClientError:
        return False  # throttle / transient -> not yet


def cleanup_orphans(iam: BaseClient) -> int:
    """Delete any leftover probe roles (tag/prefix match) from a crashed run; return the count."""
    deleted = 0
    for page in iam.get_paginator("list_roles").paginate():
        for role in page.get("Roles", []):
            name = role["RoleName"]
            if not name.startswith(_NAME_PREFIX):
                continue
            for pol in iam.list_role_policies(RoleName=name).get("PolicyNames", []):
                iam.delete_role_policy(RoleName=name, PolicyName=pol)
            try:
                iam.delete_role(RoleName=name)
                deleted += 1
            except iam.exceptions.NoSuchEntityException:
                pass
    return deleted


def summarize(rows: list[dict[str, float | None]]) -> dict[str, dict[str, float | int | None]]:
    out: dict[str, dict[str, float | int | None]] = {}
    for sig in _SIGNALS:
        # Iterate the extracted list (not re-subscript r[sig]) so `is not None` narrows to float.
        measured = [r[sig] for r in rows]
        vals = sorted(v for v in measured if v is not None and v >= 0.0)
        out[sig] = {
            "n": len(vals),
            "bound_exceeded": sum(1 for v in measured if v is None),
            "not_measured": sum(1 for v in measured if v is not None and v < 0.0),
            "p50": round(_percentile(vals, 0.50), 3) if vals else None,
            "p95": round(_percentile(vals, 0.95), 3) if vals else None,
            "p99": round(_percentile(vals, 0.99), 3) if vals else None,
            "max": round(vals[-1], 3) if vals else None,
        }
    return out


def run(args: argparse.Namespace) -> int:
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    iam = session.client("iam", config=_NO_RETRY)  # IAM is global; region not required
    sts = session.client("sts", region_name=args.region, config=_NO_RETRY)
    cc = session.client("cloudcontrol", region_name=args.region, config=_NO_RETRY)

    ident = sts.get_caller_identity()
    account = ident["Account"]
    print(
        f"caller account={account} arn={ident['Arn']} region={args.region} profile={args.profile}",
        file=sys.stderr,
    )

    if args.cleanup_only:
        deleted = cleanup_orphans(iam)
        print(json.dumps({"cleanup_only": True, "roles_deleted": deleted}))
        return 0

    # Trust the account root: robust across IAM-user and SSO/assumed-role callers (deriving an SSO
    # role ARN for a trust policy is brittle). The caller still needs identity-based sts:AssumeRole
    # on the role, so trust-policy propagation is still what `assume` measures.
    trust_principal = args.trust_principal or f"arn:aws:iam::{account}:root"

    rows: list[dict[str, float | None]] = []
    for trial in range(1, args.trials + 1):
        signals = probe_once(
            iam,
            cc,
            sts,
            session,
            args.region,
            account,
            trust_principal,
            trial,
            args.max_wait_seconds,
            args.poll_interval,
            args.skip_list,
        )
        rows.append(signals)
        pretty = {
            k: (round(v, 3) if isinstance(v, float) and v >= 0 else v) for k, v in signals.items()
        }
        print(f"trial {trial:02d}/{args.trials}: {pretty}", file=sys.stderr)

    result = {
        "spike": "#60 IAM eventual consistency",
        "account": account,
        "region": args.region,
        "trials": args.trials,
        "max_wait_seconds": args.max_wait_seconds,
        "poll_interval_seconds": args.poll_interval,
        "trust_principal": trust_principal,
        "signal_seconds": summarize(rows),
        "raw_trials": rows,
    }
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="AssayOps spike #60 IAM eventual-consistency propagation probe."
    )
    p.add_argument(
        "--profile", default=None, help="AWS profile name (boto3 default chain if omitted)"
    )
    p.add_argument("--region", default="us-east-1", help="region for STS + Cloud Control")
    p.add_argument(
        "--trials", type=int, default=12, help="number of fresh-role trials (default 12)"
    )
    p.add_argument(
        "--max-wait-seconds", type=float, default=60.0, help="per-signal bound (default 60)"
    )
    p.add_argument(
        "--poll-interval", type=float, default=0.25, help="poll cadence seconds (default 0.25)"
    )
    p.add_argument("--skip-list", action="store_true", help="skip the cc_list signal")
    p.add_argument("--trust-principal", default=None, help="override the role trust principal ARN")
    p.add_argument(
        "--cleanup-only", action="store_true", help="sweep orphaned probe roles and exit"
    )
    args = p.parse_args()
    try:
        return run(args)
    except ClientError as exc:
        print(f"AWS error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
