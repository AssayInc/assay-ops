"""#176 leg 3: the private-corpus loader -- fail-closed admission + I11 residency.

``load_corpus`` is the task-ADMISSION gate: every task spec is validated, its golden must
regenerate (the #75 engine), and the golden must be readable within the corpus's read scope (the
#141 authoring-time per-property gate) -- a task that cannot legitimately score reward 1 never
enters the dataset. The loader also enforces the I11 residency rule fail-closed: a corpus inside
this code repo is refused (real tasks/goldens live in the private store, never committed); the
committed synthetic fixture loads only under the loudly-named test flag.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import FIXTURE_CORPUS
from conftest import FIXTURE_TASK_ID as TASK_ID

from assayops_evals.corpus import Corpus, CorpusError, load_corpus


def _tmp_corpus(tmp_path: Path) -> Path:
    corpus_dir = tmp_path / "corpus"
    shutil.copytree(FIXTURE_CORPUS, corpus_dir)
    return corpus_dir


def test_loads_a_valid_corpus(tmp_path: Path) -> None:
    corpus = load_corpus(_tmp_corpus(tmp_path))

    assert isinstance(corpus, Corpus)
    assert [task.spec.task_id for task in corpus.tasks] == [TASK_ID]
    task = corpus.tasks[0]
    assert task.spec.seed == "seed-corpus-001"
    assert task.setup_script is not None and task.setup_script.name == "setup.sh"
    assert "main.tf" in task.files
    assert corpus.compose_file.name == "compose.yaml"
    assert corpus.scope.allowed_regions == ("us-east-1",)
    assert corpus.bridge_registry is None
    # The registry is live: the admitted task's golden regenerates deterministically.
    golden = corpus.registry.generate(task.spec, task.spec.seed)
    assert golden.resources[0].type == "AWS::S3::Bucket"


def test_a_corpus_inside_the_code_repo_fails_closed() -> None:
    # I11: tasks/goldens never live in a code repo. The committed synthetic fixture is inside this
    # repo, so loading it WITHOUT the test flag must be refused.
    with pytest.raises(CorpusError, match="I11"):
        load_corpus(FIXTURE_CORPUS)


def test_the_committed_synthetic_fixture_loads_with_the_test_flag() -> None:
    corpus = load_corpus(FIXTURE_CORPUS, allow_in_repo_for_tests=True)

    assert [task.spec.task_id for task in corpus.tasks] == [TASK_ID]


def test_a_corpus_inside_a_foreign_git_repo_fails_closed(tmp_path: Path) -> None:
    # The residency guard keys off the CORPUS's own location, not the harness's -- so a corpus in
    # ANY git repo is refused (I11 = never a code repo), and it does not fail OPEN when the harness
    # itself has no .git ancestor (installed/site-packages). Here: a tmp corpus placed under a dir
    # made into a git repo (a foreign repo, not this harness's) must be refused.
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S607
    corpus_dir = _tmp_corpus(tmp_path)  # tmp_path/corpus, under tmp_path/.git

    with pytest.raises(CorpusError, match="git repo"):
        load_corpus(corpus_dir)


def test_a_corpus_module_that_raises_on_import_fails_closed(tmp_path: Path) -> None:
    # A corpus.py that crashes at import time is a corpus-contract violation -> fail closed with
    # the cause chained, never a raw traceback mid-eval.
    corpus_dir = _tmp_corpus(tmp_path)
    (corpus_dir / "corpus.py").write_text('raise RuntimeError("boom")\n')

    with pytest.raises(CorpusError, match="failed to load"):
        load_corpus(corpus_dir)


def test_a_valid_bridge_registry_propagates(tmp_path: Path) -> None:
    corpus_dir = _tmp_corpus(tmp_path)
    module = corpus_dir / "corpus.py"
    module.write_text(
        module.read_text()
        + "\nfrom assayops_adapter_terraform import BridgeRegistry\n"
        + "BRIDGE_REGISTRY = BridgeRegistry()\n"
    )

    from assayops_adapter_terraform import BridgeRegistry

    corpus = load_corpus(corpus_dir)

    assert isinstance(corpus.bridge_registry, BridgeRegistry)


def test_a_non_bridge_registry_bridge_fails_closed(tmp_path: Path) -> None:
    corpus_dir = _tmp_corpus(tmp_path)
    module = corpus_dir / "corpus.py"
    module.write_text(module.read_text() + "\nBRIDGE_REGISTRY = 42\n")

    with pytest.raises(CorpusError, match="BRIDGE_REGISTRY"):
        load_corpus(corpus_dir)


def test_a_missing_corpus_dir_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="does not exist"):
        load_corpus(tmp_path / "absent")


def test_a_missing_corpus_module_fails_closed(tmp_path: Path) -> None:
    corpus_dir = _tmp_corpus(tmp_path)
    (corpus_dir / "corpus.py").unlink()

    with pytest.raises(CorpusError, match="corpus.py"):
        load_corpus(corpus_dir)


def test_a_corpus_module_without_registry_fails_closed(tmp_path: Path) -> None:
    corpus_dir = _tmp_corpus(tmp_path)
    module = corpus_dir / "corpus.py"
    module.write_text(module.read_text().replace("REGISTRY", "OTHER_REGISTRY"))

    with pytest.raises(CorpusError, match="REGISTRY"):
        load_corpus(corpus_dir)


def test_a_malformed_task_spec_fails_closed(tmp_path: Path) -> None:
    corpus_dir = _tmp_corpus(tmp_path)
    task_json = corpus_dir / "tasks" / TASK_ID / "task.json"
    task_json.write_text(json.dumps({"task_id": TASK_ID}))

    with pytest.raises(CorpusError, match="task.json"):
        load_corpus(corpus_dir)


def test_a_task_id_mismatching_its_directory_fails_closed(tmp_path: Path) -> None:
    corpus_dir = _tmp_corpus(tmp_path)
    task_json = corpus_dir / "tasks" / TASK_ID / "task.json"
    spec = json.loads(task_json.read_text())
    spec["task_id"] = "some-other-task"
    task_json.write_text(json.dumps(spec))

    with pytest.raises(CorpusError, match="directory"):
        load_corpus(corpus_dir)


def test_a_task_without_a_golden_builder_fails_closed(tmp_path: Path) -> None:
    # Admission gate: a spec whose golden cannot regenerate would only surface at grade time
    # (UnknownTaskError mid-eval); the loader refuses it up front.
    corpus_dir = _tmp_corpus(tmp_path)
    unregistered = corpus_dir / "tasks" / "unregistered-task"
    shutil.copytree(corpus_dir / "tasks" / TASK_ID, unregistered)
    task_json = unregistered / "task.json"
    spec = json.loads(task_json.read_text())
    spec["task_id"] = "unregistered-task"
    task_json.write_text(json.dumps(spec))

    with pytest.raises(CorpusError, match="unregistered-task"):
        load_corpus(corpus_dir)


def test_a_golden_asserting_an_unreadable_property_fails_closed(tmp_path: Path) -> None:
    # The #141 authoring-time per-property gate runs at admission: a golden asserting a write-only
    # property can never legitimately score reward 1, so the task is quarantined at load.
    corpus_dir = _tmp_corpus(tmp_path)
    module = corpus_dir / "corpus.py"
    module.write_text(
        module.read_text().replace(
            'TypeCoverage("AWS::S3::Bucket", RegionScope.REGIONAL, Listability.DIRECTLY_LISTABLE)',
            'TypeCoverage("AWS::S3::Bucket", RegionScope.REGIONAL,'
            ' Listability.DIRECTLY_LISTABLE, write_only_paths=frozenset({"BucketName"}))',
        )
    )

    with pytest.raises(CorpusError, match="BucketName"):
        load_corpus(corpus_dir)


def test_a_missing_compose_file_fails_closed(tmp_path: Path) -> None:
    corpus_dir = _tmp_corpus(tmp_path)
    (corpus_dir / "compose.yaml").unlink()

    with pytest.raises(CorpusError, match="compose.yaml"):
        load_corpus(corpus_dir)


def test_an_empty_task_set_fails_closed(tmp_path: Path) -> None:
    corpus_dir = _tmp_corpus(tmp_path)
    shutil.rmtree(corpus_dir / "tasks" / TASK_ID)

    with pytest.raises(CorpusError, match="no tasks"):
        load_corpus(corpus_dir)
