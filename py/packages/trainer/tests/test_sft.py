"""#176 leg 2: the TRL SFT+LoRA harness -- lazy-imported so the heavy stack stays out of the gate.

The stack (trl/peft/transformers/datasets/accelerate/torch) is intentionally NOT a workspace dep, so
in the hermetic gate ``run_sft`` fails with a clear pointer to the pinned requirements file rather
than a raw ModuleNotFoundError. When the stack IS present, the config's kwargs must construct the
REAL ``SFTConfig`` / ``LoraConfig`` -- the grounding check that our kwarg names match the API.
"""

from __future__ import annotations

import inspect
import sys
import types
from pathlib import Path

import pytest

from assayops_trainer.config import TrainerConfig
from assayops_trainer.sft import run_sft

_CFG = TrainerConfig.model_validate({"model_revision": "a1b2c3d4"})


def test_run_sft_without_the_training_stack_points_at_the_requirements(tmp_path: Path) -> None:
    with pytest.raises(ImportError, match="train-requirements"):
        run_sft(_CFG, tmp_path / "sft.jsonl")


def test_run_sft_pins_the_tokenizer_and_wires_the_trainer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The lazy-import seam is the injection point (the heavy stack stays out of the gate): fake
    # modules record the wiring. The load-bearing assertion is the TOKENIZER PIN -- trl 1.7 loads
    # the processor from `main` when given a model string, and the chat template it carries gates
    # the assistant-mask template swap, so run_sft must load it at the pinned revision itself.
    calls: dict[str, object] = {}

    class FakeTokenizer:
        pass

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(model_id: str, *, revision: str) -> FakeTokenizer:
            calls["tokenizer"] = (model_id, revision)
            return FakeTokenizer()

    class FakeModel:
        pass

    class FakeAutoModel:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs: object) -> FakeModel:
            calls["model"] = (model_id, kwargs)
            return FakeModel()

    class FakeTrainer:
        def __init__(self, **kwargs: object) -> None:
            calls["trainer_kwargs"] = kwargs

        def train(self) -> None:
            calls["trained"] = True

        def save_model(self, output_dir: str) -> None:
            calls["saved_to"] = output_dir

    def fake_load_dataset(kind: str, data_files: str, split: str) -> str:
        calls["dataset"] = (kind, data_files, split)
        return "fake-dataset"

    datasets_mod = types.ModuleType("datasets")
    datasets_mod.load_dataset = fake_load_dataset  # type: ignore[attr-defined]
    peft_mod = types.ModuleType("peft")
    peft_mod.LoraConfig = lambda **kwargs: ("lora-config", kwargs)  # type: ignore[attr-defined]
    trl_mod = types.ModuleType("trl")
    trl_mod.SFTConfig = lambda **kwargs: ("sft-config", kwargs)  # type: ignore[attr-defined]
    trl_mod.SFTTrainer = FakeTrainer  # type: ignore[attr-defined]
    transformers_mod = types.ModuleType("transformers")
    transformers_mod.AutoTokenizer = FakeAutoTokenizer  # type: ignore[attr-defined]
    transformers_mod.AutoModelForCausalLM = FakeAutoModel  # type: ignore[attr-defined]
    for name, module in {
        "datasets": datasets_mod,
        "peft": peft_mod,
        "trl": trl_mod,
        "transformers": transformers_mod,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    out = run_sft(_CFG, tmp_path / "sft.jsonl")

    assert calls["tokenizer"] == ("Qwen/Qwen2.5-Coder-7B-Instruct", "a1b2c3d4")
    # The model is loaded HERE at the pinned revision -- handing trl a model string would leave
    # its internal AutoConfig probe reading `main` unpinned.
    assert calls["model"] == (
        "Qwen/Qwen2.5-Coder-7B-Instruct",
        {"revision": "a1b2c3d4", "dtype": "bfloat16"},
    )
    trainer_kwargs = calls["trainer_kwargs"]
    assert isinstance(trainer_kwargs, dict)
    assert isinstance(trainer_kwargs["processing_class"], FakeTokenizer)
    assert isinstance(trainer_kwargs["model"], FakeModel)
    assert trainer_kwargs["train_dataset"] == "fake-dataset"
    assert calls["dataset"] == ("json", str(tmp_path / "sft.jsonl"), "train")
    assert calls["trained"] is True
    assert calls["saved_to"] == _CFG.output_dir
    assert out == Path(_CFG.output_dir)


def test_config_kwargs_construct_the_real_trl_and_peft_configs() -> None:
    # Skips in the hermetic gate (stack absent); runs where a training env installed it, proving the
    # kwarg names in config.py match the real TRL/PEFT API (no model download involved).
    pytest.importorskip("trl")
    pytest.importorskip("peft")
    from peft import LoraConfig
    from trl import SFTConfig, SFTTrainer

    SFTConfig(**_CFG.to_sft_config_kwargs())
    LoraConfig(**_CFG.to_lora_config_kwargs())
    # the tokenizer pin rides in through processing_class -- assert the real API accepts it
    assert "processing_class" in inspect.signature(SFTTrainer.__init__).parameters
