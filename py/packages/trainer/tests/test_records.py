"""#176 leg 2: the SFT record shapes -- provenance + one training example.

The training record is what TRL trains on (clean messages+tools); provenance is what makes the set
auditable + reproducible (it lands in the manifest, never in the trained columns). Both are frozen +
`extra="forbid"` (a hardened wire/record model -- pydantic-v2 skill).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from assayops_trainer.records import Provenance, SFTExample


def _provenance(**overrides: object) -> Provenance:
    base: dict[str, object] = {
        "task_id": "drift-s3-encryption",
        "eval_task_id": "eval-task-001",
        "epoch": 1,
        "model": "hf/Qwen2.5-Coder-7B",
        "run_id": "run-abc",
        "harness_git_sha": "deadbeef",
        "reward": 1,
        "verifier_runs": 3,
    }
    base.update(overrides)
    return Provenance.model_validate(base)


def test_provenance_is_frozen_and_forbids_extra() -> None:
    prov = _provenance()
    with pytest.raises(ValidationError):
        Provenance.model_validate({**prov.model_dump(), "sneaky": "x"})
    with pytest.raises(ValidationError):
        prov.task_id = "other"  # type: ignore[misc]


def test_provenance_only_admits_a_positive_example() -> None:
    # The SFT set is rejection-sampled to reward==1; a record claiming reward 0 is a contradiction
    # and is refused at the boundary (the type says "positive example only").
    with pytest.raises(ValidationError):
        _provenance(reward=0)


def test_training_record_is_messages_plus_tools_only() -> None:
    example = SFTExample(
        messages=[{"role": "user", "content": "fix the drift"}],
        tools=[{"type": "function", "function": {"name": "bash"}}],
        provenance=_provenance(),
    )

    record = example.training_record()

    # Exactly the TRL conversational columns -- provenance never leaks into the trained data.
    assert set(record) == {"messages", "tools"}
    assert record["messages"] == [{"role": "user", "content": "fix the drift"}]
    assert record["tools"] == [{"type": "function", "function": {"name": "bash"}}]


def test_training_record_always_carries_a_tools_list_for_a_uniform_schema() -> None:
    # datasets.load_dataset("json") infers ONE schema across rows; a row missing `tools` while
    # another has it corrupts the column. Always emit a list (possibly empty).
    example = SFTExample(
        messages=[{"role": "user", "content": "no tools here"}],
        tools=[],
        provenance=_provenance(),
    )

    assert example.training_record()["tools"] == []
