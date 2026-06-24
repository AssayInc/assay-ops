"""Unit tests for the deny-by-key secret redaction censor (the one load-bearing security item —
structlog ships no built-in redaction). The censor is a structlog processor: a
``(logger, method, event_dict)`` callable that mutates the already-copied event_dict in place
(processors.html) — NOT a recursive clone (the PR #110 mistake). It mirrors the TS ``SECRET_KEYS``
and redacts recursively (closing pino's single-level-path / arrays gap with a safe superset)."""

from structlog.typing import EventDict

from assayops_logger import REDACT_KEYS, REDACTED, SECRET_KEYS, redact_secrets

# The 13 keys the TS @assayops/logger SECRET_KEYS masks (parity asserted separately in
# test_ts_parity.py against ts/packages/logger/src/index.ts).
_TS_SECRET_KEYS = (
    "password",
    "secret",
    "token",
    "accessToken",
    "refreshToken",
    "sessionToken",
    "apiKey",
    "accessKeyId",
    "secretAccessKey",
    "clientSecret",
    "privateKey",
    "authorization",
    "cookie",
)


def _redact(event_dict: EventDict) -> EventDict:
    """Invoke the censor as structlog would (logger/method_name unused by a key-based censor)."""
    return redact_secrets(None, "info", event_dict)


def test_redacted_constant_is_the_ts_censor_string() -> None:
    assert REDACTED == "[redacted]"


def test_secret_keys_mirror_the_ts_set() -> None:
    assert SECRET_KEYS == _TS_SECRET_KEYS


def test_redact_keys_superset_adds_only_the_header_keys() -> None:
    # REDACT_KEYS = SECRET_KEYS plus the AWS/auth header keys that are not already secret keys.
    assert set(SECRET_KEYS) <= REDACT_KEYS
    assert {"x-api-key", "set-cookie", "x-amz-security-token"} <= REDACT_KEYS
    assert REDACT_KEYS == set(SECRET_KEYS) | {"x-api-key", "set-cookie", "x-amz-security-token"}


def test_every_secret_key_redacted_at_top_level() -> None:
    for key in SECRET_KEYS:
        event_dict = {"event": "deploy", key: "super-sensitive-value"}
        out = _redact(event_dict)
        assert out[key] == REDACTED, key


def test_non_secret_keys_untouched() -> None:
    event_dict = {"event": "deploy", "region": "us-east-1", "username": "alice", "count": 3}
    out = _redact(event_dict)
    assert out == {"event": "deploy", "region": "us-east-1", "username": "alice", "count": 3}


def test_nested_dict_secret_redacted() -> None:
    out = _redact({"event": "x", "outer": {"password": "p", "ok": "keep"}})
    assert out["outer"] == {"password": REDACTED, "ok": "keep"}


def test_deeply_nested_secret_redacted_beyond_pino_single_level() -> None:
    # pino's `*.key` is a single-level wildcard; the recursive censor closes that gap.
    out = _redact({"a": {"b": {"c": {"secretAccessKey": "AKIA..."}}}})
    assert out["a"]["b"]["c"]["secretAccessKey"] == REDACTED


def test_aws_credentials_block_redacted() -> None:
    out = _redact(
        {
            "credentials": {
                "accessKeyId": "AKIAIOSFODNN7EXAMPLE",
                "secretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "sessionToken": "FwoGZXIvYXdz...",
                "expiration": "2026-01-01T00:00:00Z",
            }
        }
    )
    assert out["credentials"] == {
        "accessKeyId": REDACTED,
        "secretAccessKey": REDACTED,
        "sessionToken": REDACTED,
        "expiration": "2026-01-01T00:00:00Z",
    }


def test_secrets_inside_lists_of_dicts_redacted() -> None:
    out = _redact({"items": [{"token": "t1", "id": 1}, {"token": "t2", "id": 2}]})
    assert out["items"] == [{"token": REDACTED, "id": 1}, {"token": REDACTED, "id": 2}]


def test_header_keys_redacted() -> None:
    out = _redact(
        {
            "headers": {
                "authorization": "Bearer abc",
                "cookie": "session=xyz",
                "x-api-key": "key-123",
                "set-cookie": "session=xyz; HttpOnly",
                "content-type": "application/json",
            }
        }
    )
    assert out["headers"] == {
        "authorization": REDACTED,
        "cookie": REDACTED,
        "x-api-key": REDACTED,
        "set-cookie": REDACTED,
        "content-type": "application/json",
    }


def test_censor_mutates_in_place_and_returns_same_object() -> None:
    # structlog copies the event_dict before the chain, so in-place mutation is safe and correct
    # (no clone — the PR #110 failure mode that lost bindings / flattened Errors).
    event_dict: dict[str, object] = {"event": "x", "password": "p"}
    out = redact_secrets(None, "info", event_dict)
    assert out is event_dict
    assert event_dict["password"] == REDACTED


def test_non_dict_non_secret_values_preserved() -> None:
    # An exception lives under a non-secret key (e.g. exc_info) and must stay intact for the
    # exception renderer (dict_tracebacks) — the censor touches dict keys, not Errors.
    err = ValueError("boom")
    out = _redact({"event": "x", "exc_info": err, "n": 1, "flag": True})
    assert out["exc_info"] is err
    assert out["n"] == 1
    assert out["flag"] is True


def test_x_amz_security_token_is_a_denied_header_key() -> None:
    # The STS session-token header botocore sets (X-Amz-Security-Token) is credential material.
    assert "x-amz-security-token" in REDACT_KEYS


def test_redaction_is_case_insensitive() -> None:
    # botocore's SigV4Auth emits capitalized header names (Authorization, X-Amz-Security-Token);
    # HTTP header names are case-insensitive, so the censor matches case-insensitively.
    out = _redact(
        {
            "headers": {
                "Authorization": "AWS4-HMAC-SHA256 Credential=AKIA...",
                "X-Amz-Security-Token": "FwoGZXIvYXdz-session-token",
                "Cookie": "session=abc",
                "X-Api-Key": "key-123",
                "Content-Type": "application/json",
            }
        }
    )
    assert out["headers"] == {
        "Authorization": REDACTED,
        "X-Amz-Security-Token": REDACTED,
        "Cookie": REDACTED,
        "X-Api-Key": REDACTED,
        "Content-Type": "application/json",
    }


def test_secret_inside_tuple_redacted() -> None:
    # A dict-with-secret nested in a tuple (realistic for AWS-shaped / normalized IR payloads):
    # JSONRenderer serializes the tuple as an array, so it must be traversed.
    out = _redact({"creds": ({"secretAccessKey": "AKIA..."}, {"token": "t"})})
    assert out["creds"] == ({"secretAccessKey": REDACTED}, {"token": REDACTED})


def test_self_referential_event_dict_does_not_crash() -> None:
    # A cyclic object graph in a bound value must not crash the censor (RecursionError) inside a
    # logging call — that would be an availability defect for the verifier.
    cyclic: dict[str, object] = {"password": "p"}
    cyclic["self"] = cyclic
    out = _redact(cyclic)
    assert out["password"] == REDACTED
