"""Fail-closed — the engine never silently produces a reward-able golden it can't stand behind.

An unknown task or a malformed builder output must *raise*, never return an empty/ambiguous golden
a downstream grader could read as "in sync" (DECISIONS.md §1 / vector #15: never silently reward).
"""

from __future__ import annotations

import pytest
from synthetic import make_task, s3_bucket_builder

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


def test_empty_golden_is_rejected() -> None:
    # An empty golden means "the correct state is no resources" -> a no-op deploy grades reward 1
    # under the closed-world check (deployed set ≡ golden set). A builder that falls through to []
    # must fail, never mint a free reward.
    def empty_builder(_ctx: GoldenContext) -> list[GoldenResource]:
        return []

    registry = GoldenRegistry()
    registry.register("empty", empty_builder)
    with pytest.raises(GoldenError):
        registry.generate(make_task(task_id="empty"), "seed")


def test_duplicate_task_registration_is_rejected() -> None:
    # Silently overwriting a registered builder lets import order / corpus duplication change the
    # golden for the same (task, seed) — fail closed instead.
    registry = GoldenRegistry()
    registry.register("dup-reg", s3_bucket_builder)
    with pytest.raises(GoldenError):
        registry.register("dup-reg", s3_bucket_builder)


def test_builder_returning_a_non_iterable_fails_closed() -> None:
    # A builder bug (returns None) must fail closed as GoldenError, not leak a raw TypeError that a
    # reward core's `except GoldenError` would miss.
    def none_builder(_ctx: GoldenContext) -> list[GoldenResource]:
        return None  # type: ignore[return-value]

    registry = GoldenRegistry()
    registry.register("none", none_builder)
    with pytest.raises(GoldenError):
        registry.generate(make_task(task_id="none"), "seed")


def test_builder_raising_an_arbitrary_exception_fails_closed_as_golden_error() -> None:
    def boom_builder(_ctx: GoldenContext) -> list[GoldenResource]:
        raise RuntimeError("boom")

    registry = GoldenRegistry()
    registry.register("boom", boom_builder)
    with pytest.raises(
        GoldenError
    ):  # RuntimeError is wrapped into the engine's single failure type
        registry.generate(make_task(task_id="boom"), "seed")
