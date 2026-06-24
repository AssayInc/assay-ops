"""The shared, write-isolated reward core (DECISIONS.md 6A / T1 / 2A).

``grade`` is the *only* public reward entry, so the core's consumption is exactly {deployed-state
read, golden target}. It fails closed on any other provenance (T1), then diffs the two normalized
states (deployed=actual vs golden=expected) into the codegen'd ``DiffIR`` and reads
``reward in {0, 1}`` = zero normalized diff. The diff is tool-agnostic (it never branches on the
source tool) and deterministic (resources and property paths are canonically ordered); per-tool
quirks live in the adapters.
"""

from __future__ import annotations

from dataclasses import dataclass

from assayops_contracts import (
    Change,
    DiffIR,
    PropertyDiffs,
    PropertyDiffs1,
    Resource,
    Reward,
)

from assayops_diff_ir.normalized_state import NormalizedResource, NormalizedState, Provenance

# Reserved structural marker for a resource-type mismatch at the same address. `$`-prefixed paths
# are rejected as property keys (the NormalizedResource validator), so this never collides with one.
_TYPE_PATH = "$type"


class UntrustedInputError(ValueError):
    """Raised when the reward core is handed anything but {deployed read, golden target}.

    A ``ValueError`` (invalid input) -- the code-level T1: the verifier grades only the B-side
    deployed-state read and the regenerated golden, never the agent's ``plan``/``show``/state.
    Fail closed.
    """


@dataclass(frozen=True)
class GradeOutcome:
    """The reward core's result: the binary reward and the diff report it was read from."""

    reward: Reward
    diff: DiffIR


def grade(deployed: NormalizedState, golden: NormalizedState) -> GradeOutcome:
    """Grade a B-side deployed-state read against the regenerated golden -> reward + diff report."""
    _require_trusted_inputs(deployed, golden)
    # The reward core is the trust gate: re-validate inputs into fresh snapshots. `frozen` blocks
    # attribute reassignment but NOT in-place mutation of a properties dict, so tampering past the
    # construction guards is caught here -- fail closed, never grade a forged input.
    deployed = _revalidated(deployed)
    golden = _revalidated(golden)
    diff = _diff_states(deployed=deployed, golden=golden)
    reward = Reward.number_1 if _is_in_sync(diff) else Reward.number_0
    return GradeOutcome(reward=reward, diff=diff)


def _require_trusted_inputs(deployed: NormalizedState, golden: NormalizedState) -> None:
    if deployed.provenance is not Provenance.DEPLOYED_READ:
        raise UntrustedInputError(
            "the reward core grades only a B-side deployed-state read in the deployed slot, "
            f"got provenance={deployed.provenance.value} [T1]"
        )
    if golden.provenance is not Provenance.GOLDEN_TARGET:
        raise UntrustedInputError(
            "the reward core grades only the regenerated golden target in the golden slot, "
            f"got provenance={golden.provenance.value} [T1]"
        )


def _revalidated(state: NormalizedState) -> NormalizedState:
    """Re-validate the RAW object graph so a post-construction mutation can't bypass the guards.

    Reconstructing re-runs the value validator, which validate-and-copies by exact type -- never
    ``copy.deepcopy`` / ``model_dump`` (a ``__deepcopy__`` / serializer could launder a non-JSON
    object past the gate). So this catches tampering AND decouples the report from the inputs (the
    already-graded report bytes can't drift on a later mutation).
    """
    return NormalizedState(
        provenance=state.provenance,
        resources=tuple(
            NormalizedResource(address=r.address, type=r.type, properties=r.properties)
            for r in state.resources
        ),
    )


def _is_in_sync(diff: DiffIR) -> bool:
    return all(r.change is Change.unchanged for r in diff.resources)


def _diff_states(*, deployed: NormalizedState, golden: NormalizedState) -> DiffIR:
    golden_by_address = {r.address: r for r in golden.resources}
    deployed_by_address = {r.address: r for r in deployed.resources}
    # Sort by address so the IR is order-independent: identical states -> identical DiffIR.
    resources: list[Resource] = []
    for address in sorted(set(golden_by_address) | set(deployed_by_address)):
        in_golden = address in golden_by_address
        in_deployed = address in deployed_by_address
        if in_golden and in_deployed:
            resources.append(
                _diff_present(address, golden_by_address[address], deployed_by_address[address])
            )
        elif in_golden:
            # In golden, not deployed: the deploy is missing an expected resource.
            resources.append(
                Resource(
                    address=address, type=golden_by_address[address].type, change=Change.removed
                )
            )
        else:
            # In deployed, not golden: an extra resource the golden does not expect.
            resources.append(
                Resource(
                    address=address, type=deployed_by_address[address].type, change=Change.added
                )
            )
    return DiffIR(resources=resources)


def _diff_present(
    address: str, golden: NormalizedResource, deployed: NormalizedResource
) -> Resource:
    property_diffs = _property_diffs(golden.properties, deployed.properties)
    if golden.type != deployed.type:
        property_diffs.append(
            PropertyDiffs(path=_TYPE_PATH, expected=golden.type, actual=deployed.type)
        )
    if not property_diffs:
        return Resource(address=address, type=golden.type, change=Change.unchanged)
    property_diffs.sort(key=lambda pd: pd.path)
    return Resource(
        address=address, type=golden.type, change=Change.modified, propertyDiffs=property_diffs
    )


def _property_diffs(
    golden: dict[str, object], deployed: dict[str, object]
) -> list[PropertyDiffs | PropertyDiffs1]:
    diffs: list[PropertyDiffs | PropertyDiffs1] = []
    for path in sorted(set(golden) | set(deployed)):
        in_golden = path in golden
        in_deployed = path in deployed
        if in_golden and in_deployed:
            if not _values_equal(golden[path], deployed[path]):
                diffs.append(PropertyDiffs(path=path, expected=golden[path], actual=deployed[path]))
        elif in_golden:
            # Missing from deployed -> expected present, actual absent.
            diffs.append(PropertyDiffs(path=path, expected=golden[path]))
        else:
            # Extra in deployed -> actual present, expected absent.
            diffs.append(PropertyDiffs1(path=path, actual=deployed[path]))
    return diffs


def _values_equal(golden: object, deployed: object) -> bool:
    """Equality on validated JSON values: ``bool`` != a number; int/float compare by value.

    JSON has one number type, so ``int``/``float`` of the same value are equal (``90 == 90.0``; JCS
    canonicalizes them the same) -- distinguishing them is a false-negative drift. But ``bool`` is a
    JSON boolean, NOT a number: ``True`` must never equal ``1`` (``==`` collapses them, grading a
    boolean property in-sync with a numeric one -- a false reward 1). Inputs are validated to exact
    JSON types upstream, so no subclass / NaN reaches here.
    """
    if _is_json_number(golden) and _is_json_number(deployed):
        return golden == deployed
    if type(golden) is not type(deployed):
        return False
    if isinstance(golden, dict) and isinstance(deployed, dict):
        if golden.keys() != deployed.keys():
            return False
        return all(_values_equal(golden[key], deployed[key]) for key in golden)
    if isinstance(golden, list) and isinstance(deployed, list):
        if len(golden) != len(deployed):
            return False
        return all(_values_equal(g, d) for g, d in zip(golden, deployed, strict=True))
    return golden == deployed


def _is_json_number(value: object) -> bool:
    # A JSON number is an exact int or float; `bool` is a JSON boolean, not a number.
    return type(value) is int or type(value) is float
