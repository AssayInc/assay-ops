"""Shared test fixtures for the evals package (DRY: the corpus path + tmp-copy helper)."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "synthetic_corpus"
FIXTURE_TASK_ID = "synthetic-corpus-task"


@pytest.fixture
def tmp_corpus(tmp_path: Path) -> Callable[[], Path]:
    """Copy the committed synthetic corpus to an OUT-OF-REPO tmp dir (passes the I11 guard).

    Returns a factory so a test can mutate the copy before loading it.
    """

    def _make() -> Path:
        corpus_dir = tmp_path / "corpus"
        shutil.copytree(FIXTURE_CORPUS, corpus_dir)
        return corpus_dir

    return _make
