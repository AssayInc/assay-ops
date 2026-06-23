"""Reset the process-global structlog + stdlib ``logging`` state between tests so configuration,
contextvars, and the AWS clamps never leak across cases. Output is captured via an injected stream
(helpers.parse_log_lines) so tests assert on the full rendered pipeline, not pre-render hooks."""

import logging
from collections.abc import Iterator

import pytest
import structlog


@pytest.fixture(autouse=True)
def _reset_logging_state() -> Iterator[None]:
    yield
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for name in ("botocore", "boto3", "urllib3", "s3transfer"):
        logging.getLogger(name).setLevel(logging.NOTSET)
