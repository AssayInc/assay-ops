# #61 — Spike: LocalStack ↔ real-CFN drift parity (unit economics)

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: the #61 issue comment + DECISIONS.md
> note + PROGRAM.md.

**AC:** Spike closes when (1) the LocalStack↔real-CFN parity finding (DeletionPolicy / nested /
custom resources) + (2) the LocalStack-vs-cloud ratio is recorded (feeds the unit-economics number).

**Grounding (done):** issue body + founder comment (blocked_by #25 overridden; P0 per
docs/priorities.md item 3) · DECISIONS.md R3 / T3 / T9 / 8A / §3 LocalStack-licensing note ·
impl-plan spike #3 (verbatim source) · brain `entities/localstack.md` (the founding open question:
LocalStack-vs-real-cloud share + unit cost/trajectory) + `concepts/environment-economics.md`
(cost anchors: Daytona ~$0.08–0.10/task; HUD $0.25/env-hr) · prior empirical: pinned image
2026.5.4 does NOT serve `DetectStackDrift` (infra-local README, #134) · consumer: #176 ("biases
which drift types the 15 tasks use") + #66 (CDK/T3 CFN-drift read path) + #47 (T9 fidelity-diff).

**Constraints:** spike output = recorded decision + numbers (issue comment + DECISIONS.md note
flagged for ratification + PROGRAM.md), NOT a committed package (lessons: #60/#151 precedent).
Probe scripts live in the scratchpad; method preserved in the issue thread. Real-AWS side:
`assay-iam-spike` profile creds are INVALID (rotated post-#60) → empirical real-CFN confirm is
flagged pending fresh creds; real-CFN semantics grounded in authoritative AWS docs instead.

## Todo

- [x] Ground: issue + comments + timeline + DECISIONS.md + priorities.md + brain + related issues
- [x] Phase A — official docs FIRST:
  - [x] LocalStack docs: CFN coverage (drift APIs? DeletionPolicy? nested stacks? custom resources?) + current release notes (has drift support landed since 2026.5.4?)
  - [x] AWS docs: drift-detection semantics + limitations (supported-type subset, custom resources, nested stacks, DeletionPolicy)
  - [x] LocalStack pricing tiers (license cost folds into unit economics per DECISIONS §3 note)
- [x] Phase B — empirical LocalStack (token present in .env):
  - [x] Start Docker + `just up` the pinned image
  - [x] Probe: CFN stack → out-of-band drift → DetectStackDrift / DescribeStackResourceDrifts / DetectStackResourceDrift (exact error/response)
  - [x] Probe: DeletionPolicy=Retain honored on delete? nested stack deploys? Lambda/SNS-backed custom resource deploys?
  - [x] Measure: wall-clock per representative drift-task episode (create → mutate → Cloud Control grade-read → teardown), n≥5 → LocalStack cost/trajectory
- [x] Phase C — real-CFN side: doc-grounded finding + real-AWS cost/trajectory estimate from AWS pricing; FLAG empirical confirm pending creds
- [x] Phase D — record:
  - [x] Findings comment on #61 (method + numbers + parity finding + ratio)
  - [x] DECISIONS.md §1 resolved-[spike] note (flagged for founder ratification in the PR)
  - [x] PROGRAM.md Right Now / Recently Landed; ISSUES.md if needed
  - [x] Pointer comment on #176 (drift-type bias implications)
  - [x] PR, `bun run verify` green, /review (adversarial, validate findings before acting)
