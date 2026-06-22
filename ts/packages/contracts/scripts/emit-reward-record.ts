// Round-trip harness (E1-2 / #27): construct a synthetic reward-record as the generated `RewardRecord`
// type and write it as JSON to stdout. tests/test_roundtrip.py (Python lane) parses it via the generated
// Pydantic model and re-serializes to assert semantic equality. Compiling under tsc proves the generated
// type accepts the instance; the synthetic values never touch the locked golden vectors (#28).
import type { RewardRecord } from "../src/index"

const record: RewardRecord = {
  trajectory_id: "traj-0001",
  attempt: 0,
  reward: 1,
  reportDigest: "a".repeat(64),
  graderVersion: "grader-v1",
  gradedAt: "1750000000000000000",
  nonce: "nonce-abc",
}

process.stdout.write(JSON.stringify(record))
