"""AC1 — ``generate(task, seed)`` is byte-identical across K runs (feeds the #46 determinism check).

A nondeterministic golden would make the same correct deployment grade differently across re-grades
(DECISIONS.md 2A/7A) — the whole point of the reproducible target.
"""

from __future__ import annotations

from assayops_contracts.jcs import canonicalize
from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_verifier.golden import GoldenRegistry, golden_digest


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry


def test_generate_is_byte_identical_across_k_runs() -> None:
    registry = _registry()
    task = make_task(seed="episode-42")

    goldens = [registry.generate(task, "episode-42") for _ in range(5)]

    canonical_bytes = {canonicalize(golden) for golden in goldens}
    assert (
        len(canonical_bytes) == 1
    )  # one set of canonical bytes ⇒ byte-identical golden across K runs

    digests = {golden_digest(golden) for golden in goldens}
    assert len(digests) == 1  # one content address across K runs
