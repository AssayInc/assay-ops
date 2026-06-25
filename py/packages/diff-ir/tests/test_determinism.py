"""E3-1 (#34, AC3) -- "no diff" is deterministic (DECISIONS.md 2A/7A).

The pure reward core is deterministic: the same two normalized states always produce the same
DiffIR and the same reward, independent of the order resources/properties were supplied in (the
core canonically orders both). This is the in-process determinism the normalization rules promise;
the LIVE-cloud K-run reproduce (transient handling, eventual consistency) is the verifier read
harness's job (E2/E6, the ``deterministic-verification`` skill), not this pure core.
"""

from __future__ import annotations

from factories import by_address, deployed, golden, res

from assayops_diff_ir import grade


def test_grade_is_independent_of_resource_and_property_order() -> None:
    # Same content, supplied in different resource order and different property-insertion order.
    shuffled = grade(
        deployed(res("b", x=1, y=2), res("a"), res("c")),
        golden(res("c"), res("a"), res("b", y=2, x=1)),
    )
    ordered = grade(
        deployed(res("a"), res("b", x=1, y=2), res("c")),
        golden(res("a"), res("b", x=1, y=2), res("c")),
    )
    assert shuffled.diff == ordered.diff
    assert shuffled.reward is ordered.reward


def test_property_diffs_are_canonically_ordered() -> None:
    outcome = grade(
        deployed(res("r", zebra="z2", alpha="a2")),
        golden(res("r", alpha="a1", zebra="z1")),
    )
    resource = by_address(outcome)["r"]
    assert resource.propertyDiffs is not None
    paths = [pd.path for pd in resource.propertyDiffs]
    assert paths == sorted(paths)


def test_grade_reproduces_identically_across_repeated_runs() -> None:
    deployed_state = deployed(
        res("bucket", versioning="Suspended"),
        res("queue", rtype="AWS::SQS::Queue"),
    )
    golden_state = golden(res("bucket", versioning="Enabled"))
    outcomes = [grade(deployed_state, golden_state) for _ in range(5)]
    for outcome in outcomes[1:]:
        assert outcome.reward is outcomes[0].reward
        assert outcome.diff == outcomes[0].diff
