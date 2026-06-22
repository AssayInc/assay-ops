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
  signing key, no golden target, no grade logic. It "deploys" resources to a ground-truth substrate
  (`cloud_state.CLOUD`) — a spike stand-in for real AWS resources.
- **Account B** (mocked in `tests/account_b_mock.py`): a write-isolated verifier **reads the
  ground-truth deployed state (`CLOUD`) independently, by `trajectory_id`** — never the agent's
  reported observation — grades it → `reward ∈ {0, 1}`, and a reward ledger ECDSA-P256-signs (a KMS
  analog) + WORM-writes the record, keyed by `(trajectory_id, attempt)`.
- **Join** = `trajectory_id`. The TRL trainer's `rollout_func` returns a `trajectory_id` column (not
  a reward); `reward_funcs` fetches the signed account-B record by `trajectory_id`, verifies it, and
  returns the `{0, 1}` reward — TRL optimizes **that**, never the env's `step()` reward.

## What it proves (each via a passing test against a real server + real WebSocket clients)

1. **Concurrent sessions isolated** over HTTP + `/ws` — `create_app(..., max_concurrent_envs=16)` with
   `SUPPORTS_CONCURRENT_SESSIONS=True` gives each WebSocket session its own env instance; concurrent
   episodes get distinct `trajectory_id`s and isolated state.
2. **Delayed/terminal reward shape** — the env reward stays `0.0` (including at terminal); the graded
   reward is read + signed by account-B out-of-band, after the episode, by `trajectory_id`.
3. **The TRL integration seam drives the env** — the trl-1.6.0 `rollout_func` → `trajectory_id` column
   → `reward_funcs` seam, reproduced faithfully and run against the real env over WebSocket, with the
   reward supplied out-of-band. (Binding to the real `trl.GRPOTrainer` symbol is an opt-in test that
   runs only when `trl` is installed — kept out of the default gate to avoid torch/vLLM.)
4. **Reward boundary preserved** — the A-side package declares no signing dependency and no account-B
   reference (AST import scan); account-B grades the ground-truth substrate independently and **ignores
   a fabricated observation** (the read is not tautological); fuzzed actions never yield a graded reward;
   a record tampered after signing (or by a wrong key, or malformed bytes) fails the signature; WORM.

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
(`GRPOTrainer(rollout_func=...)`, `trl.experimental.openenv`) — `trl` is **not** a runtime dependency
of this spike (the seam is reproduced and run against the real env; the real-symbol binding test runs
only when `trl` is installed, to keep torch/vLLM out of the gate).

**Deliberately out of scope (E5 / E4 / E2 follow-ups):** Dockerfile / `openenv.yaml` / HF push;
`/schema` serving the real `@assayops/contracts` artifacts; real KMS + S3 Object Lock; the
independently regenerated golden + the cross-account `boto3` read of deployed state (`cloud_state.CLOUD`
is the spike stand-in for that read); a full GPU GRPO training step (TRL's generation path hard-imports
vLLM — the reward boundary lives in the rollout→reward seam, exercised here CPU-only).
