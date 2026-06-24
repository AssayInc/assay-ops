"""The single shared configuration module — the one place env-server, verifier, and reward ledger
all configure logging from, so the processor chain (and its redaction point) is defined once.

Design (grounded in the official structlog docs, 26.1.0):

- **Path (a), the unified stdlib bridge** (standard-library.html): our own logs and third-party
  (boto3/botocore/uvicorn) records render through one ``ProcessorFormatter`` pipeline. The shared
  pre-chain is referenced as both the native chain prefix and the ``foreign_pre_chain``, so the
  single ``redact_secrets`` censor covers both. Path (b) — our logs on the fast native
  ``BytesLoggerFactory`` path — is the deferred optimization for the env-server hot path (the
  verifier is I/O-bound on cloud reads, not log-CPU-bound).
- **Native fast filtering** (performance.html): ``make_filtering_bound_logger`` (``return None``
  below the level) + ``cache_logger_on_first_use``. Cached loggers are not pickleable, so each
  process configures its own (never pass a logger across processes).
- **Dev/prod renderer gate** (logging-best-practices.html): ``sys.stderr.isatty()`` →
  ``ConsoleRenderer`` (dev) else structured tracebacks + ``JSONRenderer`` to unbuffered stdout.
- **Trust-boundary hardening** (DECISIONS.md §8): botocore/boto3 wire-level DEBUG leaks AWS creds /
  Secrets Manager SecretString that no pattern catches (boto3 #2292), so the noisy AWS loggers are
  clamped to never below INFO AND a handler filter floors them (surviving a later ``setLevel``;
  ``set_stream_logger``'s sibling handler still bypasses it — the primary rule stays don't enable
  boto3/botocore DEBUG). Both the JSON and dev exception renderers pin no frame locals, so a
  KMS-signing crash can't dump key material from a traceback (``show_locals`` defaults to True).
"""

import logging
import os
import sys
from typing import TextIO

import structlog
from structlog.typing import FilteringBoundLogger, Processor

from assayops_logger.redaction import redact_secrets

# The standard stdlib level names structlog filters on (make_filtering_bound_logger uses the stdlib
# names + order). Python-native, unlike pino's fatal/warn/trace — the redaction contract
# (SECRET_KEYS), not the level names, is what is kept in lockstep with the TS lane.
LOG_LEVELS: tuple[str, ...] = ("critical", "error", "warning", "info", "debug")

_LEVEL_BY_NAME: dict[str, int] = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "warn": logging.WARNING,  # alias (pino uses `warn`) so a shared LOG_LEVEL works across lanes
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

# boto3/botocore wire-level DEBUG logs contain secrets no redaction pattern can comprehensively
# catch; never let these emit below INFO (DECISIONS.md §8). urllib3/s3transfer are the same family.
_NOISY_AWS_LOGGERS: tuple[str, ...] = ("botocore", "boto3", "urllib3", "s3transfer")


class _NoisyAwsFloorFilter(logging.Filter):
    """Drop noisy-AWS records below INFO AT our handler — so a later ``getLogger("botocore")
    .setLevel(DEBUG)`` can't push wire-level secrets through this pipeline (the one-shot setLevel
    clamp alone is bypassable). A sibling handler added by ``boto3.set_stream_logger`` bypasses this
    entirely; the primary rule stays: don't enable boto3/botocore DEBUG (DECISIONS.md §8)."""

    def filter(self, record: logging.LogRecord) -> bool:
        for name in _NOISY_AWS_LOGGERS:
            if record.name == name or record.name.startswith(f"{name}."):
                return record.levelno >= logging.INFO
        return True


def resolve_log_level(value: str | None) -> int:
    """Resolve a level name to its numeric stdlib level (case-insensitive, ``warn`` aliased).
    Unknown or missing → INFO, mirroring the TS ``resolveLogLevel``."""
    if value is None:
        return logging.INFO
    return _LEVEL_BY_NAME.get(value.strip().lower(), logging.INFO)


def _coerce_level(level: int | str | None) -> int:
    if level is None:
        return resolve_log_level(os.environ.get("LOG_LEVEL"))
    if isinstance(level, int):
        return level
    return resolve_log_level(level)


def _resolve_pretty(pretty: bool | None) -> bool:
    if pretty is not None:
        return pretty
    env = os.environ.get("LOG_PRETTY")
    if env is not None:
        return env.strip().lower() == "true"
    return sys.stderr.isatty()


def _shared_pre_chain(*, foreign: bool) -> list[Processor]:
    """The output-agnostic processors shared by the native chain and the foreign (stdlib)
    ``foreign_pre_chain``. Ends with the single ``redact_secrets`` censor (before any renderer), so
    it covers both paths."""
    chain: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # trajectory_id correlation; must be first
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if foreign:
        # Surface `extra={...}` from boto3/uvicorn LogRecords so they render AND get redacted.
        chain.append(structlog.stdlib.ExtraAdder())
    chain.append(structlog.processors.StackInfoRenderer())
    chain.append(redact_secrets)
    return chain


def _renderer_tail(*, pretty: bool) -> list[Processor]:
    if pretty:
        # ConsoleRenderer renders exceptions itself; pin a plain (no-locals) traceback so the
        # dev/pretty path can't dump KMS key material from frame locals either — Rich's default
        # formatter shows locals and Rich is an installed transitive dep. Secure-by-default.
        return [structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback)]
    return [
        # Structured, JSON-serializable tracebacks WITHOUT frame locals (KMS-signing hardening; the
        # transformer's show_locals defaults to True, so it is pinned False here).
        structlog.processors.ExceptionRenderer(
            structlog.tracebacks.ExceptionDictTransformer(show_locals=False)
        ),
        structlog.processors.JSONRenderer(),
    ]


def _clamp_noisy_aws_loggers(level: int) -> None:
    floor = max(level, logging.INFO)
    for name in _NOISY_AWS_LOGGERS:
        logging.getLogger(name).setLevel(floor)


def configure_logging(
    *,
    level: int | str | None = None,
    pretty: bool | None = None,
    stream: TextIO | None = None,
) -> None:
    """Configure structlog + the stdlib root logger for this process. Call once at startup.

    ``level``: an int (e.g. ``logging.INFO``) or a name; ``None`` → ``LOG_LEVEL`` env → INFO.
    ``pretty``: ``None`` → ``LOG_PRETTY`` env → ``sys.stderr.isatty()``.
    ``stream``: output stream; ``None`` → ``sys.stdout`` (12-factor; flushed per record).
    """
    numeric_level = _coerce_level(level)
    pretty_enabled = _resolve_pretty(pretty)
    out: TextIO = stream if stream is not None else sys.stdout

    structlog.configure(
        processors=[
            *_shared_pre_chain(foreign=False),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_shared_pre_chain(foreign=True),
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *_renderer_tail(pretty=pretty_enabled),
        ],
    )
    handler = logging.StreamHandler(out)
    handler.setFormatter(formatter)
    handler.addFilter(_NoisyAwsFloorFilter())
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(numeric_level)
    _clamp_noisy_aws_loggers(numeric_level)


def get_logger(name: str | None = None, /, **initial_values: object) -> FilteringBoundLogger:
    """Return a bound logger (optionally named + pre-bound). Use ``.bind(**values)`` for a child."""
    logger: FilteringBoundLogger = structlog.get_logger(name, **initial_values)
    return logger
