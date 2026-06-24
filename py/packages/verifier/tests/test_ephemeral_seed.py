"""'Ephemeral' — a different seed yields a different golden (fresh intent-bearing identifiers:
anti-memorization, vector #14); the same seed regenerates the same golden. The ``seed`` parameter is
separate from the task spec so the verifier can re-seed per episode without mutating the task.
"""

from __future__ import annotations

from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_verifier.golden import GoldenContext, GoldenRegistry, golden_digest


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry


def test_different_seed_yields_a_different_golden() -> None:
    registry = _registry()
    task = make_task()

    golden_a = registry.generate(task, "episode-a")
    golden_b = registry.generate(task, "episode-b")

    assert golden_a != golden_b  # the ephemeral (intent-bearing) identifiers differ
    assert golden_digest(golden_a) != golden_digest(golden_b)


def test_same_seed_regenerates_the_same_golden() -> None:
    registry = _registry()
    task = make_task()

    assert registry.generate(task, "episode-a") == registry.generate(task, "episode-a")


def test_token_encoding_is_injective() -> None:
    # Length-prefixed, so a part containing the old NUL delimiter can't collide with a different
    # (seed, *parts) split — distinct ephemeral identifiers stay distinct.
    ctx = GoldenContext(task=make_task(), seed="seed")
    assert ctx.token("foo", "bar") != ctx.token("foo\x00bar")
    seed_with_nul = GoldenContext(task=make_task(), seed="p\x00q").token()
    seed_then_part = GoldenContext(task=make_task(), seed="p").token("q")
    assert seed_with_nul != seed_then_part
