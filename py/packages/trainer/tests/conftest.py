"""Shared test helpers for the trainer package."""

from __future__ import annotations

from typing import Any


def as_dict(obj: object) -> dict[str, Any]:
    """Narrow an emitted JSON value to a dict for ergonomic deep assertions in tests.

    The library types open JSON as ``dict[str, object]`` (never ``Any``); tests reach several
    levels in, so narrow once here (``Any`` is fine in the test lane).
    """
    assert isinstance(obj, dict)
    return obj
