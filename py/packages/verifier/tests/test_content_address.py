"""Content-addressing (AC4) — ``golden_digest`` is a stable lowercase 64-hex SHA-256, reproducible
from (task, seed). So a grade is reproducible from the record alone: trajectory_id → task_id → the
golden regenerated from the task's seed → the same address (no golden artifact has to be stored).
"""

from __future__ import annotations

import re

from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_verifier.golden import GoldenRegistry, golden_digest

# The reward record's reportDigest shape (reward-record.schema.json): lowercase hex SHA-256.
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry


def test_golden_digest_is_lowercase_sha256_hex() -> None:
    digest = golden_digest(_registry().generate(make_task(), "seed"))
    assert _SHA256_HEX.match(digest) is not None


def test_golden_digest_reproducible_from_task_and_seed() -> None:
    first = golden_digest(_registry().generate(make_task(), "episode-7"))
    second = golden_digest(_registry().generate(make_task(), "episode-7"))
    assert first == second
