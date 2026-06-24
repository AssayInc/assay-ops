"""Load-bearing security: prove that secrets (AWS keys, KMS material, auth headers) NEVER reach
stdout through the full rendering pipeline — including child-logger bindings and nested structures —
and that the exception path preserves the traceback (Errors are not flattened) while NOT dumping
frame locals (show_locals=False — the KMS hardening). These run the real pipeline end to end."""

import io

from helpers import parse_log_lines

from assayops_logger import REDACTED, configure_logging, get_logger

# Distinctive sentinel secret values — assert these literal strings never appear in rendered output.
_AWS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
_AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
_KMS_PRIVATE = "PRIVATEKEYMATERIAL-d3adb33f-do-not-leak"
_BEARER = "Bearer sk-supersecrettoken-do-not-leak"
_API_KEY = "x-api-key-supersecret-do-not-leak"


def _configured() -> io.StringIO:
    buf = io.StringIO()
    configure_logging(level="info", pretty=False, stream=buf)
    return buf


def test_secrets_in_call_kwargs_never_reach_stdout() -> None:
    buf = _configured()
    get_logger("verifier").info(
        "signing",
        accessKeyId=_AWS_KEY_ID,
        secretAccessKey=_AWS_SECRET,
        privateKey=_KMS_PRIVATE,
        region="us-east-1",
    )
    out = buf.getvalue()
    for secret in (_AWS_KEY_ID, _AWS_SECRET, _KMS_PRIVATE):
        assert secret not in out, secret
    assert out.count(REDACTED) == 3
    line = parse_log_lines(buf)[0]
    assert line["event"] == "signing"
    assert line["region"] == "us-east-1"  # non-secret survives


def test_secrets_in_child_bindings_never_reach_stdout() -> None:
    buf = _configured()
    # A child logger carrying a secret in its bound context (the exact PR #110 leak: bindings).
    child = get_logger("ledger").bind(secretAccessKey=_AWS_SECRET, trajectory="t-1")
    child.info("worm-put")
    out = buf.getvalue()
    assert _AWS_SECRET not in out
    line = parse_log_lines(buf)[0]
    assert line["secretAccessKey"] == REDACTED
    assert line["trajectory"] == "t-1"


def test_nested_credentials_block_never_reaches_stdout() -> None:
    buf = _configured()
    get_logger("verifier").info(
        "assume-role",
        credentials={"accessKeyId": _AWS_KEY_ID, "secretAccessKey": _AWS_SECRET},
    )
    out = buf.getvalue()
    assert _AWS_KEY_ID not in out
    assert _AWS_SECRET not in out


def test_auth_headers_never_reach_stdout() -> None:
    buf = _configured()
    get_logger("verifier").info(
        "request",
        headers={
            "authorization": _BEARER,
            "x-api-key": _API_KEY,
            "content-type": "application/json",
        },
    )
    out = buf.getvalue()
    assert _BEARER not in out
    assert _API_KEY not in out
    line = parse_log_lines(buf)[0]
    assert line["headers"]["content-type"] == "application/json"  # type: ignore[index]


def test_exception_is_rendered_not_dropped() -> None:
    buf = _configured()
    log = get_logger("verifier")
    try:
        raise ValueError("deploy boom")
    except ValueError:
        log.exception("episode failed")
    line = parse_log_lines(buf)[0]
    assert line["event"] == "episode failed"
    # dict_tracebacks renders a structured, non-empty exception (Errors preserved, not flattened).
    exception = line["exception"]
    assert isinstance(exception, list) and exception
    assert exception[0]["exc_type"] == "ValueError"
    assert "deploy boom" in exception[0]["exc_value"]


def test_exception_traceback_omits_frame_locals() -> None:
    # KMS-signing hardening: a secret in a crashing frame's LOCALS must not be dumped into the
    # traceback (key-based redaction can't catch a local var; show_locals=False is the control).
    buf = _configured()
    log = get_logger("ledger")

    def _sign() -> None:
        kms_private_key = _KMS_PRIVATE  # noqa: F841 — intentionally a frame local
        raise RuntimeError("kms signing failed")

    try:
        _sign()
    except RuntimeError:
        log.exception("sign path crashed")

    out = buf.getvalue()
    assert _KMS_PRIVATE not in out  # frame locals are NOT in the traceback
    line = parse_log_lines(buf)[0]
    assert line["exception"][0]["exc_type"] == "RuntimeError"  # type: ignore[index]
    # No frame carries a `locals` mapping when show_locals=False.
    for frame in line["exception"][0]["frames"]:  # type: ignore[index]
        assert "locals" not in frame or frame["locals"] is None


def test_capitalized_aws_headers_never_reach_stdout() -> None:
    # botocore signs requests with capitalized Authorization + X-Amz-Security-Token (the STS session
    # token) — the verifier's primary AWS read path. Case-insensitive redaction must catch them.
    buf = _configured()
    get_logger("verifier").info(
        "signed-request",
        headers={"Authorization": _BEARER, "X-Amz-Security-Token": _AWS_SECRET},
    )
    out = buf.getvalue()
    assert _BEARER not in out
    assert _AWS_SECRET not in out


def test_secret_inside_tuple_never_reaches_stdout() -> None:
    buf = _configured()
    get_logger("verifier").info("assume-role-chain", chain=({"secretAccessKey": _AWS_SECRET},))
    assert _AWS_SECRET not in buf.getvalue()


def test_pretty_path_also_omits_frame_locals() -> None:
    # The dev/pretty ConsoleRenderer must NOT dump frame locals either (rich is installed, whose
    # traceback formatter defaults to show_locals=True) — the KMS hardening is secure-by-default.
    buf = io.StringIO()
    configure_logging(level="info", pretty=True, stream=buf)
    log = get_logger("ledger")

    def _sign() -> None:
        kms_private_key = _KMS_PRIVATE  # noqa: F841 — intentionally a frame local
        raise RuntimeError("kms signing failed")

    try:
        _sign()
    except RuntimeError:
        log.exception("sign path crashed")

    assert _KMS_PRIVATE not in buf.getvalue()
