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
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml
from assayops_adapter_terraform import BridgeRegistry
from assayops_contracts import TaskSpec
from assayops_verifier import GoldenError, GoldenRegistry, assert_golden_readable
from assayops_verifier.read_scope import ReadScope

# The compose contract this loader admits (and the readers consume): the agent's 'default'
# workbench service plus the sample's OWN LocalStack service publishing the gateway port.
LOCALSTACK_SERVICE = "localstack"
LOCALSTACK_GATEWAY_PORT = 4566

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
    _validate_compose(compose_file)
    tasks = _admitted_tasks(corpus_dir / _TASKS_DIR, registry, scope)
    return Corpus(
        registry=registry,
        scope=scope,
        bridge_registry=bridge_registry,
        compose_file=compose_file,
        tasks=tasks,
    )


def _require_out_of_repo(corpus_dir: Path) -> None:
    """The I11 residency rule, fail closed: a corpus inside ANY git repo is refused.

    Real tasks/goldens live in the private store; committing them to a code repo would be
    held-out/corpus leakage (DECISIONS.md I11 + the held-out-data residency rule). The guard asks
    whether the corpus itself sits inside a git repo -- ``corpus_dir`` or any ancestor holds a
    ``.git`` marker (a dir in a clone, a file in a worktree). That question is answered from the
    corpus's OWN location, so it holds regardless of where this harness is checked out (an
    installed / site-packages harness has no ``.git`` ancestor -- keying off ``__file__`` would
    fail OPEN there) and it refuses a corpus in a FOREIGN repo too (I11 = never ANY code repo, not
    just this one). ``allow_in_repo_for_tests`` exists ONLY for the committed synthetic fixture in
    this package's own tests.
    """
    for candidate in (corpus_dir, *corpus_dir.parents):
        if (candidate / ".git").exists():
            raise CorpusError(
                f"corpus directory {str(corpus_dir)!r} is inside the git repo "
                f"{str(candidate)!r} -- tasks/goldens live in the private store, never a code "
                "repo (DECISIONS.md I11)"
            )


def _validate_compose(compose_file: Path) -> None:
    """Structural admission for the per-sample sandbox definition -- fail fast at load time.

    A misauthored compose would otherwise surface only mid-eval (sandbox startup, or the readers'
    endpoint-discovery ValueError) after paying a full model rollout. The contract: a ``default``
    service (the agent's workbench -- Inspect's docker sandbox requires one when several services
    are defined) and a ``localstack`` service publishing container port 4566 (what
    ``localstack_endpoint`` discovers the sample's gateway from).
    """
    try:
        parsed: object = yaml.safe_load(compose_file.read_text())
    except (yaml.YAMLError, UnicodeDecodeError) as error:
        raise CorpusError(f"unparseable {_COMPOSE_FILE}: {error}") from error
    services: object = parsed.get("services") if isinstance(parsed, dict) else None
    if not isinstance(services, dict):
        raise CorpusError(f"{_COMPOSE_FILE} must define a 'services' mapping: {compose_file}")
    if "default" not in services:
        raise CorpusError(
            f"{_COMPOSE_FILE} must define a 'default' service (the agent's workbench): "
            f"{compose_file}"
        )
    localstack: object = services.get(LOCALSTACK_SERVICE)
    if not isinstance(localstack, dict):
        raise CorpusError(
            f"{_COMPOSE_FILE} must define a {LOCALSTACK_SERVICE!r} service (the sample's own "
            f"grading substrate): {compose_file}"
        )
    if not _publishes_gateway_port(localstack.get("ports")):
        raise CorpusError(
            f"the {LOCALSTACK_SERVICE!r} service in {_COMPOSE_FILE} must publish container port "
            f'{LOCALSTACK_GATEWAY_PORT} (ports: ["{LOCALSTACK_GATEWAY_PORT}"]) -- endpoint '
            f"discovery fails closed without it: {compose_file}"
        )


def _publishes_gateway_port(ports: object) -> bool:
    """Whether a compose ``ports`` value publishes the LocalStack gateway container port.

    Accepts both compose syntaxes: short strings/ints (``4566``, ``"host:4566"``,
    ``"ip:host:4566"``, optional ``/protocol`` suffix -- the container port is the last segment)
    and the long mapping form (``target: 4566``).
    """
    if not isinstance(ports, list):
        return False
    for entry in ports:
        if isinstance(entry, dict):
            if entry.get("target") == LOCALSTACK_GATEWAY_PORT:
                return True
        elif isinstance(entry, (str, int)):
            container = str(entry).split("/", 1)[0].rsplit(":", 1)[-1]
            if container == str(LOCALSTACK_GATEWAY_PORT):
                return True
    return False


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
        # model_validate_json parses + validates in one pass (pydantic-v2's JSON path) and wraps a
        # malformed-JSON parse error as a ValidationError. `except ValueError` covers that
        # (ValidationError subclasses ValueError) AND a non-UTF-8 read_text (UnicodeDecodeError,
        # also a ValueError) -- so any unreadable/invalid spec fails closed as a CorpusError.
        spec = TaskSpec.model_validate_json(spec_path.read_text())
    except ValueError as error:
        raise CorpusError(f"invalid {_TASK_SPEC_FILE} in {task_dir.name!r}: {error}") from error
    if spec.task_id != task_dir.name:
        raise CorpusError(
            f"task_id {spec.task_id!r} does not match its directory name {task_dir.name!r}"
        )
    return spec


def _sandbox_files(files_dir: Path) -> Mapping[str, Path]:
    if not files_dir.is_dir():
        return {}
    files: dict[str, Path] = {}
    for path in sorted(files_dir.rglob("*")):
        if path.is_symlink():
            # A symlink would silently materialize content from OUTSIDE the corpus into the
            # sandbox (or dangle at copy time) -- refuse at admission, never follow.
            raise CorpusError(
                f"corpus asset {str(path)!r} is a symlink -- sandbox files must be regular "
                "files inside the corpus, never links"
            )
        if not path.is_file():
            continue
        key = str(path.relative_to(files_dir).as_posix())
        if ":" in key:
            # ':' is Docker's source:destination separator -- an ambiguous key to the sandbox
            # copy layer.
            raise CorpusError(
                f"corpus asset key {key!r} contains ':' -- ambiguous to the sandbox file copy; "
                "rename the file"
            )
        files[key] = path
    return files
