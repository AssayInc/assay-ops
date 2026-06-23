"""trajectory_id correlation via structlog.contextvars — the join key (DECISIONS.md §1/§8) binding
an episode's logs to its graded reward record. Covers the async-emit path and the spawned-coroutine
fan-out (the per-concurrency isolation gotcha from contextvars.html: bind on the emitting task; set
it inside spawned coroutines, or the join key silently drops from some lines)."""

import asyncio
import io

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
