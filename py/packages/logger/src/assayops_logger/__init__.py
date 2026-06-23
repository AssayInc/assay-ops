"""AssayOps structured logger — the Python mirror of the TS ``@assayops/logger`` (pino).

The structured-logging emitter for the proof-critical Python core (env-server, write-isolated
verifier, reward ledger): structlog → JSON on stdout (dev pretty in a terminal), a deny-by-key
secret redaction censor, the stdlib bridge folding boto3/uvicorn into one pipeline, and
``trajectory_id`` correlation via ``contextvars``. Redaction is defense-in-depth, not the control:
the primary rule is don't log secrets (and never enable botocore/boto3 DEBUG; see DECISIONS.md §8).
"""

from assayops_logger.config import (
    LOG_LEVELS,
    configure_logging,
    get_logger,
    resolve_log_level,
)
from assayops_logger.context import TRAJECTORY_ID_KEY, bind_trajectory_id, clear_context
from assayops_logger.redaction import REDACT_KEYS, REDACTED, SECRET_KEYS, redact_secrets

__all__ = [
    "LOG_LEVELS",
    "REDACTED",
    "REDACT_KEYS",
    "SECRET_KEYS",
    "TRAJECTORY_ID_KEY",
    "bind_trajectory_id",
    "clear_context",
    "configure_logging",
    "get_logger",
    "redact_secrets",
    "resolve_log_level",
]
