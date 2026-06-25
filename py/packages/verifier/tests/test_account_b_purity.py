"""Account-B purity (DECISIONS.md §1/§8, T1) — ``generate`` is a pure function of (task, seed): it
has no parameter for, and so no access to, agent-reported / deployed state. The verifier regenerates
the golden **independently**; it never consumes the agent's synth/plan/state. This guards against a
refactor that threads such an input into the golden path (a trust-boundary regression, vector #15).
"""

from __future__ import annotations

import inspect

from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_verifier.golden import GoldenRegistry


def _fresh_registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry


def test_generate_consumes_only_task_and_seed() -> None:
    # No `deployed_state` / agent-channel parameter exists, so the golden cannot depend on one.
    params = list(inspect.signature(GoldenRegistry.generate).parameters)
    assert params == ["self", "task", "seed"]


def test_golden_depends_only_on_task_and_seed() -> None:
    # Two independently-constructed registries yield the identical golden: it is a function of
    # (task, seed) + the registered builder — nothing ambient / global / agent-supplied.
    task = make_task()
    assert _fresh_registry().generate(task, "s") == _fresh_registry().generate(task, "s")
