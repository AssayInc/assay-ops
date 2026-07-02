# #176 follow-up — review hardening: trainer run-path fixes + report/ETL honesty guards

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md + the PR + GitHub #176.
> **For Claude:** REQUIRED SUB-SKILL: superpowers:test-driven-development per task; verification-before-completion before claiming done.

**Goal:** Fix the findings from the post-merge six-lens review of PR #180 (evals) + PR #182 (trainer)
before the first SFT run consumes either package. Three run-path criticals (all TRL-semantic-layer,
wheel-source-verified against trl 1.7.0 / transformers 5.12.1) + the report/ETL honesty-guard cluster
(multi-model confirmed: Claude specialists + Codex xhigh) + the doc corrections. No behavior change to
the trust seam itself — every fix is inside the already-licensed pre-T0 posture.

**Branch:** `176-review-hardening` (off main). Focused PR (`Advances #176`, never Closes).

## Fixes (each test-first)

### Trainer (`py/packages/trainer`)
- [x] **messages.py — tool-call `arguments` str→dict.** `messages_to_openai` emits OpenAI wire-format
      JSON *strings*; TRL 1.7.0's conversational path renders `tool_call.arguments | tojson`, so string
      arguments double-encode into every training target (silent corruption of the tool-call syntax the
      SFT teaches). Parse each `tool_calls[*].function.arguments` back to a dict (TRL's documented
      conversational format); an unparseable arguments string fails closed (ValueError).
- [x] **config.py — packing requires flash-attention; load dtype.** `packing=True` (bfd) force-enables
      padding-free flattening, sample-isolated ONLY under flash-attn kernels; TRL warns and trains on
      under the sdpa default (cross-sample attention). Default `packing=False` for the slice (tiny set —
      packing buys nothing) + new `attn_implementation: str | None`, with a model_validator refusing
      `packing=True` unless it is one of trl 1.7.0's exact FLASH_ATTENTION_VARIANTS. Final mechanism
      (post-Codex): `to_model_kwargs()` carries revision + dtype (derived from `bf16`) +
      attn_implementation for the model load; `to_sft_config_kwargs()` carries NO `model_init_kwargs`.
- [x] **sft.py — pin every Hub read.** trl 1.7.0 loads the tokenizer/processor from `main` (no
      revision) when given a model string, and its internal `AutoConfig` probe reads `main` too. Final
      mechanism (post-Codex): `run_sft` loads BOTH `AutoTokenizer.from_pretrained(model_id,
      revision=...)` (passed as `processing_class=` — the chat template gates the assistant-mask
      template swap) AND the model object via `AutoModelForCausalLM.from_pretrained(model_id,
      **to_model_kwargs())`. Real-API check: `processing_class` in `SFTTrainer.__init__`'s signature
      (importorskip); wiring locked by a fake-module test at the lazy-import seam.
- [x] **etl.py — admission + accounting hardening.** (a) `_require_reproduced_grade` also requires
      `metadata["reward"] == 1` (a CORRECT with contradictory metadata is refused — one more shape check
      on the pre-T0 stand-in); (b) `held_out_ids` becomes REQUIRED on `build_sft_dataset`/`build_and_write`
      (the fail-open `frozenset()` default contradicted the "FAILS CLOSED on any appearance" docstring —
      an explicit empty set at the call site is a documented operator decision); (c) `_verifier_runs`
      excludes `bool` (bool subclasses int — a `true` in a foreign log fabricated `verifier_runs: 1`);
      (d) `build_and_write` refuses a zero-example dataset (never writes a no-op `sft.jsonl`).

### Evals (`py/packages/evals`)
- [x] **report.py — status gate.** `directional_delta` refuses a non-`"success"` log (mirrors the ETL;
      an interrupted run must not yield a delta).
- [x] **report.py — limit triage.** A limit-hit sample with NO verifier score is counted `errored`
      (incomplete), not a whole-report crash with a misleading message. A limit-hit sample WITH a score
      stays a settled grade (deployed state was graded; an unfinished fix deserves its 0).
- [x] **report.py — error bracketing.** `pass_rate_lower_bound` counts errored rollouts in the
      denominator too (pre-T0 an agent-wedged substrate can surface as a scoring cancel/error, not just
      a quarantine — the bracket must cover both dodge shapes), and a second divergence warning fires
      when error rates differ materially (same 0.15 threshold as quarantine divergence).

### Docs
- [x] trainer README: `(trl ≥ 0.13)` is false for `assistant_only_loss` (that floor is peft's) → `trl ≥ 1.7`
      + describe the REAL trl 1.7 mechanism (vendored Qwen2.5 training-template swap on byte-exact match;
      loud ValueError/RuntimeError otherwise — NOT a silent no-op).
- [x] train-requirements.txt: floors were jointly unsatisfiable (trl 1.7.0 itself requires
      transformers>=4.56.2, datasets>=4.7.0, accelerate>=1.4.0) → raise to trl's own minimums; reword the
      assistant_only_loss comment to the template-swap mechanism.
- [x] ISSUES.md: correct the prior "mask silently no-ops" deferred note (trl 1.7 fails loud); record this
      PR + the remaining deferred minors. PROGRAM.md: status note.

## Out of scope (deliberate)
- Min-K enforcement in ETL/report (goes with the #78 KMS-signed join — recorded in ISSUES.md).
- Corpus-side compose validation / symlink / colon-in-path admission guards (leg-1 corpus-contract work,
  already tracked in ISSUES.md).
- report `ModelSlice.pass_rate` zero-guard, exception taxonomy (`ContaminationError`), dedup'd exclusion
  counters, private `EvalError` test import — review minors, listed in the PR body, not blocking the run.

## Codex xhigh re-review findings (all fixed)
- [x] **sft.py — model string left trl's `AutoConfig` probe unpinned** (P2): `run_sft` now loads the
      model OBJECT itself via `to_model_kwargs()` (revision + dtype + attn) and drops
      `model_init_kwargs` from `SFTConfig` (trl only honors it for a string).
- [x] **etl.py — `reward == 1` accepted `True`** (P2): the shape check now requires a non-bool int.
- [x] **config.py — `dtype` contradicted `bf16=False`** (P3): load dtype derived from `bf16`.
- [x] **config.py — flash-attn guard rejected kernels-community variants** (P3): accepted by prefix.

## Verification
- [x] `bun run verify` green (all packages; hermetic — no new deps in the gate).
- [x] Codex gpt-5.5 xhigh review of the diff + re-review after fixes (standing practice).
