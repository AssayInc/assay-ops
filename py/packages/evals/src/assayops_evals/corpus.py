"""The private-corpus loader -- fail-closed task admission + the I11 residency rule.

A corpus DIRECTORY is the slice's unit of task authoring (the #176 corpus leg authors into one; it
lives in the PRIVATE store -- DECISIONS.md I11: tasks/goldens are never committed to a code repo).
Its contract:

    <corpus_dir>/
      corpus.py                 # REGISTRY: GoldenRegistry (the per-task golden builders),
                                # READ_SCOPE: ReadScope (the closed-world type x Region matrix),
                                # optional BRIDGE_REGISTRY: BridgeRegistry | None
      compose.yaml              # the per-sample sandbox: the agent's 'default' workbench service
                                # + the sample's OWN 'localstack' service (per-sample isolation --
                                # the closed-world read enumerates the whole substrate)
      tasks/<task_id>/
        task.json               # the TaskSpec (task_id must equal the directory name)
        setup.sh                # optional: deploys the baseline + injects the drift
        files/**                # optional: the agent's working files (e.g. the Terraform dir)

``load_corpus`` is the ADMISSION gate (the #141 scope-3 placement: authoring-time, not the hot
grade path): each spec is validated, its golden must REGENERATE via the corpus registry (a task
that would only fail at grade time is refused up front), and the golden must be readable within
the read scope (``assert_golden_readable`` -- a golden asserting a write-only property can never
legitimately score reward 1). ``corpus.py`` is executed: corpus code is TRUSTED AUTHORING input
(ours, from the private store) -- it is the same trust as the golden builders themselves (#76),
never agent-reachable.
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from assayops_adapter_terraform import BridgeRegistry
from assayops_contracts import TaskSpec
from assayops_verifier import GoldenError, GoldenRegistry, assert_golden_readable
from assayops_verifier.read_scope import ReadScope
from pydantic import ValidationError

_CORPUS_MODULE = "corpus.py"
_COMPOSE_FILE = "compose.yaml"
_TASKS_DIR = "tasks"
_TASK_SPEC_FILE = "task.json"
_SETUP_SCRIPT = "setup.sh"
_FILES_DIR = "files"


class CorpusError(ValueError):
    """The corpus directory violates its contract -- fail closed, never admit a broken task."""


@dataclass(frozen=True)
class CorpusTask:
    """One admitted task: its validated spec + the sandbox assets its sample carries."""

    spec: TaskSpec
    directory: Path
    setup_script: Path | None
    # Sandbox-relative target path -> the source file to copy in (Sample.files values are paths).
    files: Mapping[str, Path]


@dataclass(frozen=True)
class Corpus:
    """A loaded, admission-gated corpus -- the harness's grading + dataset inputs."""

    registry: GoldenRegistry
    scope: ReadScope
    bridge_registry: BridgeRegistry | None
    compose_file: Path
    tasks: tuple[CorpusTask, ...]


def load_corpus(corpus_dir: Path, *, allow_in_repo_for_tests: bool = False) -> Corpus:
    """Load + admission-gate a private corpus directory (see the module docstring)."""
    corpus_dir = corpus_dir.resolve()
    if not corpus_dir.is_dir():
        raise CorpusError(f"corpus directory {str(corpus_dir)!r} does not exist")
    if not allow_in_repo_for_tests:
        _require_out_of_repo(corpus_dir)

    registry, scope, bridge_registry = _grading_inputs(corpus_dir / _CORPUS_MODULE)
    compose_file = corpus_dir / _COMPOSE_FILE
    if not compose_file.is_file():
        raise CorpusError(
            f"corpus has no {_COMPOSE_FILE} (the per-sample sandbox definition): {compose_file}"
        )
    tasks = _admitted_tasks(corpus_dir / _TASKS_DIR, registry, scope)
    return Corpus(
        registry=registry,
        scope=scope,
        bridge_registry=bridge_registry,
        compose_file=compose_file,
        tasks=tasks,
    )


def _require_out_of_repo(corpus_dir: Path) -> None:
    """The I11 residency rule, fail closed: a corpus inside this code repo is refused.

    Real tasks/goldens live in the private store; committing them here would be held-out/corpus
    leakage (DECISIONS.md I11 + the held-out-data residency rule). The guard finds the repo this
    harness is checked out in (the nearest ancestor with a ``.git`` -- a dir in a clone, a file in
    a worktree) and refuses a corpus under it. ``allow_in_repo_for_tests`` exists ONLY for the
    committed synthetic fixture in this package's own tests.
    """
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / ".git").exists():
            if corpus_dir == ancestor or ancestor in corpus_dir.parents:
                raise CorpusError(
                    f"corpus directory {str(corpus_dir)!r} is inside the code repo "
                    f"{str(ancestor)!r} -- tasks/goldens live in the private store, never a code "
                    "repo (DECISIONS.md I11)"
                )
            return


def _grading_inputs(module_path: Path) -> tuple[GoldenRegistry, ReadScope, BridgeRegistry | None]:
    if not module_path.is_file():
        raise CorpusError(f"corpus has no {_CORPUS_MODULE} (REGISTRY + READ_SCOPE): {module_path}")
    spec = importlib.util.spec_from_file_location("assayops_evals._private_corpus", module_path)
    if spec is None or spec.loader is None:
        raise CorpusError(f"could not import the corpus module at {module_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        # A corpus module that crashes on import is a corpus-contract violation -- fail closed
        # with the cause chained, never a raw traceback mid-eval.
        raise CorpusError(f"the corpus module at {module_path} failed to load: {error}") from error
    registry = _module_attr(module, "REGISTRY", GoldenRegistry, module_path)
    scope = _module_attr(module, "READ_SCOPE", ReadScope, module_path)
    bridge: object = getattr(module, "BRIDGE_REGISTRY", None)
    if bridge is not None and not isinstance(bridge, BridgeRegistry):
        raise CorpusError(
            f"{module_path}: BRIDGE_REGISTRY must be a BridgeRegistry or None, "
            f"got {type(bridge).__name__}"
        )
    return registry, scope, bridge


def _module_attr[T](module: object, name: str, expected: type[T], module_path: Path) -> T:
    value: object = getattr(module, name, None)
    if not isinstance(value, expected):
        raise CorpusError(
            f"{module_path}: the corpus module must define {name} as a "
            f"{expected.__name__} (got {type(value).__name__})"
        )
    return value


def _admitted_tasks(
    tasks_dir: Path, registry: GoldenRegistry, scope: ReadScope
) -> tuple[CorpusTask, ...]:
    if not tasks_dir.is_dir():
        raise CorpusError(f"corpus has no tasks/ directory: {tasks_dir}")
    task_dirs = sorted(path for path in tasks_dir.iterdir() if path.is_dir())
    if not task_dirs:
        raise CorpusError(f"corpus has no tasks under {tasks_dir}")
    return tuple(_admit_task(task_dir, registry, scope) for task_dir in task_dirs)


def _admit_task(task_dir: Path, registry: GoldenRegistry, scope: ReadScope) -> CorpusTask:
    spec = _task_spec(task_dir)
    # The admission gate: the golden must regenerate (fail closed on an unregistered task / broken
    # builder -- surfacing it here beats an UnknownTaskError mid-eval) and every asserted property
    # must be readable within the scope (#141 scope 3 -- else the task can never score a
    # legitimate reward 1).
    try:
        golden = registry.generate(spec, spec.seed)
        assert_golden_readable(golden, scope)
    except (GoldenError, ValueError) as error:
        # GoldenError covers the unregistered task / broken builder (it is not a ValueError);
        # ValueError covers the read-scope gates (unknown coverage / write-only property).
        raise CorpusError(f"task {spec.task_id!r} failed admission: {error}") from error
    setup_script = task_dir / _SETUP_SCRIPT
    return CorpusTask(
        spec=spec,
        directory=task_dir,
        setup_script=setup_script if setup_script.is_file() else None,
        files=_sandbox_files(task_dir / _FILES_DIR),
    )


def _task_spec(task_dir: Path) -> TaskSpec:
    spec_path = task_dir / _TASK_SPEC_FILE
    if not spec_path.is_file():
        raise CorpusError(f"task directory {task_dir.name!r} has no {_TASK_SPEC_FILE}")
    try:
        spec = TaskSpec.model_validate(json.loads(spec_path.read_text()))
    except (ValueError, ValidationError) as error:
        raise CorpusError(f"invalid {_TASK_SPEC_FILE} in {task_dir.name!r}: {error}") from error
    if spec.task_id != task_dir.name:
        raise CorpusError(
            f"task_id {spec.task_id!r} does not match its directory name {task_dir.name!r}"
        )
    return spec


def _sandbox_files(files_dir: Path) -> Mapping[str, Path]:
    if not files_dir.is_dir():
        return {}
    return {
        str(path.relative_to(files_dir).as_posix()): path
        for path in sorted(files_dir.rglob("*"))
        if path.is_file()
    }
