"""The standard-library bridge: third-party (boto3/botocore/uvicorn) records flow through ONE JSON
pipeline with the same redaction + trajectory_id. Trust-boundary hardening: botocore/boto3 are
clamped to never below INFO — their wire-level DEBUG leaks AWS creds / SecretString (DECISIONS.md
§8; boto3 #2292)."""

import io
import logging

from helpers import parse_log_lines

from assayops_logger import REDACTED, bind_trajectory_id, clear_context, configure_logging

_AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def _configured(level: str = "info") -> io.StringIO:
    buf = io.StringIO()
    configure_logging(level=level, pretty=False, stream=buf)
    return buf


def test_foreign_stdlib_record_renders_as_json() -> None:
    buf = _configured()
    # boto3/botocore/uvicorn use stdlib logging; the record must come out as JSON via our pipeline.
    logging.getLogger("botocore").warning("api call complete")
    [line] = parse_log_lines(buf)
    assert line["event"] == "api call complete"
    assert line["level"] == "warning"
    assert line["logger"] == "botocore"
    assert isinstance(line["timestamp"], str)


def test_foreign_record_secret_in_extra_is_redacted() -> None:
    buf = _configured()
    # A foreign record carrying a secret in `extra` — ExtraAdder surfaces it, the censor masks it.
    logging.getLogger("uvicorn").info("auth attempt", extra={"secretAccessKey": _AWS_SECRET})
    out = buf.getvalue()
    assert _AWS_SECRET not in out
    assert parse_log_lines(buf)[0]["secretAccessKey"] == REDACTED


def test_foreign_record_carries_trajectory_id() -> None:
    buf = _configured()
    clear_context()
    bind_trajectory_id("traj-xyz")
    logging.getLogger("uvicorn").info("request")
    assert parse_log_lines(buf)[0]["trajectory_id"] == "traj-xyz"


def test_botocore_clamped_to_info_even_when_root_is_debug() -> None:
    _configured(level="debug")
    # Never DEBUG: the clamp keeps botocore at the INFO floor regardless of the configured level.
    assert logging.getLogger("botocore").level == logging.INFO
    assert logging.getLogger("boto3").level == logging.INFO
    assert logging.getLogger("urllib3").level == logging.INFO
    assert logging.getLogger("s3transfer").level == logging.INFO


def test_botocore_debug_is_dropped_but_info_passes() -> None:
    buf = _configured(level="debug")
    botocore = logging.getLogger("botocore")
    botocore.debug("wire-level dump with AKIA-style secrets")  # clamped away — never emitted
    botocore.info("retrying request")
    events = [line["event"] for line in parse_log_lines(buf)]
    assert events == ["retrying request"]


def test_clamp_follows_a_higher_configured_level() -> None:
    buf = _configured(level="warning")
    # floor = max(WARNING, INFO) = WARNING — botocore INFO is dropped, WARNING passes.
    assert logging.getLogger("botocore").level == logging.WARNING
    logging.getLogger("botocore").info("routine")
    logging.getLogger("botocore").warning("throttled")
    assert [line["event"] for line in parse_log_lines(buf)] == ["throttled"]


def test_post_config_setlevel_debug_cannot_push_botocore_secrets() -> None:
    # The one-shot setLevel clamp is bypassable by a later setLevel(DEBUG); the handler floor-filter
    # drops botocore-family records below INFO regardless, so wire-level DEBUG can't reach stdout.
    buf = _configured(level="debug")
    logging.getLogger("botocore").setLevel(logging.DEBUG)  # try to re-enable wire dumps
    logging.getLogger("botocore").debug("wire dump with AKIA secret")
    logging.getLogger("botocore.endpoint").debug("child wire dump")  # child propagates too
    logging.getLogger("botocore").info("kept")
    assert [line["event"] for line in parse_log_lines(buf)] == ["kept"]
