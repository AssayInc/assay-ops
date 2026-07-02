"""The TRL ``SFTTrainer`` + LoRA harness (I6) -- the runner for the rejection-sampled slice set.

The heavy training stack (trl / peft / transformers / datasets / accelerate / torch) is
lazy-imported; its minimum versions live in ``train-requirements.txt`` (frozen to exact hashes at
run time), kept OUT of the workspace so the hermetic ``bun run verify`` gate never resolves torch. A
real run needs a CUDA GPU + a pinned model
revision (I8); this harness only wires the config to the API -- ``config.py`` owns the (unit-tested)
hyperparameter policy. SFT-only (DECISIONS: no RL/GRPO loop before the proof).
"""

from __future__ import annotations

from pathlib import Path

from assayops_trainer.config import TrainerConfig

_MISSING_STACK = (
    "the SFT training stack (trl, peft, transformers, datasets, accelerate, torch) is not "
    "installed -- it is intentionally kept out of the hermetic verify gate. Install the training "
    "stack into a training env (needs a CUDA GPU for a real run): "
    "`uv pip install -r py/packages/trainer/train-requirements.txt`."
)


def run_sft(config: TrainerConfig, dataset_path: Path) -> Path:
    """SFT+LoRA-train ``config.model_id`` on the ETL's ``sft.jsonl``; return the output dir.

    Raises ``ImportError`` (with a pointer to ``train-requirements.txt``) when the training stack is
    absent -- the expected state inside the hermetic gate.
    """
    try:
        from datasets import load_dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import SFTConfig, SFTTrainer
    except ImportError as error:
        raise ImportError(_MISSING_STACK) from error

    dataset = load_dataset("json", data_files=str(dataset_path), split="train")
    # I8: EVERY Hub read happens at the pinned revision, so both artifacts are loaded HERE --
    # handing trl a model string leaves its internal AutoConfig probe reading `main` unpinned,
    # and it loads the processor from `main` too. The tokenizer's chat template both gates trl's
    # assistant-mask template swap (byte-exact match against the stock Qwen2.5 template) and
    # defines tokenization, so a template change upstream would silently alter a "pinned" run.
    tokenizer = AutoTokenizer.from_pretrained(config.model_id, revision=config.model_revision)
    model = AutoModelForCausalLM.from_pretrained(config.model_id, **config.to_model_kwargs())
    trainer = SFTTrainer(
        model=model,
        args=SFTConfig(**config.to_sft_config_kwargs()),
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=LoraConfig(**config.to_lora_config_kwargs()),
    )
    trainer.train()
    trainer.save_model(config.output_dir)
    return Path(config.output_dir)
