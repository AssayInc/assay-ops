"""7A transient/genuine classifier (DECISIONS.md §1 / 7A): the policy — which grade-attempt failures
are transiently unreadable (throttle / 5xx / read-after-create eventual consistency — retry within a
bounded budget, NEVER a false-negative reward 0) vs a genuine/settled failure (fail closed). The
retry MECHANISM is boto3 adaptive (in #141's read) + #141's read-after-create poll; this owns the
POLICY, which the read path routes a surfaced transient through (#141 scope 1).
"""

from __future__ import annotations

from assayops_replay import (
    FailureClass,
    TransientGradeError,
    TransientKind,
    classify,
    is_transient_aws_error_code,
    transient_kind,
)


def test_read_after_create_not_found_is_transient() -> None:
    # Eventual consistency: a just-created resource not yet visible (DECISIONS.md §1, #60) is a
    # transient — retry within the small read budget; a SETTLED NotFound (after budget) is genuine.
    assert is_transient_aws_error_code("ResourceNotFoundException") is True


def test_resource_not_found_short_form_is_transient() -> None:
    # Some read surfaces spell the read-after-create signal without the `Exception` suffix.
    assert is_transient_aws_error_code("ResourceNotFound") is True


def test_throttle_is_transient() -> None:
    # A throttle is NOT a wrong answer (the skill; #141 scope 1): scoring it 0
    # is a false-negative reward. boto3 adaptive owns the SDK retry; a surfaced throttle is still a
    # transient the determinism layer must retry, never score 0.
    assert is_transient_aws_error_code("ThrottlingException") is True
    assert is_transient_aws_error_code("RequestThrottledException") is True
    assert is_transient_aws_error_code("SlowDown") is True


def test_5xx_service_error_is_transient() -> None:
    # A 5xx / service blip is transient — retry, not a wrong answer.
    assert is_transient_aws_error_code("ServiceUnavailable") is True
    assert is_transient_aws_error_code("InternalError") is True


def test_access_denied_is_genuine() -> None:
    # An isolation/permissions failure is a real alarm, never masked as a retryable transient.
    assert is_transient_aws_error_code("AccessDeniedException") is False


def test_validation_error_is_genuine() -> None:
    assert is_transient_aws_error_code("ValidationException") is False


def test_unknown_code_is_genuine_fail_closed() -> None:
    # Default-deny: an unrecognized code is genuine (fail closed), never treated as retryable.
    assert is_transient_aws_error_code("SomethingNovelException") is False


def test_classify_transient_marker_is_transient() -> None:
    assert (
        classify(TransientGradeError(TransientKind.INFRA, "throttled read"))
        is FailureClass.TRANSIENT
    )


def test_transient_kind_maps_marker_and_codes() -> None:
    # The marker's explicit kind, else derived from the AWS code (NotFound → EVENTUAL_CONSISTENCY,
    # throttle/5xx → INFRA); a genuine failure → None. The caller maps exhaustion on this kind.
    class FakeClientError(Exception):
        def __init__(self, code: str) -> None:
            super().__init__(code)
            self.response = {"Error": {"Code": code}}

    ec = TransientKind.EVENTUAL_CONSISTENCY
    assert transient_kind(TransientGradeError(ec)) is ec
    assert transient_kind(FakeClientError("ResourceNotFoundException")) is ec
    assert transient_kind(FakeClientError("ThrottlingException")) is TransientKind.INFRA
    assert transient_kind(FakeClientError("ServiceUnavailable")) is TransientKind.INFRA
    assert transient_kind(FakeClientError("AccessDeniedException")) is None
    assert transient_kind(ValueError("bug")) is None


def test_5xx_status_with_unknown_code_is_infra_transient() -> None:
    # botocore retries a 5xx by HTTP status even when the error code is unrecognized, so a surfaced
    # 503-with-unknown-code is an INFRA transient — never a false-negative genuine (scored 0).
    class FakeClientError(Exception):
        def __init__(self, code: str, status: int) -> None:
            super().__init__(code)
            self.response: dict[str, object] = {
                "Error": {"Code": code},
                "ResponseMetadata": {"HTTPStatusCode": status},
            }

    err = FakeClientError("SomeUnmodeledServiceError", 503)
    assert classify(err) is FailureClass.TRANSIENT
    assert transient_kind(err) is TransientKind.INFRA
    # A 4xx genuine (AccessDenied 403) is NOT a 5xx → stays genuine, fail closed.
    assert classify(FakeClientError("AccessDeniedException", 403)) is FailureClass.GENUINE


def test_idp_communication_error_is_transient() -> None:
    # botocore's RetryIDPCommunicationError — an identity-provider communication blip is transient.
    assert is_transient_aws_error_code("IDPCommunicationError") is True


def test_connection_and_timeout_exceptions_are_infra_transient() -> None:
    # botocore retries connection/timeout exceptions (ConnectionError / HTTPClientError subclasses);
    # they have no `.response`, so detect by MRO class name. A surfaced one is INFRA, never a
    # false-negative genuine. The builtin ConnectionError (a network error) matches too.
    assert classify(ConnectionError("network down")) is FailureClass.TRANSIENT
    assert transient_kind(ConnectionError("network down")) is TransientKind.INFRA

    class HTTPClientError(Exception):  # mimics botocore.exceptions.HTTPClientError
        pass

    class ReadTimeoutError(HTTPClientError):  # mimics botocore's ReadTimeoutError
        pass

    assert transient_kind(ReadTimeoutError()) is TransientKind.INFRA
    # A plain bug (no connection/HTTP base) stays genuine — fail closed.
    assert transient_kind(ValueError("bug")) is None


def test_classify_client_error_shaped_is_classified_by_code() -> None:
    # A botocore-ClientError-shaped exception (``.response['Error']['Code']``) is classified by its
    # code WITHOUT importing botocore — replay stays boto3-free; #141's read path owns boto3.
    class FakeClientError(Exception):
        def __init__(self, code: str) -> None:
            super().__init__(code)
            self.response = {"Error": {"Code": code}}

    assert classify(FakeClientError("ResourceNotFoundException")) is FailureClass.TRANSIENT
    assert classify(FakeClientError("ThrottlingException")) is FailureClass.TRANSIENT
    assert classify(FakeClientError("AccessDeniedException")) is FailureClass.GENUINE


def test_classify_plain_bug_is_genuine() -> None:
    # A bug (ValueError/TypeError) is never a transient — never retried into a silent reward.
    assert classify(ValueError("boom")) is FailureClass.GENUINE


def test_classify_malformed_client_error_is_genuine() -> None:
    # A ClientError-shaped exception missing Error/Code (or wrong-typed) extracts no code, so it is
    # genuine (fail closed), never mis-retried — the duck-typed extraction's partial-shape branches.
    class ShapeOnly(Exception):
        def __init__(self, response: object) -> None:
            super().__init__("shape")
            self.response = response

    assert classify(ShapeOnly({})) is FailureClass.GENUINE  # no "Error"
    assert classify(ShapeOnly({"Error": {}})) is FailureClass.GENUINE  # no "Code"
    assert classify(ShapeOnly({"Error": {"Code": 123}})) is FailureClass.GENUINE  # non-str Code
    assert classify(ShapeOnly("not-a-dict")) is FailureClass.GENUINE  # response not a dict
