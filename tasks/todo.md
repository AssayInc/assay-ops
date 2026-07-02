# #176 leg 1 — the corpus: private store + ~15 TF drift tasks + per-type gates + run enablement

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md + the PR + GitHub #176.
> **For Claude:** REQUIRED SUB-SKILL: superpowers:test-driven-development per code task;
> verification-before-completion before claiming done.

**Goal:** the last unbuilt part of #176 — leg 1 (the corpus) plus run enablement. Legs 2+3 are built
and hardened; the remaining gate to a directional number is: the minimal private-store decision,
~15 Terraform drift tasks authored against the #155 contract, the per-type LocalStack gates beyond
`AWS::S3::Bucket`, the two leg-1-owned admission guards (ISSUES.md), then the runs (rollouts → ETL →
SFT → base-vs-SFT delta).

**Grounding (reconciled):** issue #176 body + 4 comments (grounding reconciliation, #61 substrate
answer, #155 contract, leg-2 status) · DECISIONS.md I6/I8/I11/§8 · priorities.md P1 item 4 (R1:
directional only, never published) · PROGRAM.md "Right Now" · ISSUES.md leg-1 deferred items ·
code contracts read first-hand (`load_corpus`, `drift_slice`, `readers`, `read_scope`,
`assert_golden_readable`, adapter `normalize`/`BridgeRegistry`, roundtrip smoke). No blocked-by on
the issue; #61 + #155 both landed.

**Store decision (founder call, synthesized):** author into an out-of-repo local dir
(`~/assay-private/corpus/pre-t0-slice/` — I11: `_require_out_of_repo` refuses ANY git-repo ancestor,
so "gitignored in-repo" is not even loadable), mirrored to a **private HF dataset** when the founder
provides HF access (their message anticipates this). Record on the issue.

## A. Committable (the PR — no task/golden content, engine + gates only)

- [x] **A1. Probe LocalStack CC shapes** (scratchpad, licensed image): SQS Queue / SNS Topic /
      SSM Parameter / DynamoDB Table — get/list support, `assayops:address` tag return shape,
      server-defaulted posture. Pick 2–3 new types minimizing adapter change (tag shape!).
- [x] **A2. TDD: `load_corpus` compose validation** (ISSUES.md leg-1 item): parse `compose.yaml`,
      require a `localstack` service publishing container port 4566 + a `default` service; fail
      closed (`CorpusError`) otherwise.
- [x] **A3. TDD: `_sandbox_files` guards** (ISSUES.md leg-1 item): a symlinked corpus asset and a
      `:` in a file key fail closed (`CorpusError`), never silently dropped/passed.
- [x] **A4. Per new type (founder per-type gate):** adapter `TypeBridge` registration with real-schema
      `readOnlyProperties`/`tagProperty` (+ tag-shape support only if a chosen type needs it, TDD)
      + `infra-local` read smoke (tag return) + grade round-trip posture pin (golden = declared
      constants; negative control included). Types NOT probed green do not enter the corpus.
- [x] **A5. Runbook** — the three runs (rollout collection, ETL+SFT, base-vs-SFT eval ×3 seeds +
      report), store layout, LOCALSTACK_AUTH_TOKEN handling, R1 framing. Smallest home that fits
      (evals/trainer READMEs + a short docs page only if genuinely cross-package).
- [x] **A6. PROGRAM.md / ISSUES.md** in-PR; issue comment: store decision + leg-1 grounding.

## B. Private store (out-of-repo; NEVER committed — I11)

- [x] **B1. Corpus skeleton:** `compose.yaml` (workbench `default` + per-sample `localstack` with
      pinned licensed image, ports "4566", auth token from host env) + workbench image (terraform +
      provider mirror + aws cli + inspect-tool-support) + `corpus.py` (REGISTRY / READ_SCOPE /
      BRIDGE_REGISTRY as needed).
- [x] **B2. Author ~15 tasks** across the proven types × drift categories (modified property /
      removed resource / added-extra resource / tag drift), each `task.json` + `setup.sh` (deploy
      baseline → inject drift out-of-band) + `files/**` (the Terraform config = the intent).
      Goldens declare server-defaulted posture (#155). Fixed deterministic names (per-sample
      LocalStack; no cross-sample collision).
- [x] **B3. Per-task validation** (private script, spike-output rule — stays in the store):
      admission via `load_corpus` → deploy+drift → grade 0 → apply the reference fix → grade 1,
      against local LocalStack through the production read→normalize→grade path.
- [x] **B4. End-to-end plumbing run:** `inspect eval` drift_slice with `mockllm/model` on 1–2 tasks —
      sandbox comes up, setup runs, scorer grades through `verify()` (INCORRECT expected) — proves
      compose/endpoint-discovery/scorer wiring without model spend.
- [ ] **B5. Mirror to private HF dataset** (needs founder HF access/token).

## C. The runs (converge here; GPU/HF-gated — surface exact needs to founder)

- [ ] **C1. Rollout collection:** base Qwen2.5-Coder-7B-Instruct over the corpus (epochs>1) →
      graded logs. Model endpoint: ollama local or HF — founder call on spend.
- [ ] **C2. ETL → `sft.jsonl`** (held_out_ids explicit) → **SFT run** (TRL harness; CUDA — HF Jobs
      or founder GPU box; freeze exact pins + model_revision at provision, I8).
- [ ] **C3. Eval:** base vs SFT ×3 seeds × ~15 tasks, LocalStack-graded → `render_report` →
      one-paragraph read on #176.

## Reviews (before PR merge-ready)
- [ ] Two adversarial reviews: Codex gpt-5.5 xhigh (review + re-review to convergence on the diff)
      + a diverse-lens Workflow pass (trust-seam / correctness / craft). `/review` gate.
- [ ] `bun run verify` green; smokes green against local LocalStack.

## Scope guards
- No new trust infra (issue guardrail); smallest change; every changed line traces to leg 1.
- Never commit tasks/goldens/trajectories (I11) — in-repo fixtures synthetic only.
- The number is R1-scoped: directional, never published.
