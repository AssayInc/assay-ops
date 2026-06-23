"""``trajectory_id`` correlation via ``structlog.contextvars``. ``trajectory_id`` is the join key
(DECISIONS.md §1/§8) binding an episode's logs to its graded, KMS-signed reward record.
``merge_contextvars`` (first in the shared chain) merges the context-local context into every line.

Per-concurrency isolation (contextvars.html): context variables are isolated per concurrency
mechanism, and each asyncio task gets its own copy of the context. So bind ``trajectory_id`` on the
SAME async task that emits the logs, and set it INSIDE spawned coroutines when fanning out —
otherwise the join key silently drops from some lines.
"""

import structlog

# The single context key correlating an episode's logs to its reward record.
TRAJECTORY_ID_KEY = "trajectory_id"


def bind_trajectory_id(trajectory_id: str) -> None:
    """Bind ``trajectory_id`` into the context-local context so it appears on every subsequent log
    line of the current execution context (thread or asyncio task)."""
    structlog.contextvars.bind_contextvars(**{TRAJECTORY_ID_KEY: trajectory_id})


def clear_context() -> None:
    """Clear the context-local context — call at episode start before binding a new id."""
    structlog.contextvars.clear_contextvars()
