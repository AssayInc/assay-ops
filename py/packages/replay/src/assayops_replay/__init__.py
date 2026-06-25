"""AssayOps determinism harness (DECISIONS.md 7A / T8, epic E6).

The verifier's determinism policy: a transient/genuine failure classifier + K-run reproduce +
**quarantine** of flaky tasks. ``reproduce`` drives a grade callable K times, absorbs a
transiently-unreadable read (throttle / 5xx / eventual consistency) within a bounded budget, and
**quarantines** a
non-reproducing (flaky) task so its reward is never silently shipped into training (vector #15 —
"never silently rewarded"). It is generic over an injected grade callable, so it does not import the
verifier; the read path (#141) reuses this classifier without a dependency cycle.
"""

from assayops_replay.classifier import (
    FailureClass,
    TransientGradeError,
    TransientKind,
    classify,
    is_transient_aws_error_code,
    transient_kind,
)
from assayops_replay.reproduce import (
    DEFAULT_MAX_TRANSIENT_RETRIES,
    DEFAULT_RUNS,
    GradeFn,
    Quarantined,
    ReproduceVerdict,
    Reproducible,
    TransientBudgetExhausted,
    reproduce,
)

__all__ = [
    "DEFAULT_MAX_TRANSIENT_RETRIES",
    "DEFAULT_RUNS",
    "FailureClass",
    "GradeFn",
    "Quarantined",
    "Reproducible",
    "ReproduceVerdict",
    "TransientBudgetExhausted",
    "TransientGradeError",
    "TransientKind",
    "classify",
    "is_transient_aws_error_code",
    "reproduce",
    "transient_kind",
]
