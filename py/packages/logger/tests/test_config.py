"""Configuration: level resolution, JSON one-event-per-line to stdout with ISO-8601 UTC
timestamps, native fast filtering, and the dev/prod renderer gate (sys.stderr.isatty)."""

import io
import json
import logging
import re

import pytest
from helpers import parse_log_lines

from assayops_logger import LOG_LEVELS, configure_logging, get_logger, resolve_log_level

_ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")


def test_log_levels_are_the_standard_stdlib_names() -> None:
    assert LOG_LEVELS == ("critical", "error", "warning", "info", "debug")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("critical", logging.CRITICAL),
        ("error", logging.ERROR),
        ("warning", logging.WARNING),
        ("warn", logging.WARNING),  # common alias (pino uses `warn`)
        ("info", logging.INFO),
        ("debug", logging.DEBUG),
        ("INFO", logging.INFO),  # case-insensitive
        ("Debug", logging.DEBUG),
    ],
)
def test_resolve_log_level_known(value: str, expected: int) -> None:
    assert resolve_log_level(value) == expected


@pytest.mark.parametrize("value", [None, "", "bogus", "trace"])
def test_resolve_log_level_unknown_defaults_to_info(value: str | None) -> None:
    # Mirrors the TS resolveLogLevel: unknown/missing -> info.
    assert resolve_log_level(value) == logging.INFO


def test_emits_one_json_event_per_line_to_the_stream() -> None:
    buf = io.StringIO()
    configure_logging(level="info", pretty=False, stream=buf)
    log = get_logger("svc")
    log.info("deployed", resource="bucket", count=2)
    log.warning("drifted")

    lines = parse_log_lines(buf)
    assert len(lines) == 2
    assert lines[0]["event"] == "deployed"
    assert lines[0]["resource"] == "bucket"
    assert lines[0]["count"] == 2
    assert lines[0]["level"] == "info"
    assert lines[1]["event"] == "drifted"
    assert lines[1]["level"] == "warning"


def test_timestamp_is_iso8601_utc() -> None:
    buf = io.StringIO()
    configure_logging(level="info", pretty=False, stream=buf)
    get_logger("svc").info("x")
    [line] = parse_log_lines(buf)
    assert isinstance(line["timestamp"], str)
    assert _ISO_UTC.match(line["timestamp"]), line["timestamp"]


def test_native_level_filtering_drops_below_threshold() -> None:
    buf = io.StringIO()
    configure_logging(level="info", pretty=False, stream=buf)
    log = get_logger("svc")
    log.debug("noisy")  # below info -> make_filtering_bound_logger returns None
    log.info("kept")
    lines = parse_log_lines(buf)
    assert [line["event"] for line in lines] == ["kept"]


def test_debug_level_lets_debug_through() -> None:
    buf = io.StringIO()
    configure_logging(level="debug", pretty=False, stream=buf)
    get_logger("svc").debug("seen")
    assert [line["event"] for line in parse_log_lines(buf)] == ["seen"]


def test_pretty_true_renders_console_not_json() -> None:
    buf = io.StringIO()
    configure_logging(level="info", pretty=True, stream=buf)
    get_logger("svc").info("hello")
    out = buf.getvalue()
    assert "hello" in out
    # ConsoleRenderer output is human-formatted, not a JSON object.
    with pytest.raises(json.JSONDecodeError):
        json.loads(out.strip())


def test_pretty_defaults_to_isatty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_PRETTY", raising=False)
    monkeypatch.setattr("sys.stderr.isatty", lambda: False)
    buf = io.StringIO()
    configure_logging(level="info", stream=buf)  # pretty unset -> follows isatty (False -> JSON)
    get_logger("svc").info("prod")
    assert parse_log_lines(buf)[0]["event"] == "prod"


def test_log_pretty_env_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_PRETTY", "true")
    monkeypatch.setattr("sys.stderr.isatty", lambda: False)
    buf = io.StringIO()
    configure_logging(level="info", stream=buf)  # pretty unset, LOG_PRETTY=true -> console
    get_logger("svc").info("hello")
    with pytest.raises(json.JSONDecodeError):
        json.loads(buf.getvalue().strip())


def test_log_level_env_used_when_level_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "warning")
    buf = io.StringIO()
    configure_logging(pretty=False, stream=buf)  # level unset -> LOG_LEVEL env
    log = get_logger("svc")
    log.info("dropped")
    log.warning("kept")
    assert [line["event"] for line in parse_log_lines(buf)] == ["kept"]
