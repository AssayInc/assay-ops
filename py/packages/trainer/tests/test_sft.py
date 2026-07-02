"""#176 leg 2: the TRL SFT+LoRA harness -- lazy-imported so the heavy stack stays out of the gate.

The stack (trl/peft/transformers/datasets/accelerate/torch) is intentionally NOT a workspace dep, so
in the hermetic gate ``run_sft`` fails with a clear pointer to the pinned requirements file rather
than a raw ModuleNotFoundError. When the stack IS present, the config's kwargs must construct the
REAL ``SFTConfig`` / ``LoraConfig`` -- the grounding check that our kwarg names match the API.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from assayops_trainer.config import TrainerConfig
from assayops_trainer.sft import run_sft

_CFG = TrainerConfig.model_validate({"model_revision": "a1b2c3d4"})


def test_run_sft_without_the_training_stack_points_at_the_requirements(tmp_path: Path) -> None:
    with pytest.raises(ImportError, match="train-requirements"):
        run_sft(_CFG, tmp_path / "sft.jsonl")


def test_config_kwargs_construct_the_real_trl_and_peft_configs() -> None:
    # Skips in the hermetic gate (stack absent); runs where a training env installed it, proving the
    # kwarg names in config.py match the real TRL/PEFT API (no model download involved).
    pytest.importorskip("trl")
    pytest.importorskip("peft")
    from peft import LoraConfig
    from trl import SFTConfig

    SFTConfig(**_CFG.to_sft_config_kwargs())
    LoraConfig(**_CFG.to_lora_config_kwargs())
