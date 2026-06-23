"""Deny-by-key secret redaction — the one load-bearing security item, since structlog ships no
built-in redaction (unlike pino, the TS lane).

A structlog *processor* is a ``(logger, method_name, event_dict)`` callable, and structlog copies
the event_dict before the chain runs (processors.html), so the censor mutates it **in place** — NOT
a recursive clone, which is the PR #110 failure mode (lost bindings / flattened Errors). It mirrors
the TS ``SECRET_KEYS`` exactly and redacts **recursively** (dicts and lists), closing pino's
single-level-path / arrays-of-credentials gap with a safe superset of the same key set.

Redaction is defense-in-depth, NOT the control: it catches only enumerated keys at known structure,
not a secret interpolated into a free-text message. The primary rule stays "don't log secrets" (and
never enable botocore/boto3 DEBUG — see config.py and DECISIONS.md §8).
"""

from collections.abc import MutableMapping

from structlog.types import EventDict, WrappedLogger

# The exact key set the TS @assayops/logger redacts (ts/packages/logger/src/index.ts SECRET_KEYS).
# Kept in lockstep with the TS lane by tests/test_ts_parity.py.
SECRET_KEYS: tuple[str, ...] = (
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

# Header keys the TS lane redacts via its `headers["..."]` paths but which are not in SECRET_KEYS.
# Redacting them by key (at any depth) is a safe superset of the TS header paths.
_HEADER_KEYS: tuple[str, ...] = ("x-api-key", "set-cookie")

# The full deny set: a key whose name is in here is masked wherever it appears.
REDACT_KEYS: frozenset[str] = frozenset(SECRET_KEYS) | frozenset(_HEADER_KEYS)

# The censor string — identical to the TS lane.
REDACTED = "[redacted]"


def _redact_in_place(value: object, deny: frozenset[str]) -> None:
    """Recurse into dicts (masking matched keys) and lists, mutating in place. Non-container values
    and objects (e.g. an Exception under ``exc_info``) are left untouched for the renderers."""
    if isinstance(value, MutableMapping):
        for key, child in tuple(value.items()):
            if isinstance(key, str) and key in deny:
                value[key] = REDACTED
            else:
                _redact_in_place(child, deny)
    elif isinstance(value, list):
        for item in value:
            _redact_in_place(item, deny)


def redact_secrets(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """The default censor: masks every ``REDACT_KEYS`` value to ``[redacted]``, recursively."""
    _redact_in_place(event_dict, REDACT_KEYS)
    return event_dict
