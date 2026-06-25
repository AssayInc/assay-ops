"""#31 (E2-2) — the integration's T1 trust boundary (DECISIONS.md §1/§8, T1/2A).

grade_deployment composes #75 (regenerate the golden) with #34 (grade) — so it must inherit, not
bypass, the moat: the deployed slot accepts ONLY a B-side deployed read (never the agent's
plan/state), the golden is REGENERATED internally (never caller-supplied — 2A "independently
regenerated golden"), and a golden the reward core cannot represent fails CLOSED (never a silent
reward). These guard the new seam at the code level; they complement (do not replace) the account-B
isolation that is the moat.
"""

from __future__ import annotations

import inspect

import pytest
from assayops_diff_ir import NormalizedResource, NormalizedState, Provenance, UntrustedInputError
from synthetic import (
    DOLLAR_KEY_TASK_ID,
    NONE_PROPERTY_TASK_ID,
    SYNTHETIC_TASK_ID,
    dollar_key_builder,
    make_task,
    none_property_builder,
    s3_bucket_builder,
)

from assayops_verifier import (
    GoldenBuilder,
    GoldenNotGradableError,
    GoldenRegistry,
    golden_as_normalized_state,
    grade_deployment,
)

# The two documented divergences where #75's generator is looser than #34's grading core, so the
# bridge must fail closed on both (the adjacent-case rule, lessons.md): a None value, a `$`-key.
_NON_NORMALIZABLE = [
    (NONE_PROPERTY_TASK_ID, none_property_builder),
    (DOLLAR_KEY_TASK_ID, dollar_key_builder),
]

SEED = "episode-7"


def _registry() -> GoldenRegistry:
    registry = GoldenRegistry()
    registry.register(SYNTHETIC_TASK_ID, s3_bucket_builder)
    return registry


@pytest.mark.parametrize(
    "tainted",
    [Provenance.AGENT_PLAN, Provenance.AGENT_STATE, Provenance.GOLDEN_TARGET],
)
def test_rejects_a_non_deployed_read_in_the_deployed_slot(tainted: Provenance) -> None:
    # Agent plan/state in the deployed slot is the T1 hole; a golden there is a wiring mistake. The
    # composition must fail closed exactly as the reward core does — the integration adds no bypass.
    registry = _registry()
    tainted_deployed = NormalizedState(
        provenance=tainted,
        resources=(NormalizedResource(address="x", type="AWS::S3::Bucket", properties={}),),
    )
    with pytest.raises(UntrustedInputError):
        grade_deployment(registry, make_task(seed=SEED), SEED, tainted_deployed)


def test_bridge_tags_the_golden_as_golden_target_provenance() -> None:
    # The bridge is the only thing that mints a GOLDEN_TARGET state from a regenerated golden, so
    # the reward core's golden-slot guard stays meaningful (a deployed read can't wear that tag).
    registry = _registry()
    target = registry.generate(make_task(seed=SEED), SEED)

    golden_state = golden_as_normalized_state(target)

    assert golden_state.provenance is Provenance.GOLDEN_TARGET
    assert {r.address for r in golden_state.resources} == {r.address for r in target.resources}


def test_regenerates_the_golden_and_never_accepts_one() -> None:
    # 2A/T1: the verifier REGENERATES the golden from (task, seed); a caller cannot inject it. The
    # signature exposes only {registry, task, seed, deployed} — no golden/expected slot to forge.
    params = set(inspect.signature(grade_deployment).parameters)
    assert "golden" not in params
    assert "expected" not in params
    assert {"registry", "task", "seed", "deployed"} <= params


@pytest.mark.parametrize(("task_id", "builder"), _NON_NORMALIZABLE)
def test_non_normalizable_golden_fails_closed_through_grade_deployment(
    task_id: str, builder: GoldenBuilder
) -> None:
    # #75's generator accepts a None value and a `$`-key; the #34 grading core forbids both — so
    # grade_deployment must fail closed (GoldenNotGradableError), never reaching a reward (§8, #15).
    registry = GoldenRegistry()
    registry.register(task_id, builder)
    deployed = NormalizedState(provenance=Provenance.DEPLOYED_READ, resources=())
    with pytest.raises(GoldenNotGradableError):
        grade_deployment(registry, make_task(task_id=task_id, seed=SEED), SEED, deployed)


@pytest.mark.parametrize(("task_id", "builder"), _NON_NORMALIZABLE)
def test_bridge_fails_closed_on_a_non_normalizable_golden(
    task_id: str, builder: GoldenBuilder
) -> None:
    registry = GoldenRegistry()
    registry.register(task_id, builder)
    target = registry.generate(make_task(task_id=task_id, seed=SEED), SEED)
    with pytest.raises(GoldenNotGradableError):
        golden_as_normalized_state(target)


def test_golden_not_gradable_error_is_in_the_value_error_family() -> None:
    # Invalid input → ValueError (python-error-handling), consistent with UntrustedInputError and
    # the value validators, so a caller can catch any malformed grade input uniformly.
    assert issubclass(GoldenNotGradableError, ValueError)
