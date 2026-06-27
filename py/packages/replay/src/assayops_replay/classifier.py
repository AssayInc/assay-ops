"""The 7A transient/genuine failure classifier (DECISIONS.md §1 / 7A; epic E6 / T8).

A grade attempt against live cloud state can fail two ways the determinism policy treats
differently:

- **Transient** (transiently unreadable — NOT a wrong answer): a throttle, a 5xx / service blip, a
  request timeout, or read-after-create eventual consistency (a fresh resource not yet visible).
  Scoring any of these 0 is a *false-negative reward* — the anti-pattern the deterministic-
  verification skill names ("a throttle ... is transient, never a false-negative 0"). Retry within
  a bounded budget; only a *settled* mismatch is reward 0.
- **Genuine** (a settled failure): an ``AccessDenied`` (an isolation alarm, never masked), a
  ``ValidationException``, a settled ``NotFound`` after the read budget, or a bug. Fail closed.

Policy vs mechanism. This owns the *policy* (which signals are transient). The read path (#141) uses
it to route a transiently-unreadable read through the 7A classifier + K-run (#141 scope 1: "never
pass on a transient"). The retry *mechanism* is not duplicated here: boto3's adaptive retry absorbs
SDK throttles / 5xx within a read, and #141's read-after-create poll handles eventual consistency. A
surfaced transient those could not absorb is routed here, classified TRANSIENT, and re-attempted by
the K-run gate — never scored 0 on the spot.

The transient **kind** (``TransientKind``) is what the caller maps on budget exhaustion (see
``reproduce.TransientBudgetExhausted``): a settled-absent ``EVENTUAL_CONSISTENCY`` ⇒ reward 0; an
``INFRA`` transient (throttle / 5xx the read could not complete) ⇒ quarantine, NOT reward 0 (that
would be the false-negative). So the read path (#141) must surface a kind-carrying transient:
a raw botocore ``ClientError`` (its code identifies the kind), or a ``TransientGradeError`` with an
explicit ``kind``.

boto3-free. #141's read path classifies a surfaced transient by calling ``transient_kind`` (this
classifier's best-effort policy: the static code sets + a 5xx HTTP status + a connection / timeout
exception class — covering boto3's code / status / exception retry checkers), then raises a
``TransientGradeError`` marker carrying that verdict. boto3's adaptive retry owns the per-read RETRY
MECHANISM (it absorbs throttles / 5xx WITHIN a read); this classifier owns the surfaced-transient
POLICY. The one case it cannot mirror boto3-free is a service-*modeled*-retryable error (per-service
JSON metadata) with an unrecognized code AND a non-5xx status — it classifies GENUINE (a narrow,
safe-direction false-negative; Cloud Control's own throttles are code/status-covered).
"""

from __future__ import annotations

from enum import Enum


class FailureClass(Enum):
    """How the determinism policy treats a grade-attempt failure."""

    TRANSIENT = "transient"  # transiently unreadable — retry; never a false-negative reward 0
    GENUINE = "genuine"  # a settled failure — fail closed; never retried into a silent reward


class TransientKind(Enum):
    """Which transient — what the caller maps on budget exhaustion."""

    EVENTUAL_CONSISTENCY = "eventual_consistency"  # NotFound: settled-absent ⇒ reward 0
    INFRA = "infra"  # throttle / 5xx: read could not complete ⇒ quarantine (never reward 0)


class TransientGradeError(Exception):
    """The read path's signal that a grade attempt was transiently unreadable — retry via the K-run.

    Raised by the read path (#141) for a transient (throttle / 5xx / eventual consistency) that
    boto3's adaptive retry and the read-after-create poll did not absorb, so it routes through the
    determinism layer (#141 scope 1: "never pass on a transient"). It carries the ``kind`` so a
    budget-exhausted transient maps correctly (eventual consistency ⇒ reward 0; infra ⇒ quarantine);
    a dedicated type lets the harness re-attempt without inspecting AWS error codes, keeping the
    package boto3-free.
    """

    def __init__(self, kind: TransientKind, detail: str = "") -> None:
        super().__init__(f"{kind.value}: {detail}" if detail else kind.value)
        self.kind = kind


# Read-after-create eventual consistency (DECISIONS.md §1, spike #60): a fresh resource not yet
# visible to the verifier's Cloud Control read — retry within the small read budget; a NotFound that
# SETTLES after the budget is genuine (reward 0, vector #15). Cloud Control raises
# ``ResourceNotFoundException``; some surfaces spell it ``ResourceNotFound``.
_EVENTUAL_CONSISTENCY_CODES = frozenset({"ResourceNotFoundException", "ResourceNotFound"})

# Infra transients — a throttle is NOT a wrong answer (the skill; #141 scope 1
# routes it through the 7A classifier). boto3 adaptive owns the SDK throttle RETRY; this labels a
# *surfaced* one so the K-run re-attempts it rather than scoring it 0. Best-effort fallback — the
# authoritative path is #141 raising the structured marker (via boto3's retryable classification),
# so this need not be a complete botocore mirror.
_INFRA_TRANSIENT_CODES = frozenset(
    {
        # Throttling family.
        "Throttling",
        "ThrottlingException",
        "ThrottledException",
        "RequestThrottled",
        "RequestThrottledException",
        "TooManyRequestsException",
        "RequestLimitExceeded",
        "BandwidthLimitExceeded",
        "LimitExceededException",
        "ProvisionedThroughputExceededException",
        "TransactionInProgressException",
        "SlowDown",
        "EC2ThrottledException",
        "PriorRequestNotComplete",
        # Service-side / network blips (5xx-class + timeouts).
        "RequestTimeout",
        "RequestTimeoutException",
        "ServiceUnavailable",
        "ServiceUnavailableException",
        "InternalError",
        "InternalFailure",
        "InternalServerError",
        # An identity-provider communication blip (botocore's RetryIDPCommunicationError).
        "IDPCommunicationError",
    }
)

_TRANSIENT_AWS_ERROR_CODES = _EVENTUAL_CONSISTENCY_CODES | _INFRA_TRANSIENT_CODES

# A 5xx HTTP status is retryable even with an UNRECOGNIZED error code — botocore's standard retry
# (``TransientRetryableChecker._TRANSIENT_STATUS_CODES`` in the pinned source). So a surfaced
# 5xx is an INFRA transient, never a false-negative "genuine"-scored 0.
_TRANSIENT_HTTP_STATUS_CODES = frozenset({500, 502, 503, 504})

# Connection / timeout exceptions are retryable too — botocore's ``TransientRetryableChecker``
# retries any ``(ConnectionError, HTTPClientError)`` (verified vs the pinned source), which every
# connection/timeout error subclasses (EndpointConnectionError, ReadTimeoutError, ...). Detected
# boto3-free by MRO class name (also catches the builtin ``ConnectionError`` — a network transient).
_TRANSIENT_EXC_BASE_NAMES = frozenset({"ConnectionError", "HTTPClientError"})


def is_transient_aws_error_code(code: str) -> bool:
    """The 7A policy: is this AWS error code transiently unreadable (retry, never score 0) vs a
    genuine/settled failure (fail closed)?

    Transient (``True``) — throttling / 5xx / request-timeout / read-after-create ``NotFound``.
    Genuine (``False``) — ``AccessDenied*`` (isolation alarm), ``ValidationException``, and any
    unrecognized code (default-deny / fail closed).
    """
    return code in _TRANSIENT_AWS_ERROR_CODES


def transient_kind(failure: BaseException) -> TransientKind | None:
    """The transient kind for exhaustion mapping, or ``None`` if ``failure`` is genuine.

    The ``TransientGradeError`` marker's ``kind``; else from a botocore ``ClientError``: by code (a
    NotFound ⇒ ``EVENTUAL_CONSISTENCY``, a throttle ⇒ ``INFRA``) and, like botocore's retry, by
    **HTTP status** (a 5xx ⇒ ``INFRA`` even with an unrecognized code — never a false-negative).
    """
    if isinstance(failure, TransientGradeError):
        return failure.kind
    code = _aws_error_code(failure)
    if code in _EVENTUAL_CONSISTENCY_CODES:
        return TransientKind.EVENTUAL_CONSISTENCY
    if code in _INFRA_TRANSIENT_CODES:
        return TransientKind.INFRA
    status = _aws_http_status(failure)
    if status is not None and status in _TRANSIENT_HTTP_STATUS_CODES:
        return TransientKind.INFRA
    if _is_transient_exception(failure):
        return TransientKind.INFRA
    return None


def classify(failure: BaseException) -> FailureClass:
    """Classify a grade-attempt failure as ``TRANSIENT`` (retry) or ``GENUINE`` (fail closed).

    TRANSIENT iff it is an explicit ``TransientGradeError`` OR a botocore-``ClientError``-shaped
    exception whose code is transiently unreadable (i.e. ``transient_kind`` resolves it). Everything
    else — a bug (``ValueError`` / ``TypeError``), an ``AccessDenied``, a settled mismatch — is
    GENUINE: never retried into a false-negative reward, never silently rewarded.
    """
    return FailureClass.TRANSIENT if transient_kind(failure) is not None else FailureClass.GENUINE


def _aws_error_code(failure: BaseException) -> str | None:
    """Best-effort extract of a botocore ``ClientError`` code WITHOUT importing botocore.

    botocore exposes ``err.response['Error']['Code']``. Reading it by duck typing keeps the package
    boto3-free (the read path #141 owns boto3) while letting the classifier label a forwarded
    transient (throttle / ``ResourceNotFoundException``) correctly — so a transient read is never
    mis-settled as genuine (a false-negative reward).
    """
    response: object = getattr(failure, "response", None)
    if not isinstance(response, dict):
        return None
    error: object = response.get("Error")
    if not isinstance(error, dict):
        return None
    code: object = error.get("Code")
    return code if isinstance(code, str) else None


def _aws_http_status(failure: BaseException) -> int | None:
    """Best-effort extract of a botocore ``ClientError`` HTTP status WITHOUT importing botocore.

    botocore exposes ``err.response['ResponseMetadata']['HTTPStatusCode']``. Used to label a 5xx
    transient even when its error code is unrecognized (matching botocore's status-based retry).
    """
    response: object = getattr(failure, "response", None)
    if not isinstance(response, dict):
        return None
    meta: object = response.get("ResponseMetadata")
    if not isinstance(meta, dict):
        return None
    status: object = meta.get("HTTPStatusCode")
    return status if isinstance(status, int) else None


def _is_transient_exception(failure: BaseException) -> bool:
    """True for a botocore connection/timeout exception (no ``.response`` code/status to inspect).

    Matches botocore's ``TransientRetryableChecker`` exception path by MRO class name, so a surfaced
    ``EndpointConnectionError`` / ``ReadTimeoutError`` is INFRA, not a false-negative genuine.
    """
    return any(cls.__name__ in _TRANSIENT_EXC_BASE_NAMES for cls in type(failure).__mro__)
