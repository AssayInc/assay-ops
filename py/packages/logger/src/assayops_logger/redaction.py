"""Deny-by-key secret redaction — the one load-bearing security item, since structlog ships no
built-in redaction (unlike pino, the TS lane).

A structlog *processor* is a ``(logger, method_name, event_dict)`` callable, and structlog copies
the event_dict before the chain runs (processors.html), so the censor mutates it **in place** — NOT
a recursive clone, which is the PR #110 failure mode (lost bindings / flattened Errors). It mirrors
the TS ``SECRET_KEYS`` exactly and masks any denied key **case-insensitively** in a dict, recursing
through nested dicts and list/tuple sequences — a safe superset of pino's single-level-path / arrays
model. The match is case-insensitive because botocore signs requests with capitalized
``Authorization`` / ``X-Amz-Security-Token``; HTTP header names are case-insensitive.

Redaction is defense-in-depth, NOT the control. It deliberately does NOT cover secrets keyed by
**non-dict** structures — a ``(key, value)`` tuple/pair sequence, a ``NamedTuple``'s fields, a
set/frozenset, an immutable mapping — nor a secret interpolated into a free-text message or a
positional ``%``-arg. Those are the "nested arbitrarily" cases a key censor can't catch; the control
is the primary rule: **don't log secrets** (and never enable botocore/boto3 DEBUG — config.py clamps
the noisy AWS loggers; DECISIONS.md §8). Keeping the censor a simple, auditable key-matcher rather
than a heuristic deep-redactor is itself a security property (hand-rolling one is a defect magnet).
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

# AWS/auth header keys the TS lane redacts via its `headers["..."]` paths but which are not in
# SECRET_KEYS, plus `x-amz-security-token` (the STS session-token header botocore's SigV4Auth sets).
# Redacting them by key at any depth is a safe superset of the TS header paths.
_HEADER_KEYS: tuple[str, ...] = ("x-api-key", "set-cookie", "x-amz-security-token")

# The full deny set: a key whose name is in here is masked wherever it appears.
REDACT_KEYS: frozenset[str] = frozenset(SECRET_KEYS) | frozenset(_HEADER_KEYS)

# Case-insensitive form used for matching. HTTP header names are case-insensitive and botocore signs
# requests with capitalized `Authorization` / `X-Amz-Security-Token`; a case-sensitive match would
# leak them. The public REDACT_KEYS / SECRET_KEYS keep their original case (TS-parity contract).
_DENY_CASEFOLDED: frozenset[str] = frozenset(key.casefold() for key in REDACT_KEYS)

# The censor string — identical to the TS lane.
REDACTED = "[redacted]"


def _redact_in_place(value: object, deny: frozenset[str], seen: set[int]) -> None:
    """Recurse into dicts (masking matched keys case-insensitively) and list/tuple sequences,
    mutating in place. A visited-id guard prevents a RecursionError on a cyclic object graph.
    Non-container values and objects (e.g. an Exception under ``exc_info``) are left untouched for
    the renderers. ``deny`` is the casefolded deny set."""
    if isinstance(value, MutableMapping):
        if id(value) in seen:
            return
        seen.add(id(value))
        for key, child in tuple(value.items()):
            if isinstance(key, str) and key.casefold() in deny:
                value[key] = REDACTED
            else:
                _redact_in_place(child, deny, seen)
    elif isinstance(value, (list, tuple)):
        # Tuples can hold a secret-bearing dict (AWS-shaped / normalized IR payloads); JSONRenderer
        # serializes them as arrays, so they must be traversed. The nested dict is mutated in place.
        if id(value) in seen:
            return
        seen.add(id(value))
        for item in value:
            _redact_in_place(item, deny, seen)


def redact_secrets(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """The default censor: masks every ``REDACT_KEYS`` value to ``[redacted]``, case-insensitively
    and recursively (dicts + list/tuple)."""
    _redact_in_place(event_dict, _DENY_CASEFOLDED, set())
    return event_dict
