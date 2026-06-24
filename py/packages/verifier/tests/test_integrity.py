"""Content-address integrity — ``golden_digest`` pins a canonical golden even though Pydantic
``frozen`` is shallow (the open ``properties`` dict stays mutable). The resource set is a tuple
(cannot be emptied/extended), and ``golden_digest`` re-validates so post-generation tampering (a
verifier-internal bug, never agent-reachable) fails closed, not a misleading address.
"""

from __future__ import annotations

import pytest
from synthetic import SYNTHETIC_TASK_ID, make_task, s3_bucket_builder

from assayops_verifier.golden import GoldenError, GoldenRegistry, golden_digest
from assayops_verifier.models import GoldenTarget


def _golden() -> GoldenTarget:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry.generate(make_task(), "seed")


def test_resources_is_an_immutable_tuple() -> None:
    # A tuple cannot be emptied/extended after generation (frozen alone would leave a list mutable).
    assert isinstance(_golden().resources, tuple)


def test_tampering_a_property_fails_closed_at_digest() -> None:
    golden = _golden()
    # frozen is shallow: the properties dict is still mutable. Inject a non-deterministic value.
    golden.resources[0].properties["injected"] = {"a", "b"}
    with pytest.raises(GoldenError):
        golden_digest(golden)  # re-validation rejects the set — fail closed, no misleading address
