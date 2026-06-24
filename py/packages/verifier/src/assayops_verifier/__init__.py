"""AssayOps account-B verifier core (DECISIONS.md §1/§8, T1).

E2-5 (#75): the golden-target generator. The grading path (deployed-state read, diff IR, reward
core) is E2-1/#30 + E2-3/#32. The per-task golden builders are the private corpus (#76); this
package is the engine that runs them: ``GoldenRegistry.generate(task, seed)`` → a content-addressed
``GoldenTarget``.
"""

from __future__ import annotations

from assayops_verifier.golden import (
    GoldenBuilder,
    GoldenContext,
    GoldenError,
    GoldenRegistry,
    UnknownTaskError,
    golden_digest,
)
from assayops_verifier.models import GoldenResource, GoldenTarget

__all__ = [
    "GoldenBuilder",
    "GoldenContext",
    "GoldenError",
    "GoldenRegistry",
    "GoldenResource",
    "GoldenTarget",
    "UnknownTaskError",
    "golden_digest",
]
