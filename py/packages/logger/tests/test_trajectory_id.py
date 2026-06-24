"""trajectory_id correlation via structlog.contextvars — the join key (DECISIONS.md §1/§8) binding
an episode's logs to its graded reward record. Covers the async-emit path and the spawned-coroutine
fan-out (the per-concurrency isolation gotcha from contextvars.html: bind on the emitting task; set
it inside spawned coroutines, or the join key silently drops from some lines)."""

import asyncio
import io
import threading

from helpers import parse_log_lines

from assayops_logger import (
    TRAJECTORY_ID_KEY,
    bind_trajectory_id,
    clear_context,
    configure_logging,
    get_logger,
)


def _configured() -> io.StringIO:
    buf = io.StringIO()
    configure_logging(level="info", pretty=False, stream=buf)
    return buf


def test_trajectory_id_key_is_the_join_key_name() -> None:
    assert TRAJECTORY_ID_KEY == "trajectory_id"


def test_bound_trajectory_id_appears_on_every_line() -> None:
    buf = _configured()
    clear_context()
    bind_trajectory_id("traj-001")
    log = get_logger("env")
    log.info("reset")
    log.info("step")
    lines = parse_log_lines(buf)
    assert [line["trajectory_id"] for line in lines] == ["traj-001", "traj-001"]


def test_clear_context_removes_trajectory_id() -> None:
    buf = _configured()
    bind_trajectory_id("traj-001")
    clear_context()
    get_logger("env").info("after-clear")
    assert "trajectory_id" not in parse_log_lines(buf)[0]


def test_trajectory_id_on_async_emit_path() -> None:
    buf = _configured()

    async def episode() -> None:
        # Bind on the SAME async task that emits the log (the isolation rule).
        bind_trajectory_id("traj-async")
        await asyncio.sleep(0)
        get_logger("env").info("graded")

    asyncio.run(episode())
    assert parse_log_lines(buf)[0]["trajectory_id"] == "traj-async"


def test_trajectory_id_isolated_across_spawned_coroutines() -> None:
    buf = _configured()

    async def worker(tid: str) -> None:
        # Set the contextvar INSIDE the spawned coroutine; each gather task gets its own copy, so
        # binds never bleed across siblings even when interleaved.
        bind_trajectory_id(tid)
        await asyncio.sleep(0)
        get_logger("env").info("step", worker=tid)

    async def fan_out() -> None:
        clear_context()
        await asyncio.gather(worker("traj-A"), worker("traj-B"), worker("traj-C"))

    asyncio.run(fan_out())
    by_worker = {line["worker"]: line["trajectory_id"] for line in parse_log_lines(buf)}
    assert by_worker == {"traj-A": "traj-A", "traj-B": "traj-B", "traj-C": "traj-C"}


def test_spawned_coroutines_inherit_parent_binding() -> None:
    buf = _configured()

    async def child(label: str) -> None:
        await asyncio.sleep(0)
        get_logger("env").info("child", label=label)

    async def parent() -> None:
        clear_context()
        bind_trajectory_id("traj-parent")  # bound BEFORE the children are spawned
        await asyncio.gather(child("a"), child("b"))

    asyncio.run(parent())
    lines = parse_log_lines(buf)
    assert {line["label"]: line["trajectory_id"] for line in lines} == {
        "a": "traj-parent",
        "b": "traj-parent",
    }


def test_thread_does_not_inherit_parent_binding_but_can_bind_its_own() -> None:
    # The verifier grades deployed state via concurrent boto3 reads (ThreadPoolExecutor). Unlike an
    # asyncio task, a new THREAD starts with a fresh context and does NOT inherit the binding,
    # so each worker thread must re-bind trajectory_id or the join key silently drops.
    buf = _configured()
    clear_context()
    bind_trajectory_id("traj-main")

    def worker() -> None:
        get_logger("env").info("no-inherit")  # fresh context: no trajectory_id
        bind_trajectory_id("traj-worker")  # bind inside the thread → present from here
        get_logger("env").info("own")

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    get_logger("env").info("main")  # the main thread's binding is intact + isolated

    by_event = {line["event"]: line for line in parse_log_lines(buf)}
    assert "trajectory_id" not in by_event["no-inherit"]
    assert by_event["own"]["trajectory_id"] == "traj-worker"
    assert by_event["main"]["trajectory_id"] == "traj-main"
