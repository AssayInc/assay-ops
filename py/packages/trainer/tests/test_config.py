"""#176 leg 2: the SFT trainer config -- I6 (TRL SFTTrainer+LoRA, Qwen2.5-Coder-7B), I8 (pinned
model revision), eval-rigor (a TRAINING seed, never a rollout seed).

The config is a hardened, pure model: it validates the hyperparameters and maps them to TRL
``SFTConfig`` / PEFT ``LoraConfig`` kwargs WITHOUT importing the heavy training stack, so the policy
is unit-testable inside the hermetic gate.
"""

from __future__ import annotations

import pytest
from conftest import as_dict
from pydantic import ValidationError

from assayops_trainer.config import TrainerConfig

_REV = "a1b2c3d4e5f6"  # a pinned commit hash (I8) -- required, no default


def _config(**overrides: object) -> TrainerConfig:
    base: dict[str, object] = {"model_revision": _REV}
    base.update(overrides)
    return TrainerConfig.model_validate(base)


def test_defaults_encode_the_i6_dense_baseline() -> None:
    config = _config()
    assert config.model_id == "Qwen/Qwen2.5-Coder-7B-Instruct"
    assert config.lora_r == 32
    assert config.lora_alpha == 16
    assert config.assistant_only_loss is True  # tool observations masked at train time (TRL flag)


def test_the_model_revision_pin_is_required() -> None:
    # I8: pin the model by commit hash. No default -- an unpinned run must not typecheck-construct.
    with pytest.raises(ValidationError):
        TrainerConfig.model_validate({})


def test_config_is_frozen_and_forbids_extra() -> None:
    config = _config()
    with pytest.raises(ValidationError):
        TrainerConfig.model_validate({"model_revision": _REV, "sneaky": 1})
    with pytest.raises(ValidationError):
        config.lora_r = 8  # type: ignore[misc]


def test_out_of_range_hyperparameters_are_refused() -> None:
    with pytest.raises(ValidationError):
        _config(lora_r=0)
    with pytest.raises(ValidationError):
        _config(learning_rate=0)
    with pytest.raises(ValidationError):
        _config(num_train_epochs=0)


def test_lora_kwargs_map_to_peft_names() -> None:
    kwargs = as_dict(_config().to_lora_config_kwargs())
    assert kwargs["r"] == 32
    assert kwargs["lora_alpha"] == 16
    assert kwargs["task_type"] == "CAUSAL_LM"
    assert "q_proj" in kwargs["target_modules"]


def test_sft_kwargs_map_to_trl_names_and_pin_the_revision() -> None:
    kwargs = as_dict(_config(training_seed=7).to_sft_config_kwargs())
    assert kwargs["assistant_only_loss"] is True
    assert kwargs["packing"] is True
    # the TRAINING seed maps to TRL's `seed` (eval-rigor: distinct from a rollout/inference seed)
    assert kwargs["seed"] == 7
    # I8: the revision reaches from_pretrained via model_init_kwargs
    assert kwargs["model_init_kwargs"]["revision"] == _REV
