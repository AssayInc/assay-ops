"""Fail-closed — the engine never silently produces a reward-able golden it can't stand behind.

An unknown task or a malformed builder output must *raise*, never return an empty/ambiguous golden
a downstream grader could read as "in sync" (DECISIONS.md §1 / vector #15: never silently reward).
"""

from __future__ import annotations

import pytest
from synthetic import make_task

from assayops_verifier.golden import GoldenContext, GoldenError, GoldenRegistry, UnknownTaskError
from assayops_verifier.models import GoldenResource


def test_generate_for_unregistered_task_raises_unknown_task() -> None:
    registry = GoldenRegistry()  # empty — no corpus registered
    with pytest.raises(UnknownTaskError):
        registry.generate(make_task(task_id="not-registered"), "seed")


def test_duplicate_addresses_are_rejected() -> None:
    def dup_builder(_ctx: GoldenContext) -> list[GoldenResource]:
        # Two resources share an address — the golden would be ambiguous; the engine must reject it.
        return [
            GoldenResource(address="dup", type="AWS::S3::Bucket"),
            GoldenResource(address="dup", type="AWS::S3::Bucket"),
        ]

    registry = GoldenRegistry()
    registry.register("dup-task", dup_builder)
    with pytest.raises(GoldenError):
        registry.generate(make_task(task_id="dup-task"), "seed")
