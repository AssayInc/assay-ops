# @assayops/py-env-server — OpenEnv-native Python env-server (feasibility spike)

A timeboxed **feasibility spike** (E17-S1), not the production env-server (E5). It proves that an
OpenEnv-native Python `create_app`/FastAPI environment supports AssayOps-style usage **without
violating the reward boundary**, and records a go/no-go for OpenEnv-native Python vs. a TS wire-only
server.

## The reward boundary (the non-negotiable)

The env-server runs **A-side** (agent-reachable), so it **never computes the graded reward**
(`DECISIONS.md` §8 + I5). The wiring:

- **A-side env** (`src/assayops_env_server/`): `step()`/terminal `reward` is always `0.0` (a zero
  shaping signal); no OpenEnv rubric is attached; `reset()` mints a `trajectory_id`. It holds no
  signing key, no golden target, no grade logic.
- **Account B** (mocked in `tests/account_b_mock.py`): a write-isolated verifier grades the deployed
  state → `reward ∈ {0, 1}`; a reward ledger ECDSA-P256-signs (a KMS analog) and WORM-writes the
  record, keyed by `(trajectory_id, attempt)`.
- **Join** = `trajectory_id`. The TRL trainer's `rollout_func` returns a `trajectory_id` column (not
  a reward); `reward_funcs` fetches the signed account-B record by `trajectory_id`, verifies it, and
  returns the `{0, 1}` reward — TRL optimizes **that**, never the env's `step()` reward.

## What it proves (each via a passing test against a real server + real WebSocket clients)

1. **Concurrent sessions isolated** over HTTP + `/ws` — `create_app(..., max_concurrent_envs=8)` with
   `SUPPORTS_CONCURRENT_SESSIONS=True` gives each WebSocket session its own env instance; concurrent
   episodes get distinct `trajectory_id`s and isolated state.
2. **Delayed/terminal reward shape** — the env reward stays `0.0` (including at terminal); the graded
   reward is fetched from account-B out-of-band, after the episode, by `trajectory_id`.
3. **TRL drives the env** via the OpenEnv integration path — the trl-1.6.0 `rollout_func` →
   `trajectory_id` column → `reward_funcs` seam, with the reward supplied out-of-band.
4. **Reward boundary preserved** — the A-side package declares no signing dependency and no account-B
   reference (AST import scan); fuzzed actions never yield a graded reward; a forged record fails
   account-B's signature; the ledger is WORM.

## Run

```sh
# Tests (boots a real uvicorn server on an ephemeral port; drives it over WebSocket)
uv run --frozen pytest -q          # from this directory

# The server, standalone (web UI stays off unless ENABLE_WEB_INTERFACE is set)
uv run uvicorn assayops_env_server.app:app --port 8000
curl localhost:8000/health
```

## Pins & scope

Pinned to `openenv[core]==0.3.1` (canonical PyPI dist `openenv` + the `core` extra; clears the TRL
doc floor `>=0.3.1`, satisfies `DECISIONS.md` I8). The TRL integration targets `trl==1.6.0`
(`GRPOTrainer(rollout_func=...)`, `trl.experimental.openenv`).

**Deliberately out of scope (E5 / E4 / E2 follow-ups):** Dockerfile / `openenv.yaml` / HF push;
`/schema` serving the real `@assayops/contracts` artifacts; real KMS + S3 Object Lock; an
independently regenerated golden + cross-account `boto3` state read; a full GPU GRPO training step
(TRL's generation path hard-imports vLLM — the reward boundary lives in the rollout→reward seam,
which is exercised here CPU-only).
