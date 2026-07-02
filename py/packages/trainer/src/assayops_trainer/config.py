"""The SFT trainer config -- I6 (TRL ``SFTTrainer`` + LoRA on Qwen2.5-Coder-7B), I8 (pinned model
revision), eval-rigor (a TRAINING seed, distinct from a rollout/inference seed).

A hardened, PURE model: it validates the hyperparameters and maps them to TRL ``SFTConfig`` / PEFT
``LoraConfig`` kwargs without importing the heavy training stack -- so the hyperparameter policy is
unit-testable inside the hermetic gate, while ``sft.run_sft`` (the only place the stack is imported)
just spreads these kwargs.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from assayops_trainer.records import JsonObject

_PositiveInt = Annotated[int, Field(gt=0)]
_PositiveFloat = Annotated[float, Field(gt=0)]
_UnitInterval = Annotated[float, Field(ge=0, lt=1)]

# Qwen2.5-Coder attention + MLP projections -- the standard LoRA target set for the family.
_QWEN_LORA_TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")

# trl 1.7 packing (bfd) force-enables padding-free flattening, and only flash-attention varlen
# kernels respect packed sample boundaries -- under the sdpa default TRL merely WARNS and packed
# samples cross-attend (silent corruption). Packing is therefore refused without one of these --
# trl 1.7.0's FLASH_ATTENTION_VARIANTS mirrored EXACTLY (a prefix match would let a non-flash hub
# kernel slip packing back onto the warn-and-train path).
_FLASH_ATTENTION_IMPLEMENTATIONS = (
    "flash_attention_2",
    "flash_attention_3",
    "kernels-community/flash-attn2",
    "kernels-community/flash-attn3",
    "kernels-community/vllm-flash-attn3",
)


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
    # OFF by default: the slice set is tiny (packing buys nothing) and turning it on requires a
    # flash-attention implementation (see _FLASH_ATTENTION_IMPLEMENTATIONS; enforced below).
    packing: bool = False
    # Passed to the weights' from_pretrained when set; None keeps transformers' own default (sdpa).
    attn_implementation: str | None = None
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

    @model_validator(mode="after")
    def _packing_requires_flash_attention(self) -> TrainerConfig:
        if self.packing and self.attn_implementation not in _FLASH_ATTENTION_IMPLEMENTATIONS:
            raise ValueError(
                "packing=True requires attn_implementation to be one of "
                f"{', '.join(_FLASH_ATTENTION_IMPLEMENTATIONS)} -- trl's padding-free "
                "flattening cross-attends packed samples under any other implementation "
                "(TRL only warns and trains on)"
            )
        return self

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

    def to_model_kwargs(self) -> JsonObject:
        """``AutoModelForCausalLM.from_pretrained`` kwargs -- the I8 pin + load policy.

        ``run_sft`` loads the model OBJECT itself so every Hub read (config + weights; the
        tokenizer separately) happens at the pinned revision -- handing trl a model string leaves
        its internal ``AutoConfig`` probe reading ``main`` unpinned. The load dtype follows the
        training precision (transformers loads float32 unless told otherwise -- ~28 GB of fp32
        weights for the 7B under ``bf16=True``).
        """
        kwargs: JsonObject = {
            "revision": self.model_revision,
            "dtype": "bfloat16" if self.bf16 else "float32",
        }
        if self.attn_implementation is not None:
            kwargs["attn_implementation"] = self.attn_implementation
        return kwargs

    def to_sft_config_kwargs(self) -> JsonObject:
        """TRL ``SFTConfig`` kwargs -- the training-seed maps to ``seed``.

        No ``model_init_kwargs``: trl only honors it for a model STRING, and ``run_sft`` passes a
        loaded model object (see ``to_model_kwargs``) precisely so no Hub read floats on ``main``.
        The tokenizer pin is ``run_sft``'s job too (trl loads the processor from ``main`` when one
        is not passed in).
        """
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
        }
