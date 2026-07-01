"""#176 leg 3: the drift-slice Task builder -- corpus -> Samples -> the Inspect Task.

The dataset mapping is the trust seam the scorer relies on: each Sample's METADATA carries the
validated TaskSpec (the grading identity the scorer re-validates), and its files/setup come from
the admitted corpus task -- all harness-authored at dataset-build time, none of it agent-writable.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from conftest import FIXTURE_CORPUS, FIXTURE_TASK_ID
from inspect_ai import Task

from assayops_evals.corpus import load_corpus
from assayops_evals.scorer import TASK_SPEC_METADATA_KEY
from assayops_evals.task import drift_slice, samples_of


def test_samples_carry_the_task_spec_metadata_and_assets() -> None:
    corpus = load_corpus(FIXTURE_CORPUS, allow_in_repo_for_tests=True)

    samples = samples_of(corpus)

    assert len(samples) == 1
    sample = samples[0]
    assert sample.id == FIXTURE_TASK_ID
    assert sample.input == corpus.tasks[0].spec.description
    assert sample.metadata is not None
    spec_dump = sample.metadata[TASK_SPEC_METADATA_KEY]
    assert spec_dump["task_id"] == FIXTURE_TASK_ID
    assert spec_dump["seed"] == "seed-corpus-001"
    assert sample.files is not None
    assert Path(sample.files["main.tf"]).is_file()
    assert sample.setup is not None
    assert Path(sample.setup).name == "setup.sh"


def test_a_task_without_assets_maps_to_a_bare_sample(tmp_corpus: Callable[[], Path]) -> None:
    corpus_dir = tmp_corpus()
    (corpus_dir / "tasks" / FIXTURE_TASK_ID / "setup.sh").unlink()
    shutil.rmtree(corpus_dir / "tasks" / FIXTURE_TASK_ID / "files")

    samples = samples_of(load_corpus(corpus_dir))

    assert samples[0].files is None
    assert samples[0].setup is None


def test_drift_slice_builds_the_inspect_task(tmp_corpus: Callable[[], Path]) -> None:
    # Build against an OUT-OF-REPO copy so the production `drift_slice` entry runs with the I11
    # residency guard ACTIVE (it has no test-bypass param -- that surface is deliberately off the
    # @task CLI; see the residency-guard tests in test_corpus.py).
    corpus_dir = tmp_corpus()

    task = drift_slice(corpus_dir=str(corpus_dir), epochs=3)

    assert isinstance(task, Task)
    assert len(task.dataset) == 1
    assert task.epochs == 3
    assert task.sandbox is not None
    assert task.sandbox.type == "docker"
    assert task.sandbox.config == str(corpus_dir / "compose.yaml")
    assert task.scorer is not None
    assert task.solver is not None
