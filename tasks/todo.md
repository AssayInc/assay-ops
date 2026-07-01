# #176 leg 3 — Inspect-AI eval harness (`py/packages/evals`) Implementation Plan

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md + the PR + GitHub #176.
> **For Claude:** REQUIRED SUB-SKILL: superpowers:test-driven-development per task; superpowers:verification-before-completion before claiming done.

**Goal:** The Inspect-AI harness leg of the pre-T0 directional slice (#176): the deploy-verifier as
an Inspect `Scorer` around the shipped `assayops_verifier.verify`, a private-corpus dataset loader,
the drift-slice `Task` builder, and the R1-framed directional pass-rate-delta report — so the
15 × 3-seed LocalStack-graded base-vs-SFT runs have a harness.

**Architecture:** New `py/packages/evals` (`assayops_evals`), consuming the shipped verifier (E2),
Terraform adapter (E3-2), replay verdicts (E6-2), and contracts by source path (the repo's
virtual-member convention). The scorer maps `VerifyVerdict` → Inspect `Score`
(`Reproducible(1)`→CORRECT, `Reproducible(0)`/`FailedClosed`→INCORRECT, `Quarantined`→
`Score.unscored()`; corpus/config errors PROPAGATE). Tasks + goldens live in the PRIVATE corpus dir
(I11 — never committed); in-repo tests use synthetic fixtures only. Per-sample Docker-compose
sandbox = agent container + its own LocalStack service; the scorer runs in the eval process
(outside the sandbox) and reads deployed state via boto3 Cloud Control against the sample's
LocalStack endpoint (ephemeral published port, discovered via the sandbox connection — injected
seam, hermetically tested).

**Tech Stack:** inspect-ai (pinned), pydantic v2, boto3 (reader construction only), pytest,
mypy --strict + disallow_any_explicit, ruff.

**Trust framing (write-isolated-verifier / eval-rigor):** pre-T0 the agent and LocalStack share a
compose network — no account A/B split. Allowed per docs/priorities.md P1 (no adversarial policy,
no external claim; never published — R1). The report artifact hard-codes the
"PRE-T0 DIRECTIONAL — NOT the E13 proof" framing so the number can't be innocently reused.
Scorer inputs (task_id, seed, scope, registries) are harness-owned (sample metadata written by the
dataset loader from the validated TaskSpec) — never agent-supplied. The verifier never executes in
the agent's container; grading runs in the eval process via `verify()` only (the sole
reward-emitting entry).

---

## Task 0: Grounding + package scaffold
- [x] Ground #176 (body, comments=none, timeline), #61/#155/#78/#76/#67 siblings, DECISIONS.md §1/§3/§6/§8, priorities.md, ARCHITECTURE.md, brain (impl-plan E12/E13 lines), Inspect docs (custom-scorers/sandboxing/tasks/metrics), write-isolated-verifier + eval-rigor skills.
- [x] Comment the grounding reconciliation + leg plan on #176.
- [x] Scaffold `py/packages/evals`: `pyproject.toml` (deps: `inspect-ai` pinned, `pydantic>=2.10`, `boto3>=1.40`; mypy strict + `disallow_any_explicit` + sibling `follow_imports=silent` overrides mirroring verifier), thin `package.json` (`@assayops/py-evals`, workspace deps on py-verifier/py-adapter-terraform/py-diff-ir/py-contracts/py-replay), `turbo.json` (`dependsOn ^typecheck/^test`), `src/assayops_evals/__init__.py`.
- [x] `bun install` + `uv sync` → BOTH lockfiles updated (lessons: bun-lock-and-uv-lock-after-adding-a-py-package); verify `bun install --frozen-lockfile` passes.

## Task 1: Scorer — verdict → Score mapping (the moat seam)
Files: `src/assayops_evals/scorer.py`, `tests/test_scorer.py`.
- [x] RED: tests with a synthetic golden registry + fake reader (recording fake proving read-only ops only, mirroring verifier tests):
      clean deploy → CORRECT; property drift → INCORRECT; extra resource → INCORRECT;
      FailedClosed (unreadable) → INCORRECT + `verdict:"failed_closed"` metadata;
      Quarantined → unscored (excluded from metrics); corpus error (unknown task) PROPAGATES;
      task identity read from sample metadata (agent text cannot override).
- [x] GREEN: `deploy_verifier_scorer(corpus, reader_factory, runs)` — `@scorer(metrics=[accuracy(), stderr()])`; re-validate TaskSpec from metadata (fail closed); call `verify()`; map verdict.
- [x] Negative-control the load-bearing assertions (disable mapping → tests fail).

## Task 2: Private-corpus loader (I11 residency, fail closed)
Files: `src/assayops_evals/corpus.py`, `tests/test_corpus.py` (+ synthetic corpus fixture under `tests/fixtures/`).
- [x] RED: loads `tasks/*.json` → validated `TaskSpec`s; loads `corpus.py` module (GoldenRegistry/ReadScope/BridgeRegistry, fail closed if missing/malformed); duplicate task_id → error; malformed spec → error; per-task sandbox assets (files/setup/compose) resolved.
- [x] GREEN: `load_corpus(corpus_dir)` → frozen `Corpus` object.
- [x] Residency guard: loading a corpus dir inside this repo fails closed unless the test-only flag is set (protects I11).

## Task 3: Task builder + dataset mapping
Files: `src/assayops_evals/task.py`, `tests/test_task.py`.
- [x] RED: TaskSpec → `Sample` (input=description, metadata=spec+seed, files/setup from corpus); task builder wires solver (react agent + bash/text_editor), scorer, `epochs`, sandbox=(docker, corpus compose), limits.
- [x] GREEN: `drift_slice_task(...)` `@task` factory, params for corpus_dir/epochs/limits.

## Task 4: LocalStack endpoint discovery + reader factory (injected seam)
Files: `src/assayops_evals/readers.py`, `tests/test_readers.py`.
- [x] RED: reader factory builds per-region `DeployedStateReader` map from `ReadScope` + endpoint (boto3 client with endpoint_url, test creds, region); endpoint discovery parses the sandbox connection/port output (injected exec — no docker in tests); malformed discovery output fails closed.
- [x] GREEN: `localstack_reader_factory(...)`, `discover_localstack_endpoint(...)`.

## Task 5: Directional report (R1-framed)
Files: `src/assayops_evals/report.py`, `tests/test_report.py`.
- [x] RED: two eval logs (synthetic) → per-model pass rate, delta, n/epochs/unscored counts; report text contains the hard-coded PRE-T0/NOT-the-proof framing; quarantined excluded from the rate.
- [x] GREEN: `directional_delta(base_log, sft_log)` + `render_report(...)`.

## Task 6: Gate + docs + reviews
- [x] `bun run verify` green — 32/32 tasks (41 evals tests).
- [x] Package README/docstring: the pre-T0 trust caveat + run recipe (`inspect eval … -T corpus_dir=…`).
- [x] Update PROGRAM.md (Right Now + Recently Landed) + ISSUES.md if residuals.
- [ ] `/review` + Codex gpt-5.5 xhigh adversarial review (diverse-lens: forge + crash + design) → re-review fixed code to convergence.
- [ ] PR `Advances #176` (never Closes — umbrella), diff scoped to this leg.

## Out of scope (tracked, not built here)
- Corpus leg (15 TF drift tasks): private store (#76 unbuilt), informed by #61 (open P0), per-type LocalStack Cloud Control smoke gate — comment on #176.
- Trainer leg (TRL SFT + LoRA + ETL): follow-up PR; ETL consumes this harness's logs (#78 shape minus KMS — no ledger yet).
- #155 item 3 (LocalStack adapter↔golden round-trip test) — owned by #155.
- #46 (§6 determinism gate over the real corpus in the Scorer) — E13/Phase 2-3, blocked by #14/#45.
