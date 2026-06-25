"""AC1 — ``generate(task, seed)`` is byte-identical across K runs (feeds the #46 determinism check).

A nondeterministic golden would make the same correct deployment grade differently across re-grades
(DECISIONS.md 2A/7A) — the whole point of the reproducible target.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

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


def test_digest_is_stable_across_python_hash_seeds() -> None:
    # Cross-process stability canary: a single-process loop shares one PYTHONHASHSEED. Regenerate in
    # fresh interpreters varying the seed and assert one content address. (Sets — the hash-seed-
    # sensitive case — are rejected at construction, so this guards the dict/scalar happy path.)
    tests_dir = Path(__file__).resolve().parent
    pkg_src = tests_dir.parent / "src"
    contracts_src = tests_dir.parents[1] / "contracts" / "src"
    # `assayops_verifier.__init__` now re-exports grade_deployment (E2-2/#31), which pulls in the
    # diff-ir reward core — so a fresh interpreter importing the package needs diff-ir on the path.
    diff_ir_src = tests_dir.parents[1] / "diff-ir" / "src"
    script = (
        "from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder\n"
        "from assayops_verifier.golden import GoldenRegistry, golden_digest\n"
        "registry = GoldenRegistry()\n"
        "registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)\n"
        "print(golden_digest(registry.generate(make_task(), 'episode-42')))\n"
    )
    pythonpath = os.pathsep.join(
        str(path) for path in (tests_dir, pkg_src, contracts_src, diff_ir_src)
    )
    digests = set()
    for hash_seed in ("0", "1", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            env={**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": pythonpath},
            capture_output=True,
            text=True,
            check=True,
        )
        digests.add(result.stdout.strip())
    assert len(digests) == 1  # one content address regardless of the interpreter's hash seed
