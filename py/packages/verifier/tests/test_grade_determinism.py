"""#31 (E2-2, AC2 / #46) — generate→bridge→grade is deterministic: same input ×K → identical reward.

A nondeterministic verifier path would grade the same correct deployment differently across
re-grades (DECISIONS.md 2A/7A) — poisoning training. The golden regeneration (#75) is byte-identical
×K and the reward core (#34) is order-independent; this asserts the COMPOSITION (grade_deployment)
inherits both: one reward AND one (canonical) diff report, in-process and across interpreter hash
seeds. The LIVE-cloud K-run reproduce (transients / eventual consistency) is the read-harness's job
(#141/#46), not this path.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from assayops_contracts.jcs import canonicalize
from synthetic import SYNTHETIC_TASK_ID, deployed_from_golden, make_task, s3_bucket_builder

from assayops_verifier import GoldenRegistry, grade_deployment


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry


def test_grade_deployment_reproduces_identically_across_k_runs() -> None:
    registry = _registry()
    task = make_task(seed="episode-42")
    deployed = deployed_from_golden(registry.generate(task, "episode-42"))

    outcomes = [grade_deployment(registry, task, "episode-42", deployed) for _ in range(5)]

    assert len({o.reward for o in outcomes}) == 1  # one reward across K regrades
    # One diff report across K regrades (by its canonical bytes) — a reproducible reward rests on
    # a reproducible report, the golden being regenerated inside each call.
    assert len({canonicalize(o.diff) for o in outcomes}) == 1


def test_grade_is_stable_across_python_hash_seeds() -> None:
    # Cross-process determinism canary: a single-process loop shares one PYTHONHASHSEED. Re-grade in
    # fresh interpreters varying the seed and assert one (reward, report-digest) pair — the
    # dict/scalar happy path (sets, the hash-seed-sensitive case, are rejected at construction).
    tests_dir = Path(__file__).resolve().parent
    pkg_src = tests_dir.parent / "src"
    contracts_src = tests_dir.parents[1] / "contracts" / "src"
    diff_ir_src = tests_dir.parents[1] / "diff-ir" / "src"
    script = (
        "from synthetic import SYNTHETIC_TASK_ID, deployed_from_golden, make_task, "
        "s3_bucket_builder\n"
        "from assayops_contracts.jcs import canonical_digest\n"
        "from assayops_verifier import GoldenRegistry, grade_deployment\n"
        "registry = GoldenRegistry()\n"
        "registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)\n"
        "task = make_task(seed='episode-42')\n"
        "deployed = deployed_from_golden(registry.generate(task, 'episode-42'))\n"
        "outcome = grade_deployment(registry, task, 'episode-42', deployed)\n"
        "print(outcome.reward.value, canonical_digest(outcome.diff).hex())\n"
    )
    pythonpath = os.pathsep.join(str(p) for p in (tests_dir, pkg_src, contracts_src, diff_ir_src))
    results = set()
    for hash_seed in ("0", "1", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            env={**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": pythonpath},
            capture_output=True,
            text=True,
            check=True,
        )
        results.add(result.stdout.strip())
    assert (
        len(results) == 1
    )  # one (reward, report digest) regardless of the interpreter's hash seed
