"""The SFT trainer config -- I6 (TRL ``SFTTrainer`` + LoRA on Qwen2.5-Coder-7B), I8 (pinned model
revision), eval-rigor (a TRAINING seed, distinct from a rollout/inference seed).

A hardened, PURE model: it validates the hyperparameters and maps them to TRL ``SFTConfig`` / PEFT
``LoraConfig`` kwargs without importing the heavy training stack -- so the hyperparameter policy is
unit-testable inside the hermetic gate, while ``sft.run_sft`` (the only place the stack is imported)
just spreads these kwargs.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from assayops_trainer.records import JsonObject

_PositiveInt = Annotated[int, Field(gt=0)]
_PositiveFloat = Annotated[float, Field(gt=0)]
_UnitInterval = Annotated[float, Field(ge=0, lt=1)]

# Qwen2.5-Coder attention + MLP projections -- the standard LoRA target set for the family.
_QWEN_LORA_TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


class TrainerConfig(BaseModel):
    """Hyperparameters for one SFT+LoRA run over the rejection-sampled slice set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    # I8: pin the model by COMMIT HASH -- required (no default) AND constrained to a hex sha, so a
    # moving ref ("main"), a mutable tag, or "" is refused; only a real commit pin constructs.
    model_revision: Annotated[str, Field(pattern=r"^[0-9a-f]{7,40}$")]

    lora_r: _PositiveInt = 32
    lora_alpha: _PositiveInt = 16
    lora_dropout: _UnitInterval = 0.05
    lora_target_modules: tuple[str, ...] = _QWEN_LORA_TARGETS

    learning_rate: _PositiveFloat = 2e-4
    num_train_epochs: _PositiveFloat = 1.0
    per_device_train_batch_size: _PositiveInt = 1
    gradient_accumulation_steps: _PositiveInt = 8
    max_length: _PositiveInt = 4096
    packing: bool = True
    # Mask everything but assistant turns at train time (tool observations included) -- TRL's own
    # mechanism, not a hand-rolled mask (the ETL emits faithful messages; TRL does the masking).
    assistant_only_loss: bool = True
    bf16: bool = True
    gradient_checkpointing: bool = True
    # A TRAINING seed (weight init / data order). eval-rigor: never conflated with a rollout/
    # inference seed -- those live in the eval harness (leg 3), not here.
    training_seed: int = 0
    output_dir: str = "sft-output"
    report_to: str = "none"

    def to_lora_config_kwargs(self) -> JsonObject:
        """PEFT ``LoraConfig`` kwargs."""
        return {
            "r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "target_modules": list(self.lora_target_modules),
            "task_type": "CAUSAL_LM",
            "bias": "none",
        }

    def to_sft_config_kwargs(self) -> JsonObject:
        """TRL ``SFTConfig`` kwargs -- the training-seed maps to ``seed``; the pinned revision (I8)
        reaches ``from_pretrained`` via ``model_init_kwargs``."""
        return {
            "output_dir": self.output_dir,
            "learning_rate": self.learning_rate,
            "num_train_epochs": self.num_train_epochs,
            "per_device_train_batch_size": self.per_device_train_batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "max_length": self.max_length,
            "packing": self.packing,
            "assistant_only_loss": self.assistant_only_loss,
            "bf16": self.bf16,
            "gradient_checkpointing": self.gradient_checkpointing,
            "seed": self.training_seed,
            "report_to": self.report_to,
            "model_init_kwargs": {"revision": self.model_revision},
        }
