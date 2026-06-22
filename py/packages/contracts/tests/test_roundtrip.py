"""Cross-language reward-record round-trip (E1-2 / #27).

Proves the generated TS type (quicktype) and the generated Pydantic v2 model
(datamodel-code-generator) agree on the reward-record contract: a synthetic instance serialized
by TS parses faithfully via the Pydantic model and re-serializes deep-equal. This is *semantic*
equality; canonical JCS byte-parity is #28's scope. The instance is synthetic and never touches
the locked golden vectors (#28).

The round-trip is inherently cross-language, so it runs in the Python (uv) lane (the only CI lane
with both runtimes), shelling out to a tsc-checked TS emitter for the serialize step.
"""

import json
import shutil
import subprocess
from pathlib import Path

from assayops_contracts import RewardRecord

REPO_ROOT = Path(__file__).resolve().parents[4]
EMITTER = REPO_ROOT / "ts" / "packages" / "contracts" / "scripts" / "emit-reward-record.ts"


def test_reward_record_roundtrips_ts_to_python() -> None:
    bun = shutil.which("bun")
    assert bun is not None, "bun must be on PATH (monorepo setup is `bun install && uv sync`)"

    # Serialize (TS): the emitter constructs a synthetic record as the generated `RewardRecord` type
    # (tsc proves the type accepts it) and writes JSON.stringify to stdout.
    emitted = subprocess.run(
        [bun, "run", str(EMITTER)],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    ).stdout
    original = json.loads(emitted)

    # Parse (Pydantic) then serialize (Py): the generated model round-trips the TS-emitted JSON...
    model = RewardRecord.model_validate_json(emitted)
    roundtripped = json.loads(model.model_dump_json())

    # ...deep-equal to the original (no field lost, renamed, or retyped across the two generators).
    assert roundtripped == original
