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
    # packing is OFF by default: trl 1.7 bfd packing force-enables padding-free flattening, which
    # is sample-isolated only under flash-attn; the slice set is tiny, so packing buys nothing.
    assert config.packing is False
    assert config.attn_implementation is None


def test_the_model_revision_pin_is_required() -> None:
    # I8: pin the model by commit hash. No default -- an unpinned run must not typecheck-construct.
    with pytest.raises(ValidationError):
        TrainerConfig.model_validate({})


def test_the_model_revision_must_be_a_commit_hash() -> None:
    # I8 means a COMMIT hash, not any string: a moving branch/tag or empty defeats the pin while the
    # manifest still claims it, so the config refuses them.
    for bad in ("", "main", "v1.0", "HEAD"):
        with pytest.raises(ValidationError):
            TrainerConfig.model_validate({"model_revision": bad})
    # a real hex sha (short or full) is accepted
    assert TrainerConfig.model_validate({"model_revision": "a1b2c3d"}).model_revision == "a1b2c3d"


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
    assert kwargs["packing"] is False
    # the TRAINING seed maps to TRL's `seed` (eval-rigor: distinct from a rollout/inference seed)
    assert kwargs["seed"] == 7
    # I8: the revision reaches the WEIGHTS' from_pretrained via model_init_kwargs (the tokenizer
    # pin is run_sft's job -- trl loads the processor from `main` unless one is passed in).
    assert kwargs["model_init_kwargs"]["revision"] == _REV
    # trl 1.7 loads float32 unless told otherwise -- ~28 GB of fp32 weights for the 7B is
    # inconsistent with bf16=True training; the load dtype must match.
    assert kwargs["model_init_kwargs"]["dtype"] == "bfloat16"


def test_packing_requires_a_flash_attention_implementation() -> None:
    # trl 1.7 packing (bfd) force-enables padding-free flattening, which respects sample boundaries
    # ONLY under a flash-attention implementation; under the sdpa default TRL merely WARNS and
    # packed samples cross-attend. The config refuses the silent-corruption combination.
    with pytest.raises(ValidationError):
        _config(packing=True)

    config = _config(packing=True, attn_implementation="flash_attention_2")
    kwargs = as_dict(config.to_sft_config_kwargs())
    assert kwargs["packing"] is True
    assert kwargs["model_init_kwargs"]["attn_implementation"] == "flash_attention_2"


def test_attn_implementation_maps_to_model_init_kwargs_only_when_set() -> None:
    with_fa = as_dict(_config(attn_implementation="flash_attention_2").to_sft_config_kwargs())
    assert with_fa["model_init_kwargs"]["attn_implementation"] == "flash_attention_2"
    # omitted when None so transformers keeps its own default selection (sdpa)
    default = as_dict(_config().to_sft_config_kwargs())
    assert "attn_implementation" not in default["model_init_kwargs"]
