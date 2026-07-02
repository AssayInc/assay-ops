"""AssayOps SFT trainer leg (pre-T0 #176 slice) -- trajectory->SFT ETL + TRL SFT+LoRA harness.

Public surface:
- ETL: ``build_sft_dataset`` / ``build_and_write`` (rejection sampling on the account-B reward)
  + ``write_sft_jsonl`` / ``write_manifest`` + ``SftDataset`` + ``DEFAULT_SCORER_NAME``.
- Records: ``SFTExample`` / ``Provenance``.
- Transcript conversion: ``sample_to_openai_messages`` / ``sample_tools``.
- Trainer: ``TrainerConfig`` + ``run_sft`` (lazy-imports the heavy stack; see ``sft``).
"""

from __future__ import annotations

from assayops_trainer.config import TrainerConfig
from assayops_trainer.etl import (
    DEFAULT_SCORER_NAME,
    SftDataset,
    build_and_write,
    build_sft_dataset,
    write_manifest,
    write_sft_jsonl,
)
from assayops_trainer.messages import sample_to_openai_messages, sample_tools
from assayops_trainer.records import Provenance, SFTExample
from assayops_trainer.sft import run_sft

__all__ = [
    "DEFAULT_SCORER_NAME",
    "Provenance",
    "SFTExample",
    "SftDataset",
    "TrainerConfig",
    "build_and_write",
    "build_sft_dataset",
    "run_sft",
    "sample_to_openai_messages",
    "sample_tools",
    "write_manifest",
    "write_sft_jsonl",
]
