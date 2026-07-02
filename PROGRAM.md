# Program State

Project state + handoff for humans, engineers, and AI agents. Read this before non-trivial work.
Keep it concise (see `CLAUDE.md`/`AGENTS.md` → **Program State**).

## Right Now

- **Sequencing is now governed by `docs/priorities.md` (set 2026-07-01): evidence + the team before
  architecture** (it wins over the board on what-first). P0 = the Henry scout note (E15-2, founder),
  close the RL/eval seat (the real T0 gate; the board's "E15-3 = Done" is stale), and the **#61**
  LocalStack↔real-CFN drift/unit-economics spike — **RESOLVED** (PR #177; see Recently Landed: R3
  substrate answer, ~12× wall-clock ratio, LocalStack grading substrate-sound for the slice). P1 =
  the **#176 pre-T0 directional slice** (three legs, focused PRs; NOT the E13 proof — LocalStack-
  graded, never published, R1-scoped): **all three legs are BUILT.** Legs 2 (trainer) + 3 (Inspect
  harness) landed earlier and were hardened post-merge (the six-lens review follow-up PR; deferred
  remainder in `ISSUES.md`). **Leg 1 (the corpus) is AUTHORED + VALIDATED** (see Recently Landed):
  the private store is a local out-of-repo dir (`~/assay-private/corpus/pre-t0-slice/`; a private
  HF dataset is the durable mirror once org HF access is set up — the resolved founder store call;
  **NOT #76**, which stays `blocked_by #52`/E8 = P2-frozen), holding **15 Terraform drift tasks
  over the three per-type-gated types** (`AWS::S3::Bucket` + the newly gated
  `AWS::IAM::Role`/`AWS::KMS::Key`; SNS/SSM/SQS/DynamoDB/Logs all FAIL the CC-read/tag-return gate
  on the pinned LocalStack image — probed empirically), each validated end-to-end through the
  production `verify()` closed-world path (drifted → 0, reference fix → 1, K-run reproducible).
  **The runs RAN (2026-07-02) and the directional number is in — flat: held-out +0.0 points
  (6/9 both arms), trained −2.8 (13/36 → 12/36); zero quarantined/errored across ~200 graded
  episodes (all K=3-reproducible).** The honest read (recorded on the issue): the MACHINE is
  validated end-to-end (corpus → rollouts via a vLLM-on-HF-Jobs endpoint with `force_tool_calls`
  → held-out-split ETL → TRL SFT+LoRA on HF Jobs → one-engine base+adapter delta), and the
  binding constraint is corpus scale + hard-task trajectory yield (top-up sampling: 1/40), NOT
  trust infra — the P2 "corpus + proof" dial. Artifacts + pins in the private HF dataset
  (`AssayInc/pre-t0-drift-corpus`, `runs/`); adapter private
  (`AssayInc/pre-t0-qwen25-coder-7b-sft`). The Freeze list (more trust infra now)
  holds until the seat + the (now-informed) go/no-go + the Henry reply.
- **Python-first core is LOCKED (E17 decision landed, PR #118; epic #113 stays open tracking the follow-ups).** The proof-critical core is **Python**
  (verifier, diff/reward core, IaC adapters, reward ledger, deterministic replay, the OpenEnv env-server,
  episode orchestration in **`py/packages/*`**); **TypeScript** is the public/web/tooling surface
  (`@assayops/contracts` binding, `assay-web`, dashboards, npm consumers). The **trust floor is preserved
  untouched** (§1 account split, §2 locked decisions, §5 15-vector bar, §6 eval rigor). The **OpenEnv
  reward-boundary invariant** is locked **non-waivable** (§8): the A-side env-server never computes the
  graded reward — the **verifier (T1) computes** `reward∈{0,1}`, the **reward ledger (T4) signs +
  WORM-writes** it, joined by `trajectory_id`; the trainer trains on **that**, never the env's `step()`.
- **E2–E7 (#3–#8) are re-scoped to Python and gated** on the feasibility spikes: **#114 (OpenEnv/TRL,
  gates E5) LANDED — GO on OpenEnv-native Python → E5/#6 unblocked** (PR #121, `b91da87`); **#115 (ledger
  rfc8785/KMS/Object-Lock, gates E4) LANDED — GO** (PR #122); **#80 (boto3 read coverage, gates E2/E3) LANDED —
  GO (with conditions)** (Terraform read path = Cloud Control `GetResource`/`ListResources` only; unreadable =
  FAIL-CLOSED; detecting *extra* resources needs a **closed-world** predicate via **T7** SCP create-allow-lists —
  reads alone can't close vector #15); **account infra T7 (P1-BLOCKING — now also owns the closed-world
  allow-list)** + LocalStack remain — **no proof-critical code starts on stale TS assumptions**.
  The contracts spine (**E1 #2**) is **complete** (planned deliverables #26–#29 all landed),
  **reframed Python-signer↔TS-consumer**: **#28** (JCS + golden vectors) and **#29** (the CI
  regenerate-and-diff parity gate) landed; the review-surfaced codegen-hardening follow-up (**#140**)
  **landed** (PR #144).
- **Type checker:** `mypy --strict` is the bridge — now also **`disallow_any_explicit`** + ruff `ANN401` (the Python `Any` ban mirroring the TS `any` ban; `object` is the `unknown` equivalent); **`ty`** (Astral) is the committed target, adopted at
  E2's first step once it is Stable + Pydantic-clean (**#119**). **Other tooling follow-ups:** **#132
  (Python structlog logger — landed; carved from #116)**, **#116 (boto3 skill + LocalStack boto3 read smoke
  + language flip — landed, PR #134)**, #117 (brain/wiki sync).
- **Next ready work:** **E2 verifier core progressing** — the golden-target generator (**#75**), the
  **golden→reward integration (#31** — `grade_deployment`), the **deployed-state read path (#30)**, and
  now **read-coverage enforcement (#141** — FAIL-CLOSED + closed-world + per-property gate) landed in
  `py/packages/verifier` (account-B-pure). The sound closed-world **`verify`** entry is now the only
  reward-emitting read path (it superseded the #30 `verify_deployment` skeleton). **Next E2: the
  reward-record/ledger handoff (#32).**
  Plus **account infra T7 (P1-BLOCKING)** — now also owns the #80-surfaced closed-world SCP
  create-allow-list (**#53**); the #141-deferred real-AWS coverage-matrix tool + cross-account
  read-role (**#52/#33**) stay T7-gated.
  With **E1's spine (#26–#29) complete** and the **#80 / #114 / #115 spikes all GO**, the gates for E2–E7 are
  cleared (**E5/#6** from the #114 GO; **E4/#5** inputs from the #115 GO; **E2/E3** inputs from the #80 GO); and
  the **E3 diff-ir core (#34) + Terraform adapter (#35) have landed** — the shared reward core + normalized
  IR + the deployed-state adapter, so the verifier core (E2/#3) is progressing — read path #30 landed;
  reward wiring #32 is next.
  **T0 team gate (#25) closed on the board** (founder interim RL/eval owner) — **superseded by
  `docs/priorities.md` (2026-07-01): the RL/eval seat is effectively OPEN** (interim ≠ closed; closing it
  is P0); Phase 3 stays hard-gated on the permanent owner.
- **The E11-1 corpus contract (#155) landed** — the `assayops:address` deploy-tag + golden-server-posture
  requirements are documented (`NORMALIZATION.md`) and round-trip-pinned to a real LocalStack read, so the
  **#176 pre-T0 P1 slice's corpus leg** (~15 Terraform drift tasks, private store) is authorable against it
  (`docs/priorities.md` P1 — the live priority order sits above the board).
- **E6 determinism (#7): verifier-determinism check status clarified; #46 re-scoped → E13.** The
  compute-level check — **golden ×K → identical reward; a nondeterministic path fails** — is **already
  built + negative-controlled by #31** (`verifier/tests/test_grade_determinism.py`), reinforced by the
  diff-ir (#34) order-independent core + the byte-identical golden generator (#75). The one
  genuinely-unbuilt slice — the **§6 eval-rigor determinism gate over the real corpus inside the Inspect-AI
  `Scorer`** — needs the **E13 harness (#14, Phase 2→3)** + the **#45 quarantine policy** (7A/T8), neither
  built; so **#46** (was `E6-3`/Phase-1/lane:A) is **re-scoped → E13 / Phase 2/3 / lane:D, blocked by #14 +
  #45** — not Phase-1-ready. **#45 (transient/genuine classifier + K-run reproduce + quarantine) landed**
  (PR #159, `py/packages/replay`). **#44 (E6-1, deterministic replay) reconciled → closed (not-planned):**
  no distinct unblocked account-B slice — its AC splits into the determinism primitive (#45, done), the
  verifier read+grade K-run consumer (**#141**, per the code's own earmark) + the corpus gate (#46/E13,
  blocked on #14), the certified-reproducibility verdict (routed → **#141** production + **#32** enforcement),
  and the *identical-end-state* snapshot-restore + delta-apply (**T9 → #47/E7**, blocked on T6/T7). E6 (#7)
  stays open; its determinism story now spans #45 + #141/#46/#31 + #47.

## Recently Landed

- **#176 leg 1: the corpus — the last unbuilt leg of the pre-T0 directional slice. 15 Terraform
  drift tasks authored + validated in the private store; per-type gates extended; the runs are all
  that remain.** The **store call is resolved**: a local out-of-repo dir
  (`~/assay-private/corpus/pre-t0-slice/` — `load_corpus`'s I11 residency guard refuses ANY
  git-repo ancestor, so "gitignored in-repo" was never loadable), mirrored to a **private HF
  dataset** when org HF access lands; **NOT #76** (P2-frozen behind #52). **Type selection is
  empirical** (the founder per-type gate): probed Cloud Control on the pinned licensed LocalStack
  image — SQS/DynamoDB/Logs have **no CC Read**, SNS/SSM read back **without tags** (the
  `assayops:address` bridge fails closed), EC2 SecurityGroup is rejected (per-instance `VpcId` =
  nondeterministic golden; set-normalization is #66), SecretsManager is weak-signal (write-only
  value) ⇒ the slice spans **S3 Bucket + IAM Role + KMS Key**. The two new types are gated in-repo:
  `default_registry` bridges (readOnly from the official registry schemas: role `Arn`/`RoleId`,
  key `Arn`/`KeyId`) + per-type **grade round-trip smokes** (posture-declaring golden → reward 1;
  minimal golden → reward 0 naming exactly the posture gap — role: ManagedPolicyArns/
  MaxSessionDuration/Path/Policies, key: 8 blocks incl. the default KeyPolicy; untagged deploy
  fails closed on a real read). **Corpus admission hardened** (the two leg-1 ISSUES.md items):
  `load_corpus` structurally validates `compose.yaml` (a `default` workbench + a `localstack`
  service publishing 4566, both port syntaxes) and fails closed on symlinked assets / `:` in file
  keys. **The 15 tasks** (6 S3 / 5 IAM / 4 KMS; drift categories: modified property, security
  posture — trust policy, key policy, PAB — tags, added resource/property, deleted resource) each
  carry `task.json` + `setup.sh` (terraform-apply baseline → aws-CLI out-of-band drift) +
  `files/**` (style-guide-conformant TF; provider pinned `~> 5.0` — 6.x reads S3 tags via the S3
  Control API the pinned image doesn't serve). **Difficulty is tiered against a blind-apply
  policy** (a diverse-lens review finding): five tasks are **state-absent** (setup removes the
  local tfstate after the baseline deploy — the agent must reconcile from config + deployed
  reads) and four require aws-CLI reads/removals by construction, so "run `terraform apply`,
  submit" scores 6/15, not 11/15. All were **validated end-to-end in the real
  per-sample compose sandbox** (workbench image: terraform + tflocal + provider mirror + aws CLI;
  `S3_HOSTNAME=localstack` forces path-style for inter-container S3): drifted state grades **0**,
  the reference fix grades **1**, K-run reproducible, through the production
  `verify()` closed-world path — plus an `inspect eval` mockllm plumbing run (sandbox → setup →
  scorer → log). Run recipe: **`docs/pre-t0-directional-run.md`** (rollouts → held-out-split ETL →
  SFT → delta). Remaining to the number: a base-model endpoint for rollouts + a CUDA GPU (HF Jobs
  or a box) for the SFT — founder-gated access.
- **#176 leg 2: the trainer — new `py/packages/trainer` (`assayops_trainer`): a trajectory→SFT ETL +
  a TRL `SFTTrainer`+LoRA harness, built pre-T0 for the directional slice.** The **ETL**
  (`build_sft_dataset`/`build_and_write`) turns leg-3's graded Inspect `EvalLog`s into a
  rejection-sampled SFT set: an example enters **only** when the deploy-verifier `Score` is `CORRECT`
  — i.e. **reward 1 = the account-B `verify()` grade** (§8 reward-boundary, non-waivable: train on the
  graded reward, **never** the env `step()`). "#78-shaped minus KMS": pre-T0 has no ledger, so the
  reward is read from the log's scorer key and the join key is the eval **sample id** (the
  `trajectory_id ⨝ KMS-signed WORM record` join #78 adds later). Everything else is **excluded and
  counted** (INCORRECT / quarantined-NaN / errored); a **held-out task id in the training logs FAILS
  CLOSED** (contamination — eval-rigor/I11); duplicates dropped; output deterministically sorted →
  reproducible **`sft.jsonl`** (clean `{messages, tools}`) + **`manifest.json`** (provenance + counts,
  R1-framed). Transcripts convert via inspect-ai's own **`messages_to_openai`** (never hand-rolled);
  tools come from the sample's model events (public `ToolInfo`→OpenAI, deduped). The **`TrainerConfig`**
  encodes I6 (Qwen2.5-Coder-7B, LoRA r=32/α=16), I8 (**required** `model_revision` pin), and
  `assistant_only_loss` (TRL masks tool observations — not hand-rolled); eval-rigor: `training_seed`
  is labelled distinct from a rollout seed. **`run_sft`** lazy-imports the heavy stack (trl/peft/
  transformers/datasets/torch) — pinned in `train-requirements.txt`, deliberately **OUT of the
  hermetic gate** (a clear `ImportError` points there when absent). SFT-only (no RL/GRPO before the
  proof). The scorer-log-key contract with `assayops_evals` is locked by a cross-check test. TDD
  (RED→GREEN); the config kwargs are proven against the real TRL/PEFT API behind `importorskip`
  (skips in-gate). **Diverse-lens adversarial review** (Codex gpt-5.5 xhigh + a reward-boundary/
  eval-rigor lens + a correctness/Python-craft lens) — all three converged, findings validated
  against the pre-T0 context and the real fixes applied: the **held-out tripwire now fires on ANY
  appearance** (before grade/error triage, not only on the CORRECT path); a CORRECT is admitted only
  against **reproduced-grade metadata** (verdict + graded task_id) from a **`status=="success"`** log
  (foreign/partial/edited logs fail closed — the pre-T0 stand-in for #78's signature check); a
  **limit-hit** sample is counted-incomplete, not a whole-build crash; **`model_revision` must be a
  hex commit hash** (rejects `main`/tags/`""` — real I8); dedup key + provenance carry the **eval
  task identity** (no cross-task collision); async `read_eval_log_async`; `exclude_none` tool dumps;
  deduped `source_run_ids`; `verifier_runs` `None`-not-`0`; and the inaccurate "pinned" wording
  corrected to "minimums, frozen at run time". `bun run verify` green **35/35** (33 trainer tests, 1
  GPU-only skip); both lockfiles frozen-checked.
- **#176 leg 3: the Inspect-AI eval harness — new `py/packages/evals` (`assayops_evals`), the E13/T11
  seam built pre-T0 for the directional slice.** The **deploy-verifier as a custom Inspect `Scorer`**
  (I6/T11) around the shipped **`verify()`** — the only reward-emitting entry — with every grading
  input HARNESS-OWNED (the TaskSpec re-validated from sample metadata the dataset loader writes; the
  registry/scope/bridge from the private corpus; readers from the injected factory — never agent
  output). Verdict→Score preserves the 7A semantics: `Reproducible`→C/I, `FailedClosed`→I (cause
  surfaced), **`Quarantined`→`Score.unscored()`** (excluded from the rate — never a false 0), and a
  corpus/config error PROPAGATES (fails the sample loudly). **`load_corpus`** defines the private
  corpus-directory contract (corpus.py REGISTRY/READ_SCOPE/BRIDGE_REGISTRY + compose.yaml +
  `tasks/<id>/{task.json,setup.sh,files/**}`) and is the task-ADMISSION gate — the golden must
  regenerate (#75) and pass `assert_golden_readable` (#141's authoring-time per-property gate) — plus
  a **fail-closed I11 residency guard** (an in-repo corpus is refused; in-repo fixtures synthetic
  only). **`drift_slice`** wires the react agent (bash/text_editor) in a per-sample compose sandbox
  (agent workbench + the sample's OWN LocalStack — per-sample isolation because the closed-world read
  enumerates the whole substrate); **`localstack_reader_factory`** discovers the sample's published
  4566 endpoint from the sandbox connection's typed port mappings (fail-closed) and builds one
  reader per scope-required Region (mirrors the skill-validated `infra-local` client shape; boto3
  adaptive per the #45/#141 policy split). **`render_report`** hard-codes the R1 framing (PRE-T0
  DIRECTIONAL / NOT the E13 proof / never publish) into the delta artifact; quarantined rollouts are
  excluded, never failures. **Pre-T0 trust caveat documented** (no A/B split — the substrate is
  agent-reachable; licensed by priorities.md P1 for a no-claim directional number only). TDD
  (RED→GREEN, no Docker/model in the gate; the scorer exercised end-to-end through the REAL
  verify→read_closed_world→normalize→grade path over the shared Cloud Control fakes;
  FailedClosed→CORRECT + Quarantined→INCORRECT negative controls proven to fail). Turbo edge
  verified (a verifier source change flips the evals task hash). `inspect-ai` pinned (0.3.244,
  py.typed → mypy-strict native).
  **Diverse-lens adversarial review** (4 specialists + 2 moat-forge lenses + Codex gpt-5.5 xhigh):
  both moat reviewers cleared the trust seam (no agent output reaches the grade); Codex's initial
  "block" was the pre-T0 quarantine-as-dodge, **validated against the floor as licensed** (R1
  non-adversarial-SFT, never-published; strictly weaker than the already-forgeable reward 1 in a
  no-A/B slice) — documented, not changed. Fixes applied + re-reviewed to a clean Codex xhigh SHIP:
  the **I11 residency guard** was FAIL-OPEN on an installed harness (no `.git` ancestor) — now keys
  off the corpus's own location, refusing a corpus inside ANY git repo; **removed the
  `allow_in_repo_for_tests` bypass from the `drift_slice` `-T` CLI surface**; **cancellable verify
  thread** (`abandon_on_cancel=True` — read-only, so the scoring time limit can cancel a wedged
  K-run); **report robustness** — errored samples excluded (never crash the artifact), a
  full-rollout-grid `(task_id, epoch)` comparability gate, a conservative quarantines-as-failures
  lower bound + a divergent-quarantine WARNING (anti-farming visibility). Tests **41 → 61**.
  `bun run verify` green **32/32**; both lockfiles frozen-checked. (#176 comment records the
  grounding reconciliation + leg gating.)

- **#61 (spike): LocalStack ↔ real-CFN drift parity — resolved, both substrates measured (licensed
  LocalStack + real AWS on re-issued creds; the R3-spike answer + unit economics recorded — §7 R3 stays
  open until the corpus-wide T9 fidelity-diff; the first 2-type sample ran clean).** **Zero parity on CFN
  drift detection — the API family does not exist on LocalStack:**
  `DetectStackDrift`/`DetectStackResourceDrift`/`DescribeStackResourceDrifts` return HTTP
  501 "not currently supported" on licensed 2026.5.4 `pro` (empirical, incl. a nested-stack root;
  `DriftInformation` remains `NOT_CHECKED`); `DescribeStackDriftDetectionStatus` + `DetectStackSetDrift`
  unimplemented per the docs' API-coverage table (feature table: Drift "—"); the real-CFN side confirmed
  empirically (same drifted stack → `DETECTION_COMPLETE`/`DRIFTED`, exact per-property `NOT_EQUAL` diffs)
  ⇒ **drift-detection-graded reads are real-AWS-only** (the CDK/T3 path #66); the Phase-1 Terraform/CC
  path is untouched (#80). **The fidelity that matters HOLDS: LocalStack Cloud Control reads live state**
  (drift AND fix read truthfully; S3+SSM, both grade directions), and the **first LocalStack↔real-AWS
  fidelity-diff sample ran clean on the graded surface** — every explicitly-authored property matched;
  divergences: adapter-dropped readOnly endpoint props (#35); server-default posture on unauthored props
  (**presence-parity holds** — all four S3 posture blocks present on both substrates, three byte-equal;
  `BucketEncryption` shape diverges: LocalStack's S3-API-style `ApplyServerSideEncryptionByDefault` vs the
  CFN-schema `ServerSideEncryptionByDefault` + real-AWS-only `BlockedEncryptionTypes` ⇒ #155's shape-pin
  is **per-substrate**); and real-CFN-injected **`aws:cloudformation:*` system tags** absent on LocalStack → the
  `aws:*`-strip adapter rule filed as **#179** (E3, boarded); per-type gates (#35/#141/canary) still admit
  each corpus type; corpus-wide sample = T9. Parity by corpus feature: DeletionPolicy=`Retain` honored on
  delete (both substrates); nested-stack children deploy + CC-readable, and real CFN's root drift run
  **masks a drifted child (root reads `IN_SYNC` — false-clean; child directly reads `DRIFTED`)**; **custom
  resources** work end-to-end on both (LocalStack needs the **docker-socket mount** — an E7 substrate
  requirement; `infra-local` omits it by design) but are **ungradable on both substrates** (not registry
  types ⇒ not CC-readable; real drift ⇒ `NOT_CHECKED`, and a custom-resource-only stack reads `IN_SYNC` —
  a second false-clean) → corpus-excluded. Real-CFN drift
  detection is itself lossy (explicit-props
  only, per-type subset, `KMSKeyId`/Lambda-`Code`/write-only excluded, `1GB`≠`1024MB` false positives) —
  confirms #80's "drift alone is incomplete" as a design input to #66. **Unit economics (the Phase-1
  exit-bar "measured LocalStack cost/trajectory"):** minimal drift episode (create → mutate → CC grade-read
  → teardown) = **~2.1s median** (n=5, poll-dominated ceiling) ⇒ ~$0.0003/trajectory substrate compute
  extrapolated at GH-Actions rates; license Hobby $0 now / Base $39/license/mo (annual; $45 monthly), CI
  un-metered ⇒ **≈$0.039/trajectory at 1k/mo (annual billing)**, falling with volume; **real AWS measured:
  ~26.0s median** (n=3; create 19.4s, grade-read 1.2s, teardown 4.6s) ⇒ **~12× LocalStack substrate
  wall-clock**, resources ~$0 (the real cost drivers are T6/T7 account infra);
  **ratio: bulk = 100% LocalStack for the CC-graded Terraform corpus (per-type gates still apply); 0% for
  drift-detection-graded; the T3 real-AWS eval slice + T9 fidelity-diff sample stay real by trust
  posture.** Ratified note in
  `DECISIONS.md` §1; probes preserved in the #61 thread (scratchpad-only — a spike's output is the
  decision, not a package); real-AWS leftovers swept to zero (stacks/buckets/lambda/role/params). Biases
  #176's task authoring → CC-readable types, no custom resources. **Cross-model adversarial review**
  (Claude subagent + Codex gpt-5.5 xhigh, both fed the verbatim probe record): both P1s fixed pre-merge
  (empirical-vs-doc attribution split; R3-spike vs §7-R3 scoping); Codex re-review → SHIP. (#61, PR #177.)

- **E11-1 (#155): the Terraform-adapter corpus contract — `assayops:address` deploy-tag + golden
  server-posture, pinned to a real read (the LocalStack grade round-trip).** The two corpus requirements
  the #35 adapter established are now a documented, machine-verified contract for corpus authoring
  (#76/#67 — and the **#176 pre-T0 P1 slice's corpus leg**, which authors "on the #155 contract",
  `docs/priorities.md` P1): (1) every graded resource deploys tagged `assayops:address = <its logical
  address>` (the golden's addresses); (2) **goldens declare server-defaulted posture explicitly** —
  confirmed empirically on a real Cloud Control read (against the **pinned LocalStack image**; the
  *defaults* themselves are AWS-user-guide facts, and real-AWS read-*shape* parity re-pins with the
  real-cloud read path, #30/#141/#61): `AWS::S3::Bucket` returns **four** blocks the deploy
  never set (`BucketEncryption` SSE-S3, `PublicAccessBlockConfiguration`, `OwnershipControls`
  `BucketOwnerEnforced`, plus **`AbacStatus` `Disabled`** — a writable current-schema property the probe
  surfaced beyond the issue's predicted three), each grounded live in the AWS user guide + the real
  `AWS::S3::Bucket` schema (top-level `readOnlyProperties` exactly match the adapter registry;
  `tagProperty=Tags`). New `infra-local` **grade round-trip smoke** drives the verifier's production
  read→normalize→grade components against LocalStack (get-scoped by identifier; the closed-world
  `verify` enumeration stays #141's hermetically-tested layer) — deploy a tagged bucket →
  `DeployedStateReader.read_resource` → adapter
  `normalize` → `grade_deployment` (synthetic registry; the golden is **declared constants, never derived
  from the read** — no tautology) → **reward 1** — plus the negative control: the minimal pre-contract
  golden grades the SAME correct deploy **reward 0** with the diff naming exactly the four posture blocks
  (the issue's defect pinned; the non-vacuousness proof; the image-bump shape canary), and a
  missing-`assayops:address` deploy **fails closed on a real read** too. Docs: the
  `NORMALIZATION.md` corpus-contract note (declare the posture; **pin a new type's golden shape to a real
  read before authoring**) + adapter/infra-local READMEs. Wiring: infra-local consumes the five sibling
  cores by source path (mypy_path/pythonpath + pydantic.mypy) with workspace deps + a `turbo.json`
  `^typecheck` edge (the #152/#31 pattern; hash-flip verified). **Review** (Claude adversarial + testing +
  maintainability agents + Codex `gpt-5.5` xhigh, findings validated then fixed): `localstack-smoke.yml`
  now **triggers on the five consumed sibling packages** (a grading-chain change runs the round-trip on
  ITS OWN PR — the canary fires where the break is); fixtures **delete-and-recreate** (a locally-mutated
  posture can't produce stale false alarms; CI was always fresh); substrate-honest wording (LocalStack-
  pinned shape vs AWS-documented defaults). Smoke green on a fresh LocalStack (re-run-proof); `bun run
  verify` green **29/29**. **No production code change** (corpus requirements, not adapter bugs); nested
  `MetadataConfiguration/*` readOnly paths characterized as out of Phase-1 scope (ISSUES.md). (PR #178.)

- **E2-6 (#141): boto3 read-coverage enforcement — FAIL-CLOSED + closed-world + per-property gate (the
  in-repo, account-B verifier-side half).** New `read_scope.py` (the verifier's read-coverage matrix:
  `RegionScope`/`Listability`/`TypeCoverage`/`ReadScope` + the per-property gate `assert_golden_readable`),
  `verify.py` (the sound closed-world **`verify`** entry + `VerifyVerdict = Reproducible | Quarantined |
  FailedClosed`), and the read path (`read.py`) extended with transient classification (7A) +
  `read_closed_world` over the in-scope **type × Region** matrix. **The three scopes (DECISIONS.md §1):**
  (1) a transient read failure routes through the 7A classifier + K-run (`reproduce`, #45) — never scored
  0 on the spot; (2) exhaustive, paginated, fail-closed enumeration so an extra can't hide *unenumerated*
  (`deployed set ≡ golden set`, vector #15); (3) the authoring-time write-only-property gate. `verify` is
  now the **only** reward-emitting read entry (it **removed** the #30 `verify_deployment` skeleton — an
  unsound single-Region, no-K-run bypass a caller could have scored reward 1 through). **AC negative
  control:** an extra/unreadable B-side resource → reward 0 / fail closed, never 1.
  **Floor-touching decision (Recommendation A, two-model grounded):** `verify` initially RAISED on a
  genuine unreadable — a silent deviation from §1 ("genuine unreadability ⇒ reward=0") leaving a
  reward-channel dodge open. Surfaced per "flag, don't silently deviate"; **Opus 4.8 max + Codex gpt-5.5
  xhigh** both CONFIRMED the dodge (the verifier reads same-account via STS-assume-into-A, so an agent
  resource-policy explicit-Deny — sharpest for the Phase-1 KMS key policies — → AccessDenied; SCPs gate
  actions not policy content) and converged on A: a genuine / un-gradable instance of agent-controlled
  deployed state (`UnreadableResourceError` + `AddressBridgeError`/`DuplicateAddressError`) → reward 0
  (cause in the verdict reason, alarm out-of-band, never masked); corpus/config errors propagate. A
  PRECONDITION is documented for #52/#60 (the readiness gate must exercise per-type read perms).
  **Review:** two adversarial rounds (Codex xhigh + a 19-agent diverse-lens Workflow, every confirmed
  finding fixed) + the 2-model A decision + a clean **final Codex xhigh re-review → SHIP** (no
  false-reward-1 path in any pass). `bun run verify` green **29/29** (102 verifier tests); the
  verifier→`replay` Turbo cache edge + the cloud-free `import assayops_verifier` boundary asserted.
  **Deferred (T7-gated, do NOT gate on):** the real-AWS coverage-matrix regeneration tool + `describe-type`
  IAM derivation (scope 4/5) → **#174** (E2-8, blocked-by #53/#52/#33); SCP #53; read-role #52/#33. (PR #172.)

- **#63 (spike): read-side reward-hacking → vector 15 characterized (E10/T10, R1).** Resolved the
  read-side reward-hacking spike. Characterized **vector 15** (read-side state-read spoofing — crafted
  state that fools the verifier's *read* into a false "in-sync") into concrete sub-attacks across the two
  reward-hacking modes (`red-team-exit-bar`). **Closable sub-attacks DEFENDED today** (mode-1 isolation:
  run-agent-code / A→B-redirect / agent-provenance; mode-2: `assayops:address` tag-bridge spoof,
  unreadable-masquerade, list/get race, normalization-gaming, empty-golden) — each demonstrated
  end-to-end against the **real** `verify_deployment → normalize → grade` path (scratchpad proof, 5 demos
  incl. a self-controlling in-scope-vs-out-of-scope differential; **not committed** — a spike's output is
  the recorded decision, the committed documented-to-fail suite is **#56**'s owner-gated job). **OPEN
  half — 15h closed-world/over-provisioning, 15i discovery-scoping, 15j per-property coverage:** reads
  alone can't see an extra resource of a type outside the verifier's `type_names` / an unscanned Region
  (demonstrated — a forbidden out-of-scope `IAM::Role` forges a false in-sync). The moat-critical closure —
  **#141** verifier-side closed-world enumeration (detection) — is **unblocked (next E2 slice; does not
  depend on #53,** per the #141 scoping comment); **#53** (T7 SCP prevention, `assay-cloud-org`) + **E8**
  (#33/#52) close the residual non-listable / out-of-scope-reachability / decoy sub-cases.
  **Per R1, vector 15 is OPEN → no reward/lift claim** until #56's suite is green. Concrete fixtures
  **promoted to #56** (comment) + **#56 wired blocked-by #53/#141**. **Diverse-lens review** (Claude
  forge-lens + Codex `gpt-5.5` xhigh, re-reviewed to convergence) caught + corrected a mis-classification
  (empty-golden is DEFENDED on the production path — the `GoldenTarget` validator — with #154 the
  `grade()`-boundary defense-in-depth, not OPEN), re-verified against the code. **No code change** (spike
  = decision); DECISIONS.md §5 untouched (locked; the vector-15 row is already correct). (#63.)

- **#165: corrected the `RoleArn`-as-cross-account knowledge-source error (skill + brain) + re-vendored.**
  The `write-isolated-verifier` skill + brain claimed Cloud Control's `RoleArn` is the B→A cross-account
  read hook — but it is a **same-account** CloudFormation service role (assumed by `cloudformation.amazonaws.com`,
  scopes downstream perms, 24h→36h); the **target account is set by the signing credentials**, and the
  cross-account read is **STS `AssumeRole` into a read-only role in A → account-A creds → Cloud Control
  client**. This is the knowledge-source root that misled #160 (the verifier-read **code** was already
  corrected in #164). Validated by **2 adversarial reviewers** (Claude Opus 4.8 + Codex `gpt-5.5` xhigh, both
  CONFIRM) + **firsthand official-AWS-docs grounding** (Cloud Control "Specifying credentials" user guide +
  STS `AssumeRole`). Fixed at source — **AssayInc/skills#10** (SKILL.md + grading-primitives.md; reframed the
  anti-pattern row so the *sanctioned* B→A read-only assume isn't branded the A→B vector; +regression eval
  case 4) — then **re-vendored + re-pinned** here (`skills-lock.json` `a268afb9`→`bf027adc`). An adversarial
  **diff** re-review (Codex FIX→SHIP; Claude SHIP) caught a signing-credentials ambiguity in the PR text
  pre-merge. Brain pages corrected (working tree, for wiki-ingest). (#165.)

- **E2-1 follow-up (#163): corrected the cross-account read mechanism + hardened the read path.** A
  post-merge diverse-lens review of #160 (security-forge + edge-case + design/SOTA, across Codex `gpt-5.5`
  xhigh + Claude) found three defects; the moat holds (no reward-forge). **(1) Trust-claim fix:** #160 used
  Cloud Control's `RoleArn` as the B→A cross-account read hook (vector #10) — but verified against the AWS
  Cloud Control user guide, `RoleArn` is a **same-account** CloudFormation service role; the target account
  is set by the **signing credentials**, and a cross-account read is **STS `AssumeRole` → account-A creds →
  client**. Removed the `role_arn` hook + corrected the docstrings — the cross-account role assumption is
  **#33/E8**, restoring DECISIONS §1 (#160 silently deviated). **(2) `RecursionError` DoS:** `_properties_of`
  caught only `ValueError`, but `json.loads` raises `RecursionError` on deeply-nested JSON → the read crashed
  raw instead of failing closed; now `except (ValueError, RecursionError)`. **(3) Empty-page false-crash:** an
  absent `ResourceDescriptions` is the AWS empty-result shape (omittable array; `infra-local` assumes the
  same) → treated as empty (refining #160's fail-closed-on-missing-key, which false-crashed the empty
  account); a present-non-list still fails closed; truncation stays #141. **Root cause flagged:** the
  `write-isolated-verifier` skill + its brain source carry the same wrong `RoleArn` claim — to correct at
  AssayInc/skills + the brain. TDD RED→GREEN; `bun run verify` green **26/26** (75 verifier tests). Codex
  `gpt-5.5` xhigh re-reviewed to convergence. (PR #164.)

- **E2-1 (#30): verifier skeleton — the account-B Cloud Control deployed-state read → grade path (T1/1C/§1).**
  New **`py/packages/verifier/read.py`**: **`DeployedStateReader`** wraps an **injected** boto3 Cloud Control
  client and reads DEPLOYED state read-only (`get_resource`/`list_resources`) into the adapter's
  `DeployedRead` records (#35); **`verify_deployment(reader, registry, task, seed, type_names)`** wires read →
  `normalize` (#35) → `grade_deployment` (#31) → `reward∈{0,1}`. **The moat, proven not asserted:** a
  recording-fake test shows the harness invokes **only** Cloud Control read ops (no write / STS / A→B assume —
  vectors **#1** + **#10** fail by construction, negative-control-verified); the produced state is always
  `DEPLOYED_READ` provenance, so `grade_deployment` (which rejects agent provenance, T1) can never be fed
  agent-reported state. **Fail-closed per record** (vector #15): `ResourceNotFoundException` = absent (a drift),
  any other `ClientError`/`BotoCoreError` or unparseable/malformed read = `UnreadableResource` → the adapter's
  `UnreadableResourceError` (never a silent reward); a listed-then-absent resource fails closed too (never
  dropped).
  **Grounding reconciliation (stale AI-written issue):** the body's `ts/packages/verifier` is **Python**
  (`py/packages/verifier`, E17); the `+ CloudFormation drift` is the **CDK path (#66)** — **Terraform = Cloud
  Control only** (#80, DECISIONS §1; #35 already dropped it). boto3 `get_resource`/`list_resources` shapes
  **primary-doc-verified**; anchored to `infra-local`'s LocalStack proof of the exact read
  APIs (no duplicate #30 smoke). **Scope deferred** (flagged, not built): the closed-world `deployed set ≡
  golden set` enumeration + per-property coverage gate + 7A transient/genuine classifier → **#141**; the
  cross-account read-only role + IAM/SCP → **#141/#53/E8**; CFN drift → **#66**; the reward-record/ledger
  (KMS-sign + WORM) handoff → **#32**; the 15-vector red-team fixtures → **#56**. **Layering:** `read.py` is
  kept **out of the package top-level `__init__`** (boto3-dependent), so golden/grade stay cloud-free (the
  determinism subprocess needs no boto3). **TDD (RED→GREEN, +39 tests → 74 verifier total):** parsing, the
  absent/unreadable/malformed fail-closed classification, paginated discovery, the
  read-only moat, and the AC integration (clean→1, property-drift→0, missing→0, unreadable→fail-closed,
  unsupported-type→fail-closed) end-to-end through the **real** `normalize` + `grade_deployment`. **Cross-model
  `/review` converged to SHIP** — Claude `code-reviewer` (moat negative-control-verified: a planted write op
  trips the fake's guard; no false-reward-1) **+ Codex `gpt-5.5` xhigh** (re-reviewed to convergence) —
  hardening the fail-closed read: `BotoCoreError` (network/timeout/creds) now → `UnreadableResource` (was
  escaping raw); a malformed `list_resources` page now **fails closed** (was fail-OPEN — a missing
  `ResourceDescriptions` had defaulted to `[]`); a listed-then-`RNF` resource now → `UnreadableResource` (was
  dropped). Adds `boto3>=1.40` to the verifier (the read SDK; account-B-pure, no write/sign deps) + the
  `adapter-terraform` workspace dep (Turbo cache edge). `bun run verify` green **26/26** (74 verifier tests);
  both lockfiles frozen-checked. (PR #160.)

- **E6-2 (#45): transient/genuine classifier + K-run reproduce + quarantine — the 7A determinism gate
  (locked 7A/T8).** New **`py/packages/replay`** (`assayops_replay`) — the E6/T8 home (ARCHITECTURE.md),
  shared with E6-1/#44 (replay); the verifier-determinism eval-gate **#46** (re-scoped to E13/Phase 2-3)
  consumes this policy. Scoped here to ONLY #45's classifier + harness.
  **`classify(exc) -> FailureClass`** + **`is_transient_aws_error_code`**: the 7A transient policy —
  **transiently unreadable** (throttle / 5xx / read-after-create eventual consistency) is TRANSIENT (retry
  within the small read budget, then FAIL-CLOSED). A throttle is NOT a wrong answer — scoring it 0 is a
  false-negative (deterministic-verification skill; #141 scope 1 routes a surfaced throttle through the 7A
  classifier + K-run). **Policy vs mechanism:** boto3 adaptive owns the SDK throttle/5xx RETRY; #45 owns the
  POLICY + the K-run gate #141 routes a surfaced transient into. AccessDenied (isolation alarm, never masked)
  / Validation / bug = GENUINE. **`reproduce(grade_fn, *, runs, ...) -> Reproducible | Quarantined`**: drives
  an injected grade callable K times, absorbs transients via a bounded backed-off retry (deterministic, NO
  jitter — single grader + determinism-critical; injectable `sleep`), and **quarantines** a non-reproducing
  (flaky) task — `Quarantined` carries **no reward attribute** (type-enforced "never silently rewarded",
  vector #15); a genuine failure / exhausted transient budget fails closed (raises). `Reproducible` carries
  the verified `GradeOutcome` so the ledger signs what the gate certified. **Generic over the grade callable**
  → depends on diff-ir + contracts only (NOT verifier), so #141's read path reuses the classifier cycle-free.
  **K is a parameter** (default 3) — DECISIONS.md leaves it unlocked (flagged, not silently locked). **TDD
  (RED→GREEN, 32 tests):** classifier policy — transient by error code, HTTP status (5xx), AND
  connection/timeout exception class (matching botocore's standard-retry checkers), eventual
  consistency; AccessDenied/
  Validation/bug genuine; marker + ClientError-shaped + malformed paths) + the AC (an **injected
  nondeterministic task** → quarantined, no reward) + same-reward/different-diff quarantine + transient-
  absorbed → reproducible + fail-closed paths + verdict determinism. Grounded: DECISIONS.md §1/7A + brain +
  deterministic-verification / write-isolated-verifier / python-resilience / error-handling / type-safety
  skills + **#141's scope (read myself, not via a stale subagent summary)**. **A primary-source re-read (the
  skill + #141 scope 1) caught + reverted an over-narrowing that had wrongly made a surfaced throttle GENUINE
  — a false-negative reward; throttle is a transient.** `TransientBudgetExhausted` carries a
  `TransientKind` so #141 maps a settled-absent NotFound → reward 0 vs a sustained throttle →
  quarantine (never a boundary false-negative). A final xhigh pass caught a second false-negative —
  a 5xx with an unrecognized code (transient by HTTP status in botocore) was scored genuine — now
  classified by code, HTTP status (500/502/503/504), **and** connection/timeout exception class —
  matching botocore's standard-retry checkers; the one un-mirrorable case (service-*modeled*-retryable)
  is documented as marker-authoritative (#141 uses boto3's own classification).
  `bun run verify` green **29/29** (32 replay tests);
  both lockfiles frozen-checked. (PR #159.)

- **#60 (spike): IAM eventual consistency — resolved (measured against real AWS).** A bounded engineer probe
  (**not committed** — a spike's output is the recorded decision, not a package; the script is preserved in the
  #60 thread) measured propagation for a fresh `AWS::IAM::Role` (n=20,
  us-east-1): **Cloud Control read-after-create is effectively immediate** (p99 < 0.2s, zero variance) — the
  verifier read path (E2/T1) is largely insulated (cc_get p99 ~0.76s, 0 bound-exceeded), so its
  read-after-create 7A budget is small + FAIL-CLOSED — while **`AssumeRole`/use propagates at ~7s p50 with a
  tail to ~42s**, so the real delay is the **E8
  provision-then-use** path: gate first use of a fresh cross-account role behind a **bounded (~60s) FAIL-CLOSED
  readiness poll, isolated from the grade**. The "readiness gate" is a **calibration of the locked 7A transient
  budget**, not a new mechanism (reconciles with #80's read-after-create→7A + #141). The smoke caught a real
  bug pre-full-run (fresh STS creds are transiently `InvalidAccessKeyId` — folded into the `perm` horizon).
  Ratified note landed in `DECISIONS.md` §1; consumers updated (#45 the 7A classifier, #141 read-coverage,
  #52/#33 cross-account role assume). Probe is mypy-strict/ruff-clean (boto3 `BaseClient` boundary). Grounded
  in `deterministic-verification` (7A) + `aws-iam` + `aws-sdk-python-usage` + brain `retries-and-backoff`.
  The probe is **not committed** (§8 build-only-the-IP) — a spike resolves into a recorded decision, not a
  package (#156 closed). `bun run verify` green. (PR #151.)
- **E2-2 (#31): golden→reward integration — `grade_deployment` (generate→bridge→grade), the verifier's
  grade entry (2A/6A/T1).** The seam between the golden-target generator (#75) and the shared reward core
  (#34) — which had no bridge yet (`verifier` didn't import `diff-ir`). New
  `py/packages/verifier/grading.py`: **`grade_deployment(registry, task, seed, deployed) -> GradeOutcome`**
  — the account-B verifier **regenerates** the golden from (task, seed) (never accepts one from the caller —
  2A "independently regenerated golden"), bridges it into the reward core's `NormalizedState` IR via
  **`golden_as_normalized_state`** (tagged `GOLDEN_TARGET`), and `grade`s a B-side deployed-state read
  against it → `reward∈{0,1}` = zero **normalized** diff. The bridge **fails closed**
  (`GoldenNotGradableError`) on a golden the grading core can't represent — the diff-ir value validator (#34)
  is intentionally **stricter** than the generator's (#75) (rejects a `None` value / `$`-key the generator
  allows): never a silent reward (§8, vector #15). **Flag (ISSUES.md):** harmonizing the two validators is a
  possible #75/#34 follow-up, out of #31's scope. **Wiring:** `verifier` now consumes `diff-ir` by source
  path (mypy_path/pythonpath + an `assayops_diff_ir.*` mypy override mirroring the contracts one); the
  existing cross-hash-seed determinism subprocess got diff-ir added to its PYTHONPATH (re-exporting
  `grade_deployment` pulls diff-ir into the package import). **TDD (RED→GREEN, +19 tests → 54 total):** AC1 —
  known-pair integration (correct deploy→1; value/missing/extra/type drift→0; a JCS-equal-but-differently-
  encoded deploy — int `90` read back as float `90.0` + reordered keys — still →1, the "*normalized*"
  proof); AC2/#46 — generate→bridge→grade ×K → identical reward + report (in-process + cross-hash-seed
  subprocess; plus a negative control — a nondeterministic golden fails the check via the load-bearing
  diff-bytes assertion, satisfying #46's "a nondeterministic path fails"); T1 — deployed slot rejects agent
  plan/state (fail closed), golden regenerated internally (no caller slot to inject), non-normalizable
  golden fails closed. **Cross-model review converged** — Claude
  (`code-reviewer` subagent: no Critical/High, moat verified — no false-reward-1 path, golden un-injectable)
  **+ Codex gpt-5.5 xhigh**. Findings closed: the `$`-key fail-closed case now tested too (the adjacent case,
  lessons.md); the bridge `except` simplified to `except ValueError` (verified against the pydantic docs that
  `ValidationError ⊂ ValueError`, not memory); a determinism comment de-overclaimed; and **Codex caught a
  Turbo cache-graph gap** — the verifier reads diff-ir by source path but Turbo didn't model the edge, so a
  reward-core change wouldn't invalidate the verifier's cached tests — now fixed (verifier declares its
  `py-diff-ir`/`py-contracts` workspace deps + a verifier `turbo.json` `dependsOn ^typecheck/^test`;
  empirically a diff-ir content change now flips the verifier task hash). The same gap is repo-wide/pre-existing
  — now tracked as **#152** (Turbo cache-graph), with the #75↔#34 validator divergence as **#153**. Pre-merge,
  the AC-cited issues (#75/#46/#34 — bodies, comments, state) were re-reviewed: #31 honors all three contracts.
  **Out of scope** (unchanged): the boto3 read path (#30/#141), the reward-record/ledger handoff (#32).
  `bun run verify` green **23/23** (54 tests). (PR #149.)
- **E3-2 (#35): `adapter-terraform` package — the Terraform deployed-state → diff-IR adapter (6A/T2, the
  A-spike engine).** New **`py/packages/adapter-terraform`** (`assayops_adapter_terraform`):
  `normalize(reads, registry)` turns already-enumerated **Cloud Control deployed-state reads** into the
  diff-ir `NormalizedState(DEPLOYED_READ)` (#34) the shared reward core grades against the golden (#75).
  **Pure** — no boto3, no `terraform`/provider/`.tfstate`/plan read (T1, the moat); the boto3 read +
  closed-world enumeration stay with the read harness (#30/#141/#53). **Address bridge (the one
  floor-unspecified call, founder-decided):** Cloud Control returns a physical id but the core diffs by
  logical `address`, so the deploy tags each resource with a reserved case-sensitive **`assayops:address`**
  tag, read from the schema tag property under a per-type **`BridgeRegistry`** (the codified #80 matrix; an
  unregistered type → fail closed). The untrusted tag value is validated as a logical address; only that tag
  is stripped (user tags kept, sorted); server-computed `readOnlyProperties` dropped; declared set properties
  sorted. **Fail-closed, never a silent reward** (vector #15): a missing/duplicate/malformed/case-wrong/
  reserved/wrong-shape tag, an unsupported or unreadable record, a duplicate address, a non-JSON property.
  **Stale-issue reconciliation (flagged on #35):** the body's `+ CFN drift` read path is dropped —
  DECISIONS.md §1 (#80) locks Terraform = Cloud Control only (no CFN stack ⇒ drift = the CDK/T3 path #66).
  **Empirical proof:** a new `infra-local` LocalStack smoke proves Cloud Control `GetResource` surfaces the
  `assayops:address` tag for `AWS::S3::Bucket` (the founder's per-type gate; **ran green on local LocalStack**
  + in CI; kept out of the hermetic gate as a `smoke` script). TDD: **41 hermetic tests** (all 4 ACs
  end-to-end through the real `grade` + every fail-closed case). **Cross-model `/review`** (Claude
  adversarial + correctness + Codex `gpt-5.5` xhigh, re-reviewed to convergence) hardened it: funnel any
  unexpected exception (a deep-nested `RecursionError`) into the fail-closed `AdapterError` family;
  case-insensitive reserved-`assayops:*` check; dropped the unused/`json.dumps`-divergent set-sort seam
  (real set normalization → #66, JCS-aligned). `bun run verify` green **26/26**; both lockfiles
  frozen-clean. Establishes the **corpus deploy-tagging convention** (#76/#67 must tag resources
  `assayops:address`; goldens must also declare server-defaulted posture, e.g. S3 encryption/BPA, for a
  real-cloud read) — tracked as **#155** (E11), with the reward-core empty-golden guard as **#154** (E2).
  (PR #150.)
- **E3-1 (#34): `diff-ir` package — the normalized IR + shared reward core (6A); the first E3 deliverable.**
  New `py/packages/diff-ir`: the tool-agnostic normalized-state IR (`NormalizedResource`/`NormalizedState` —
  the adapter↔core interface) + the **shared, write-isolated reward core** `grade(deployed, golden) ->
  GradeOutcome(reward, diff)`. `grade` is the **only** public reward entry, so its consumption is exactly
  {B-side deployed-state read, regenerated golden target} (AC2): it **fails closed** (`UntrustedInputError`)
  on any other provenance — the code-level expression of **T1** (`AGENT_PLAN`/`AGENT_STATE` exist only to be
  rejected), a complement to (not a replacement for) account-B isolation. It builds the codegen'd `DiffIR`
  (golden=expected, deployed=actual; `reward∈{0,1}` = zero normalized diff) **tool-agnostically** and
  **deterministically** (resources + property paths canonically ordered → order-independent + K-run identical;
  a same-address type mismatch → a reserved `$type` propertyDiff). **DRY:** reuses the E1
  `DiffIR`/`Resource`/`PropertyDiffs`/`Change`/`Reward` contract types; per-tool adapters (#35) + the golden
  generator (#75) do the tool-specific normalization of one side. `NORMALIZATION.md` documents the adapter↔core
  split + the determinism contract (AC3); the report serializes with `exclude_none` (the schema-valid sparse
  form — closes the ISSUES.md `propertyDiffs:null` DiffIR residual). **Reconciliation flagged on the issue:**
  the schema *description* reads "adapter produces this IR," but the **core** producing it from two normalized
  states is what AC2 requires and keeps the determinism-critical diff in one place (the brain leaves the
  diff-owner open). **Wiring:** the first intra-workspace import (diff-ir → contracts via `pythonpath`/`mypy_path`;
  the `pydantic.mypy` plugin — first hand-written plain-`BaseModel` package under the `Any` ban —
  + `follow_imports=silent` for the sibling spine); `uv.lock` + `bun.lock` both updated. **Value equality +
  validity are defined by RFC 8785 JCS canonicalization** (the form `RewardRecord.reportDigest` is signed with,
  so the grade and the digest agree by construction), behind a thin **exact-type input guard** (`type(x) is T`):
  `rfc8785.dumps` coerces a builtin subclass via user code, so a subclass / reference cycle is rejected before
  it can forge or flip its canonical bytes. TDD: 50 tests; cross-model `/review` (Claude + Codex `gpt-5.5`
  xhigh, **9 passes to convergence** — 6 on the original diff + 3 on the JCS refactor that caught the
  subclass-coercion forge then the cycle crash) hardened the reward against false-reward-1 / laundering paths.
  `bun run verify` green **20/20** (forced, 0-cached). (PR #145.)
- **E2-5 (#75): golden-target generator — the account-B verifier's reproducible ephemeral target (2A).**
  The first **E2 verifier-core** code: new **`py/packages/verifier`** (`assayops_verifier`).
  `generate(task, seed)` deterministically regenerates the expected **normalized resource set**
  (`GoldenResource` = address/type/properties — diff-IR-compatible, so the E3/#34 adapter diffs deployed
  state against it) — **pure over (task, seed)**, never the agent's synth/plan/state (T1/§1/§8); a
  **declarative regeneration, not running reference IaC**. The per-task golden builders are the engine's
  **corpus seam** (`GoldenRegistry`); real builders live in the **private corpus (#76)** (the engine, NOT
  corpus authoring), and in-repo tests use **synthetic** builders only (held-out residency). **Determinism
  (AC1, feeds #46):** hash-based ephemeral tokens (no clock/RNG) + canonical address-sort + JCS key-sort →
  byte-identical across K runs (negative-controlled). **Content address (AC4):** `golden_digest` =
  lowercase-hex SHA-256 over RFC 8785 JCS canonical bytes, **reusing the locked `assayops_contracts.jcs`
  recipe** (DRY) — reproducible from (task, seed) + the record's `trajectory_id`→`task_id`→seed +
  `graderVersion`; **no contract-schema change** (the reward record has no golden-digest field; a dedicated
  one would be a flagged #28 `fixture-change`, not silently added). **Fail-closed** (unknown task / duplicate
  addresses raise — vector #15). **Hardened** Pydantic models (frozen/extra-forbid/strict; the pydantic.mypy
  `disallow_any_explicit` gotcha fixed via the plugin + init_typed/init_forbid_extra). First cross-package
  Python dep — consumes `assayops_contracts` by source path (the repo's virtual-member convention); contracts
  untouched. **Three adversarial-review rounds converged to MERGE** (`/review`, then a founder-requested
  **Opus 4.8 max** + **Codex `gpt-5.5` xhigh** pair): the **moat held in all** (no agent-reachable forge
  path — the golden is account-B-internal), and every finding was **content-address-integrity / fail-closed
  hardening** of the open-`properties` channel, all closed + negative-controlled: reject
  set/non-finite-float/oversized-int/non-UTF-8-surrogate/non-JSON and **only exact JSON types** (subclass
  iteration/encoding can diverge from what's hashed); canonical-by-construction model + immutable `resources`
  tuple; `generate` wraps **any** builder failure into the single `GoldenError`; `golden_digest` re-checks the
  **live** golden (catching a mutated set/BaseModel/cycle) before canonicalizing; injective length-prefixed
  token. `bun run verify` green **20/20** (35 verifier tests; the load-bearing guards negative-controlled);
  both lockfiles frozen-checked. Runtime-import hardening (consume contracts as an installed pkg) deferred to
  #147. **Gates #31** (golden→reward integration). (PR #146.)

- **E1-5 (#140): codegen hardening — align the hand-maintained lists with the whole schema set.** The
  #29-review tail: three spots that wouldn't follow a newly added schema. (1) `schemas.test.ts` now
  **disk-enumerates** `contracts/schemas/*.schema.json` for the Draft-2020-12 + ajv-compile coverage (a new
  schema is validated automatically; the 4 bespoke instance/modeling tests stay keyed to fixtures). (2) The
  `just codegen` **reward-pin** (`reward: number;` → `0 | 1;`, the §8 binary invariant quicktype can't emit as
  a literal union) was a blanket file-wide rewrite asserting only ≥1 match — now **anchored** to the
  `RewardRecord` interface block + an exactly-one fail-closed guard, so a future *unrelated* `reward: number;`
  can't be silently narrowed (regeneration byte-identical to the committed `generated.ts`). (3) A fail-loud
  **re-export parity test** (`test_model_reexports.py`): every `BaseModel`/`Enum` under `models/*.py` must be
  in `assayops_contracts.__all__` + importable (datamodel-codegen leaves `models/__init__.py` empty, so the
  top-level re-exports are hand-maintained; a *dynamic* re-export would break `mypy --strict` re-export
  visibility, so harden with a test, not magic). **Quicktype globbing + `just-version` pinning were already on
  `main` (PR #139)** — grounding against `origin/main` showed the issue body's "quicktype globbed" was
  correct (the review-comment's "not globbed / never touched justfile" was stale: `origin/main` globs;
  PR #139's squash changed `justfile` +11/−9) and the body's "just-version unpinned" was stale (pinned in
  `ci.yml` + `localstack-smoke.yml`) — so neither was re-done. Proven RED→GREEN with a throwaway 5th schema
  (reaches both generators + the ajv test + the parity test with no list edit), then removed → regeneration
  byte-identical (codegen-parity gate stays green). **Not a `fixture-change` PR** (no `contracts/schemas|vectors`,
  generated-file, or `tools/red-team` edits; `gen_vectors.py` untouched). **Cross-model `/review`** (Claude
  adversarial + Codex `gpt-5.5` xhigh, 3 passes to convergence) hardened the §8 reward-pin to fail **closed**
  on any quicktype-format drift — isolate the RewardRecord interface block by `export interface`-header count +
  top-level-brace termination, `${var:-0}` count default, block-scoped pin-landed backstop — and switched the
  re-export parity test to **object-identity** (catches a cross-module class-name collision); all changes keep
  regeneration byte-identical. `bun run verify` green 17/17. (PR #144.)
- **E1-4 (#29): CI regenerate-and-diff parity gate — E1 (the contract spine) complete.** The DECISIONS.md
  §8 "one-schema codegen" non-negotiable is now CI-enforced: a dedicated **`codegen-parity` job** in the ci.yml
  workflow (it spans both generators — quicktype/bun + datamodel-codegen/`gen_vectors`/uv) runs
  `just codegen` + `just vectors` and fails on any drift (a targeted `git add -A` + `git diff
  --cached` over the three generated paths — catches edits AND added/removed modules; a clear `::error::`
  points back at the recipes). It's its **own job** (not folded into the `ts`/`py` verify lanes — it spans
  both generators and regenerates into the tree; a failed `codegen-parity` check names the cause unambiguously), made
  a **required status check** on the `main` ruleset once the workflow is on `main` — GitHub's
  create-the-check-before-requiring order (requiring it while another open PR's branch lacks the `codegen-parity` run
  would block that PR on a never-reported check; grounded in the GitHub rulesets REST API + status-check docs).
  **Proven to have teeth:** a one-property schema edit drifts all three artifacts (TS `generated.ts`, the
  Pydantic model, the JCS `jcs-golden.json`) → gate exits 1; clean tree → exits 0 (no false-fail).
  **Byte-parity (AC2) was already covered** and runs in `bun run verify` — the py lane's
  `test_python_and_ts_canonicalize_are_byte_identical` (direct TS-subprocess identity) + the ts lane's
  `sha256(canonical)==golden` — so it was verified, not rebuilt. The cross-model `/review` (Claude
  adversarial + Codex gpt-5.5 xhigh) also **hardened `just codegen`**: quicktype now reads the **whole**
  `contracts/schemas/` dir (`LC_ALL=C` glob, byte-identical to the prior explicit list) so a newly added
  schema reaches **both** generators — a hardcoded list had let a new schema's TS type go ungenerated and
  thus invisible to the gate; it also fixes an opaque removed-schema crash. Residual hardcoded-list nits (TS
  ajv test, reward-pin breadth) are tracked in **#140**. **CI-wiring + a codegen-recipe
  fix** — no `contracts/schemas|vectors` or generated-file edits → not a fixture-change PR; the agent that
  writes code never edits the grader. `just` action SHA-pinned + binary version-pinned (`just-version` 1.53.0,
  in both ci.yml `codegen-parity` and localstack-smoke); codegen tools pinned
  (bun.lock/uv.lock) → deterministic. `bun run verify` green 17/17. (PR #139.)
- **E3-4 (#80): boto3 deployed-state read-coverage spike — GO with conditions (recorded decision; no floor
  change).** The E17 (#113) verifier-read spike is resolved. **Terraform read path = boto3 Cloud Control
  `GetResource`/`ListResources` only** — provisioning-agnostic (reads Terraform-created resources without
  provider plugins, the T1 constraint); **CFN drift / `DescribeStackResources` are stack-scoped → the CDK
  adapter's (T3) path** (and drift alone is incomplete: `NOT_CHECKED` / uncomparable props), N/A for Terraform.
  **Coverage:** the authoritative AWS "Resource types that support Cloud Control API" table (~**1300** public
  types) — distinguish **readable** (`read` handler) / **enumerable** (`list` handler, differs per type) /
  **property-covered** (`GetResource` omits write-only props). Common Terraform corpus well covered; gaps =
  `IAM::Policy` + `Route53::RecordSet`/`RecordSetGroup`; inline `RolePolicy`/`UserPolicy`/`GroupPolicy` are
  Read-but-not-List. **Unsupported/unreadable = FAIL-CLOSED**; and **extra/over-provisioned resources** (the
  moat-critical half — `list_resources` is per-`TypeName`/per-Region) require a **closed-world** predicate
  (deployed set ≡ golden set), enforced primarily by **T7 SCP create-allow-lists** (a closed set of
  CC-listable types + Regions makes an out-of-scope resource unreachable by construction) + exhaustive,
  paginated, Region/global-service-aware, fail-closed union-enumeration — reads alone can't close vector #15. **Read-only IAM** = **`cloudformation:GetResource`/`ListResources`**
  (Cloud Control's IAM prefix is `cloudformation`, verified) with `Resource:"*"`, + the union of in-scope
  types' `handlers.read`∪`list` permissions (least-privilege via `describe-type`); account-B verifier assumes a
  read-only role in account A (SCP-protected; no A→B path). **Go/no-go = GO with conditions** (closed-world via
  T7; per-property gate; corrected IAM) — scope the Phase-1 **Terraform engine-validation** corpus to
  CC-readable types, **without** letting that screen shape the Phase-2 proof corpus (R2/§6 representativeness —
  uncovered families get fallback adapters). Surfaces a **new T7 requirement** (SCP create-allow-list aligned
  to CC-listable types + Regions). Grounded against AWS primary docs (live) + `DECISIONS.md` §1/§5/§8 + brain;
  **cross-model `/review` (Claude + Codex `gpt-5.5` xhigh) caught the closed-world hole + an IAM-prefix error**
  (both fixed + re-reviewed). Decision recorded on #80; the resolved-`[spike]` note is **landed in
  `DECISIONS.md` §1** (founder-ratified), and the follow-up work is **tracked as #141** (E2 verifier-side
  read-coverage enforcement) + **#53** (the T7 closed-world create-allow-list) — not left in comments. (PR #138.)

- **infra-local: relocate under `py/packages/` + docs + nested agent-config (#135).** **Moved `infra-local`
  → `py/packages/infra-local`** so the one Python package that lived at the repo root now sits with its uv
  siblings: the `./py/**` CI glob routes it to the **py** lane automatically, so the ci.yml `infra-local`
  special-case filters, the explicit `uv`/bun workspace member, and the nested-md "py lane despite root" note
  all **drop** (the move removes more special-casing than it adds). `py/packages/infra-local/README.md`
  documents the *why* — the smoke validates **LocalStack's fidelity for the verifier's Cloud Control read
  path** (NOT boto3; the moto/Floci "S3 works ≠ GetResource" precedent + `DECISIONS.md` R3), a **regression
  canary** on the pinned image (already caught `DetectStackDrift` unsupported). Added a **concise, path-scoped
  nested `py/packages/infra-local/CLAUDE.md` + `AGENTS.md` symlink** (loads only when an agent works there —
  grounded in the official Claude Code + Codex nested-loading docs; the first nested constitution in the repo)
  carrying the one non-inferable landmine: never add a `test` script (unlike its siblings — it would run the
  LocalStack smoke in the hermetic `bun run verify` gate and break CI). Cross-model `/review` converged to
  merge. `bun run verify` green. (PR #136.)

- **E17-F1 (#116): boto3/Cloud-Control skill + LocalStack boto3 read smoke + the CLAUDE.md language flip.**
  Closes #116's three remaining parts (its logger task already landed as #132/#133). **(1) Vendored the
  prefer-official boto3 skill** `aws-sdk-python-usage` — first-party AWS (`aws/agent-toolkit-for-aws`, the
  same source as the repo's `aws-cdk`/`aws-cloudformation`/`aws-iam`; the Python peer of the demoted
  `aws-sdk-js-v3-usage`). skills.sh had only off-target community skills, so checked the maintainer's GitHub
  directly (`verify-skill-absence-beyond-the-registry`). It grounds the read-path SDK mechanics — clients,
  typed `ResourceNotFoundException` (the negative-assertion path), paginators (`list_resources`), waiters
  (async drift polling), adaptive retries. Vendored byte-identical to upstream (markdown-only → no script
  surface); no `-a '*'` overshoot; lock `skillPath` matches the sibling pattern. **(2) Re-homed
  `infra-local`'s smoke from TS to boto3/Python** (E17 Python-first): `infra-local` is now a boto3
  LocalStack smoke (an env-server-style py package + bun wrapper) proving the EXACT verifier read path —
  Cloud Control `get_resource` + `list_resources` + the `ResourceNotFoundException` negative assertion —
  against real LocalStack, **negative-controlled** (never a false pass). Retired the TS `smoke.test.ts` + its
  `@aws-sdk` deps (the verifier reads via boto3 now, so the TS smoke tested an SDK the verifier no longer
  uses); one LocalStack home, run via `just smoke`. The read-path seed that **grounds + unblocks #80**. Kept
  OUT of the hermetic `bun run verify` gate (a `smoke` script, not `test`), so the gate stays Docker-free
  while ruff + mypy --strict still cover it. **Validated against the Python craft skills**:
  `python-resilience`/`error-handling` → dropped the hand-rolled retry for botocore's own bounded retries
  (the `use-the-librarys-official-mechanism-not-a-hand-roll` lesson); `python-type-safety` → `Any` at the
  untyped-boto3 boundary is idiomatic; `python-testing-patterns` → pytest fixtures. **Empirical finding
  (`local-aws-emulator-must-prove-read-api`): LocalStack does not serve `DetectStackDrift` ("not currently
  supported by LocalStack") — drift-read coverage is #80/E2 against real AWS.** boto3 reuses the pinned
  workspace dev dep (no new dep). **(3) Finished the CLAUDE.md language flip:** Toolchain reordered
  Python-first (the proof-critical core); the AWS preflight row names `aws-sdk-python-usage`. `bun run verify`
  green **17/17**; both lockfiles frozen-checked. (PR #134.)

- **E17-F4 (#132): Python structlog logger for the proof-critical core.** New `py/packages/logger`
  (`assayops_logger`) — the structlog mirror of the TS `@assayops/logger` (pino) — for the env-server (E5),
  verifier (E2), and reward ledger (E4). JSON one-event-per-line to **unbuffered stdout** (dev `ConsoleRenderer`
  gated on `sys.stderr.isatty()`), ISO-8601 UTC timestamps, `make_filtering_bound_logger` fast filtering +
  `cache_logger_on_first_use`. The load-bearing item is a **deny-by-key redaction censor** (structlog ships
  none): a processor mirroring the TS `SECRET_KEYS` exactly (parity-tested against `ts/.../index.ts`), recursive
  (dicts + lists — closing pino's depth/array gap), mutating the already-copied event_dict **in place** (not a
  clone — the PR #110 mistake). The **unified `ProcessorFormatter` stdlib bridge** folds boto3/uvicorn records
  into the same JSON pipeline + redaction + `trajectory_id` (one shared chain = one censor). **Trust-boundary
  hardening (DECISIONS.md §8), secure-by-default:** botocore/boto3/urllib3/s3transfer clamped to never-below-INFO
  (wire-level DEBUG leaks AWS creds no pattern catches), and `show_locals=False` on the prod exception renderer
  (a KMS-signing crash can't dump key material from frame locals). `trajectory_id` via `structlog.contextvars`
  (tested on the async-emit path AND spawned-coroutine isolation). The redaction + clamp + `show_locals` tests
  were **proven real** by negative controls (disable → tests fail). **Grounded in the official structlog docs**
  (processors / standard-library / contextvars / exceptions / performance / logging-best-practices, structlog
  26.1.0) read this pass, not cached knowledge. **#116's logger task is complete** (decided: KEEP the TS
  `@assayops/logger`, scoped to the consumer/web surface; #116 retains the LocalStack boto3 smoke + boto3 skill).
  `bun run verify` green **17/17** (logger: 53 py tests; both lockfiles updated, frozen-checked). OTel
  export/trace-correlation + prometheus metrics are out of scope (later / #79). (PR #132.)

- **4 wshobson Python skills — vendored (closes #127); the Python-first hardening batch is complete.** The
  four `wshobson/agents` Python skills are now in the committed layer (`.agents/skills/` + `.claude`/`.hermes`
  symlinks + `skills-lock.json` hash-pins): **`python-resilience`** (the verifier's transient-vs-genuine-failure
  rule, `deterministic-verification`, + boto3 adaptive retries — E2/#80), **`python-error-handling`** (parsing
  untrusted IaC/boto3 responses at the verifier/adapter boundary — E2/E3), **`python-configuration`** (typed
  settings + secrets via `pydantic-settings` for the ledger/account creds — E4), and **`python-observability`**
  (the **structlog** logging decision + eval/verifier metrics). Founder elected to **vendor all four now**,
  overriding #127's epic-gating — community-skill vendoring is cheap and auto-loads by relevance — which closes
  the Python-first hardening batch (#124 `Any` ban, #126 config-DRY, #128 Pydantic-v2 skill). All four are
  **markdown-only** (no bundled scripts → no `skills-sync-hygiene` script surface; the `python-resilience`
  "Critical Risk (Gen)" scanner rating is a false positive on example `httpx` calls in a doc). A lean
  `CLAUDE.md` preflight row maps each to its surface. `bun run verify` green 14/14; no `bun.lock`/`uv.lock`
  change (skills-lock.json is separate from the package locks). (PR #131.)

- **Pydantic-v2 skill — authored + vendored (closes #128).** A homegrown Pydantic v2 skill for the contract
  spine (`AssayInc/skills#9`, merged): the load-bearing **`model_dump_json` isn't JCS-canonical** rule
  (canonicalize `model_dump(mode='json')` before signing), `frozen`/`extra='forbid'`/`strict` hardening, the
  `pydantic.mypy` `disallow_any_explicit` gotcha (ties to #124), validators/`TypeAdapter`/`pydantic-settings`.
  Grounded in the official Pydantic v2 docs (load-bearing claims **primary-source-verified**); reviewed Codex
  `gpt-5.5` xhigh **×5 to convergence**; eval = a with/without A/B + the **optimizer-run** trigger set
  (**0/10 false triggers**; recall is the capable-model confound). Vendored into `.agents/skills/pydantic-v2`
  (+ `.claude`/`.hermes` symlinks + `skills-lock.json`) with a `CLAUDE.md` preflight row.

- **#129 (closes #126): config-DRY — shared ruff config hoisted to root via `extend`.** The duplicated
  `[tool.ruff]` (line-length / target-version / lint.select) now lives once in the root `pyproject.toml`;
  each member `extend`s it (proven to inherit the select — a probe fires `ANN401` + `S311` via the root
  config, not silently dropped to defaults). **mypy/pytest stay per-package by design** — mypy has no
  config-merge and the packages run divergent `disallow_any_explicit` strategies (contracts global incl.
  `scripts/`, env-server scoped with tests exempt), so it is intentional divergence, not duplication.
  `bun run verify` green 14/14. (PR #129.)

- **#124: Python type-safety parity — forbid explicit `Any` (mypy + ruff).** The Python lane now mirrors the
  TS `any` ban: mypy **`disallow_any_explicit`** (which `--strict` does NOT enable, confirmed vs the mypy
  docs) + ruff **`ANN401`**; `object` (the `unknown` equivalent) / a Pydantic model at boundaries — proven to
  fire (a probe `Any` is rejected by both). Also added ruff `S`/`LOG`/`G`/`ASYNC` + `ruff format --check`
  gating, cleaned the env-server `dict[str, Any]` → `dict[str, object]` (surfacing the real 3-level
  cloud-state nesting), and `CLAUDE.md` got the `Any` rule + **structlog** named (the pino analog) + a
  Python-skills preflight row. Cross-model `/review` (Claude + Codex `gpt-5.5` xhigh; re-reviewed after the
  scripts-gap fix → ship). Closed **#125**; follow-ups tracked as **#126** (config-DRY), **#127** (4 wshobson
  Python skills, epic-gated), **#128** (homegrown Pydantic-v2 skill). `bun run verify` green 14/14.

- **E1-3 (#28): JCS canonicalization + golden vectors.** The contract spine's canonical-byte recipe is now
  **production on both sides + locked by a golden corpus**: `assayops_contracts.jcs.canonicalize` (PyPI
  `rfc8785`, the account-B **signer**) and `@assayops/contracts` `canonicalize` (npm `canonicalize`, the TS
  **consumer/verify** side) emit **byte-identical** RFC 8785 JCS (`DECISIONS.md` I3 · `record → JCS → UTF-8
  → SHA-256 → KMS Sign`). The locked **`contracts/vectors/jcs-golden.json`** (record → canonical bytes →
  sha256, regenerated by **`just vectors`**, deterministic) covers all four contract records —
  **reward-record** (the signed artifact: both `reward∈{0,1}` + the ns-timestamp digit string), trajectory,
  diff-ir, task-spec (incl. a non-ASCII vector for raw-UTF-8 parity). **Byte-parity is asserted three ways:**
  the Python lane + the TS lane each reproduce the committed corpus (drift-locked) **and** a direct
  Python↔TS subprocess identity test. This is the **inaugural `fixture-change` PR** (the locked-grader
  exception, `DECISIONS.md` §8): adds the `contracts/vectors` CODEOWNERS rule + the turbo
  `globalDependencies` cache-bust; the #115 spike's canonicalize is DRY'd onto the production recipe. **#29
  (the CI regenerate-and-diff / parity gate)** is the remaining E1 tail. `bun run verify` green (14/14).

- **E17-S2 (#115): reward-ledger primitives feasibility spike (PR #122).** A runnable proof that the four
  reward-ledger primitives are real in the Python core, over the canonical `@assayops/contracts`
  `RewardRecord`: **RFC 8785 JCS** via `rfc8785` (byte-exact on the official vectors **and** byte-identical
  to the RFC 8785 reference JS `canonicalize` — the #29 parity shown), the **KMS `Sign`** call shape via
  boto3 (`MessageType=DIGEST`, ECDSA P-256 over JCS→SHA-256), **S3 Object Lock WORM** (Compliance +
  conditional write-once) via boto3, and portable **offline verify** on real `cryptography`. **GO** —
  confirms `DECISIONS.md` I3/4B/§8/T4 with no floor change. Lives in `py/packages/contracts/tests/` (imports
  the real `RewardRecord`; keeps signing/KMS/S3 out of the agent-reachable env-server). Cross-model
  `/review` (Claude + Codex `gpt-5.5` xhigh) caught a real fail-closed gap (`verify_offline` now pins P-256)
  + the Object-Lock checksum requirement; the KMS/S3 contract was verified against the **primary AWS docs**.
  **E4 builds the real account-B ledger** (real KMS validation + a bucket deny-policy; the agent holds no
  `kms:Sign`/`s3:BypassGovernanceRetention`). `bun run verify` green (16 spike tests).
- **E17-S1 (#114): OpenEnv-native Python env-server feasibility spike (PR #121, `b91da87`).** A minimal
  runnable OpenEnv-native Python `create_app`/FastAPI env-server (`py/packages/env-server`) proving four ACs
  against a real uvicorn server + WebSocket clients — concurrent-session isolation, terminal/delayed reward
  shape, the TRL OpenEnv drive seam, and the **non-waivable reward boundary** (the A-side env-server never
  computes the graded reward; account B grades **ground-truth** deployed state by `trajectory_id`, never the
  agent's observation). **GO — OpenEnv-native Python** (vs. a TS wire-only server). Grounded against the
  pinned source (`openenv[core]==0.3.1`, `trl==1.6.0`); cross-model `/review` (Claude + Codex `gpt-5.5`
  xhigh) caught + fixed a tautological boundary proof (now reads `cloud_state.CLOUD` independently). The
  account-B mock's primitives (sorted-key JSON, local ECDSA, in-memory WORM) are **stand-ins #115 makes real**
  (rfc8785 JCS · KMS Sign · S3 Object Lock · offline verify). `bun run verify` green.
- **E17 (#113): Python-first rebaseline — decision gate (PR #118).** Locked the **Python-first
  proof-critical core** (verifier / diff-reward / adapters / ledger / replay / OpenEnv env-server /
  orchestration → `py/packages/*`; TS kept for the public/web/tooling surface) with the **trust floor
  preserved untouched** (§1 account split, §2 locked decisions, §5 15-vector bar, §6 eval rigor). Locked
  the **OpenEnv reward-boundary invariant** non-waivable (§8): the A-side env-server never computes the
  graded reward — the verifier (T1) computes it, the reward ledger (T4) signs + WORM-writes it, joined by
  `trajectory_id`. Rewrote `DECISIONS.md` §4 I1–I7 + §8 + §1 diagram labels, `docs/ARCHITECTURE.md` package
  map + episode flow, `CLAUDE.md` + `README.md` framing + skill-preflight AWS-read→boto3; re-scoped epics
  #3–#8 + contracts #2/#28/#29 + #80; created follow-ups #114/#115 (blocking spikes) + #116/#117/#119.
  Cross-model `/review` (Claude + Codex `gpt-5.5` xhigh) caught the `README` front-line + the
  verifier-vs-ledger signing attribution; the type-checker gate was grounded against the official Astral
  docs (`ty` beta/0.0.x → `mypy --strict` bridge, `ty` the committed target, #119). **No proof-critical
  code moved** (unbuilt). (PR #118; the **#113 epic stays open** until #114/#115/#80/#116/#117/#119 close.)
- **E1-2 (#27): codegen wiring.** Root **`just codegen`** regenerates the committed contract types from
  `contracts/schemas/` — **quicktype** → `ts/packages/contracts/src/generated.ts` (interfaces) +
  **datamodel-code-generator** → `py/packages/contracts/src/assayops_contracts/models/` (Pydantic v2,
  `--use-annotated` for mypy-strict, modular package re-exported via a hand-written `__init__.py`). Both
  generators pinned (`bun.lock`/`uv.lock`) + fixed flags → **deterministic** (byte-identical re-gen; the
  #29 precondition). A cross-language **reward-record round-trip test** (TS serialize → Pydantic parse →
  Py serialize → semantic deep-equal) runs in the py lane via a tsc-checked emitter. Generated `any` (the
  open diff-IR/trajectory fields) excluded from Biome; generated `E501` excluded from ruff
  (`per-file-ignore`) — `tsc` / `mypy --strict` still typecheck both. A guarded post-process pins
  **`reward: 0|1`** into the TS type (quicktype can't emit a numeric literal union; the `DECISIONS.md` §8
  binary invariant — `reward: 2` is a tsc error); the Python `Reward` enum already encoded it. Cross-model
  `/review` (Claude + Codex `gpt-5.5 xhigh`) caught the orphan-module prune + the reward-type gap. JCS +
  golden vectors (#28), CI parity (#29) follow. (PR #112.)

- **E1-1 (#26): the 4 contract JSON Schemas.** `contracts/schemas/{reward-record,trajectory,diff-ir,task-spec}.schema.json`
  (Draft 2020-12, `additionalProperties:false`) as the neutral source of truth, + an ajv validation test in
  `ts/packages/contracts`. Modeling rules: ids / nonces / timestamps / seeds / digests = strings
  (ns-timestamps as canonical no-leading-zero digit strings); `reward` = `enum {0,1}` (binary, per
  `DECISIONS.md` §8 — **not** a continuous double); `tool` = `terraform | cdk`; `diff-ir`
  `modified ⟺ non-empty propertyDiffs`. `contracts/schemas/**` added to turbo `globalDependencies` (a schema
  change now busts the contracts-test cache). Two cross-model `/review` rounds (Claude + Codex `gpt-5.5
  xhigh`) caught the reward-binary frozen-floor deviation and the JCS leading-zero / empty-diff holes.
  Codegen (#27), JCS + golden vectors (#28), CI parity (#29) follow. (PR #109.)

- **E0-4 (#21): repo hygiene.** `.github/CODEOWNERS` (global owner; the DECISIONS.md §8 enforcement arm —
  no speculative locked-grader rules, those land with #28/#56), `.github/pull_request_template.md`
  (documents the `Closes #` convention), and `CONTRIBUTING.md` (branch → focused PR → `bun run verify` →
  `/review` → merge-on-explicit-go; links the README Get started). **Secret scanning + push protection
  enabled** repo-side (the org has GitHub Advanced Security) — proven by a planted push-protection-supported
  secret (Stripe/SendGrid/Slack) **rejected on push** (`GH013`); `google_api_key` is detection-only, so it
  doesn't test push protection. Deferred (ISSUES.md): require-code-owner-review on the `main` ruleset (a
  single collaborator would deadlock solo PRs) + the per-path grader CODEOWNERS rules (#28/#56). (PR #108.)

- **E0-2 (#19): two-lane CI + branch protection.** `.github/workflows/ci.yml` runs the canonical
  `verify` gate (`turbo run typecheck lint test`) on every PR as two parallel, independently
  cache-keyed lanes that don't block each other — **`ts`** (bun/turbo) and **`py`** (uv + turbo); the two
  filters partition all packages by toolchain, so the union is exactly `bun run verify`. `permissions: contents: read`, no secrets/OIDC — **zero account-B creds**
  (DECISIONS.md §1/§8). Branch protection on `main` is **applied** — a repository ruleset requires the
  `ts` + `py` checks + a PR and blocks force-push/deletion. The **codegen-parity gate (#29)** is deferred —
  it's blocked-by #27/#28 and there's no `contracts/` schema yet (a parity check against nothing would be
  an empty verifier). (PR #101.)

- **E0-11 (#86): homegrown AssayOps domain skills.** Five brain-distilled skills authored in `AssayInc/skills`
  (each provenance-cited to a brain page/plan, `skill-creator`-authored, independently reviewed by Codex
  `gpt-5.5 xhigh` two-pass and A/B-evaluated) and vendored into the committed layer: `write-isolated-verifier`
  (the trust boundary), `reward-ledger-worm` (the WORM/KMS reward record), `deterministic-verification` (the
  diff-IR reward), `red-team-exit-bar` (the reward-channel red-team gate), `eval-rigor` (the
  eval-to-performance proof protocol). Each `SKILL.md` hash-pinned in `skills-lock.json`, symlinked into
  `.claude/`+`.hermes/`. Homegrown only where no official pack covers the AssayOps-specific need
  (`localstack-verifier` folded into the official `localstack/skills` pack instead). (PR #92, `330d340`.)

- **E0-10 (#85): prefer-official skill packs.** 25 skills vendored into the committed layer (18 official-vendor +
  3 maintainer-authored Inspect AI + 4 well-adopted community `wshobson/agents`), each mapped to a coding surface: `skill-creator` (anthropics); AWS `aws-cdk` / `aws-sdk-js-v3-usage` /
  `aws-cloudformation` / `aws-iam` (verifier read surface E2 + CDK adapter/drift E3/E11 + A/B role; **E17
  supersedes:** the verifier read is now **boto3/Python**, `aws-sdk-js-v3-usage` → the TS consumer surface);
  `terraform-style-guide` / `terraform-test` (adapter-terraform E3); `openenv-cli` / `generate-openenv-env`
  (env-server E5, from canonical `huggingface/OpenEnv` — `meta-pytorch/openenv` now redirects there);
  `hf-cli` / `trl-training` (trainer E12); `uv` / `ruff` (Python lane); LocalStack `localstack` /
  `localstack-deploy` / `localstack-iam` / `localstack-state` / `localstack-logs` (dev loop E0-3, from
  `localstack/skills`); and Inspect AI `map-inspect-packages` / `reading-logs` / `babysitting-evals` (eval
  lane E13, from `meridianlabs-ai/inspect-skills` — Meridian Labs now maintain `inspect_ai`); and TS/Python craft
  `typescript-advanced-types` / `python-testing-patterns` / `python-type-safety` / `async-python-patterns`
  (well-adopted community `wshobson/agents`, where no official skill exists). Vendored verbatim (byte-identical to upstream), symlinked into
  `.claude/`+`.hermes/`, each `SKILL.md` hash-pinned in `skills-lock.json` (scripts/resources guarded by the
  `skills-sync-hygiene` rule, not the lock); the off-target majority of each multi-skill repo excluded
  (prefer-official, smallest-change). All six `CLAUDE.md` preflight domains now have a vendored skill. (PR #91.)

- **E0-6 (#18): AI-operating layer.** `CLAUDE.md` (the single auto-loaded constitution) + `AGENTS.md`
  symlink, `PROGRAM.md`, `ISSUES.md`, `tasks/{todo,lessons}.md`; the **`verify`-gate + locked-fixtures
  loop**, the "implement the next ready issue" trigger, and the quality bar — adapted to the polyglot,
  verification-infra domain. No `HANDOFF.md` (folded into `CLAUDE.md`); no `ci.yml` (that is E0-2/#19). (PR #84, `4d3fdf7`.)
- **E0-8 (#74): `DECISIONS.md`** — the frozen floor (trust model, locked decisions 1C–T3, I1–I11, the
  15-vector threat bar, eval rigor) ported from the `brain` plans so the repo stands alone. (PR #82.)
- **E0-1 (#17): bootstrap polyglot monorepo skeleton** — Bun + Turborepo TS lane (`ts/**`), UV Python
  lane (`py/**`), shared `typescript-config`/`biome-config`, `contracts/` shells, the `verify` task
  graph, committed lockfiles. (PR #83, `c871960`.)

## Handoff Notes

- **CI landed (E0-2, #19).** `.github/workflows/ci.yml` runs `bun run verify` per PR as two parallel,
  independently cache-keyed lanes (`ts` = bun/turbo, `py` = uv + turbo) that don't block each other,
  with zero account-B creds. Branch protection on `main` is **applied** — a repository ruleset requires
  the `ts` + `py` checks + a PR and blocks force-push/deletion (rulesets need the repo's paid GitHub plan;
  tracked in `ISSUES.md`). The **codegen-parity gate (#29)** is deferred (blocked-by #27/#28; no
  `contracts/` schema yet).
- **Brain sibling + skill layer.** Strategy/research/vision live in `../brain/` (`AssayInc/brain`);
  recall via the **`assay-brain`** skill, built in `AssayInc/skills` (**#73**, closed). As of PR #89
  it's **committed into this repo's skill layer** (`.agents/skills/assay-brain`, symlinked into
  `.claude/`+`.hermes/`, `SKILL.md` hash-pinned in `skills-lock.json`), so every agent here — Codex, CI, a fresh clone —
  gets it with zero setup. It also still ships as a **per-developer install** (`AssayInc/skills` →
  `./install.sh`, symlinked into `~/.claude/skills`) that makes recall work from *any* Assay repo; on a dev
  machine that global copy shadows the committed one (same content). Both resolve `../brain` with zero config
  and degrade gracefully when the brain is absent. The prefer-official cloud/IaC/training/eval packs landed
  in **#85** (PR #91 — 25 skills, each `SKILL.md` hash-pinned in `skills-lock.json`); the five homegrown
  domain skills are authored + vendored (**E0-11 / #86**). `CLAUDE.md` documents the layer as the design.
- **Read order for a new agent:** `CLAUDE.md`/`AGENTS.md` (operating layer) → `DECISIONS.md` (why/rules)
  → `docs/ARCHITECTURE.md` (how/where). The build spine is the `contracts/` schema (E1) — built first
  because it is the join key both lanes and a buying lab verify against.
