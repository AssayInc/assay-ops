"""#176 leg 2: persisting the SFT set -- the training JSONL + a reproducible provenance manifest.

The JSONL holds ONLY the trained columns ({messages, tools}); the manifest holds the provenance +
curation counts, aligned line-for-line to the JSONL, and carries the R1 framing so the artifact
can't be mistaken for the E13 proof corpus. ``build_and_write`` is the end-to-end seam: read graded
logs -> build -> write both files.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSample, EvalSpec, write_eval_log
from inspect_ai.model import ChatMessageUser
from inspect_ai.scorer import CORRECT, Score

from assayops_trainer.etl import (
    DEFAULT_SCORER_NAME,
    SftDataset,
    build_and_write,
    write_manifest,
    write_sft_jsonl,
)
from assayops_trainer.records import Provenance, SFTExample


def _example(task_id: str, epoch: int = 1) -> SFTExample:
    return SFTExample(
        messages=[{"role": "user", "content": f"fix {task_id}"}],
        tools=[{"type": "function", "function": {"name": "bash"}}],
        provenance=Provenance(
            task_id=task_id,
            eval_task_id="eval-task-001",
            epoch=epoch,
            model="hf/base",
            run_id="run-1",
            harness_git_sha="cafe",
            reward=1,
            verifier_runs=3,
        ),
    )


def _dataset() -> SftDataset:
    return SftDataset(
        examples=(_example("task-a"), _example("task-b")),
        excluded_incorrect=1,
        excluded_quarantined=2,
        excluded_errored=0,
        dropped_duplicates=1,
        source_run_ids=("run-1",),
    )


def test_jsonl_holds_only_the_trained_columns(tmp_path: Path) -> None:
    path = tmp_path / "sft.jsonl"

    write_sft_jsonl(_dataset(), path)

    lines = path.read_text().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert set(first) == {"messages", "tools"}
    assert first["messages"][0]["content"] == "fix task-a"


def test_manifest_carries_provenance_counts_and_the_r1_framing(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"

    write_manifest(_dataset(), path)

    manifest = json.loads(path.read_text())
    assert "NOT the E13 proof" in manifest["framing"]
    assert manifest["counts"]["examples"] == 2
    assert manifest["counts"]["excluded_quarantined"] == 2
    assert manifest["counts"]["dropped_duplicates"] == 1
    assert manifest["source_run_ids"] == ["run-1"]
    # provenance is aligned line-for-line with the JSONL
    assert [e["task_id"] for e in manifest["examples"]] == ["task-a", "task-b"]
    assert manifest["examples"][0]["reward"] == 1


def test_manifest_line_count_matches_the_jsonl(tmp_path: Path) -> None:
    ds = _dataset()
    write_sft_jsonl(ds, tmp_path / "sft.jsonl")
    write_manifest(ds, tmp_path / "manifest.json")

    jsonl_lines = (tmp_path / "sft.jsonl").read_text().splitlines()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert len(jsonl_lines) == len(manifest["examples"]) == manifest["counts"]["examples"]


def test_build_and_write_reads_graded_logs_end_to_end(tmp_path: Path) -> None:
    sample = EvalSample(
        id="task-pass",
        epoch=1,
        input="fix the drift",
        target="",
        messages=[ChatMessageUser(content="fix task-pass")],
        scores={
            DEFAULT_SCORER_NAME: Score(
                value=CORRECT,
                metadata={
                    "verdict": "reproducible",
                    "reward": 1,
                    "runs": 3,
                    "task_id": "task-pass",
                },
            )
        },
    )
    log = EvalLog(
        eval=EvalSpec(
            run_id="run-1",
            created="2026-07-02T00:00:00+00:00",
            task="drift_slice",
            dataset=EvalDataset(),
            model="hf/base",
            config=EvalConfig(),
        ),
        status="success",
        samples=[sample],
    )
    log_path = tmp_path / "base.eval"
    write_eval_log(log, str(log_path))
    out_dir = tmp_path / "out"

    ds = asyncio.run(build_and_write([log_path], out_dir, harness_git_sha="cafe"))

    assert len(ds.examples) == 1
    assert (out_dir / "sft.jsonl").is_file()
    assert (out_dir / "manifest.json").is_file()
    record = json.loads((out_dir / "sft.jsonl").read_text().splitlines()[0])
    assert record["messages"][0]["content"] == "fix task-pass"
