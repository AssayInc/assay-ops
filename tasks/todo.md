# #155 — E11-1 Terraform-adapter corpus contract (deploy-tag + golden server-posture + round-trip)

> Ephemeral per-session scratchpad (CLAUDE.md). Durable record: PROGRAM.md (Recently Landed) + the PR + GitHub #155.

## Grounding (done)

- Issue #155 (no comments; cross-referenced by #176 — today's P1 pre-T0 slice builds its corpus leg
  "on the #155 contract", so this is on the P1 critical path). Parent: E11 (#12). No blockers.
- DECISIONS.md §1 (T1 read path, #80 resolved spike, fail-closed/closed-world), §4 I11 (residency:
  synthetic fixtures only in-repo), §5 vector #15. `docs/priorities.md` P1 item 4 (#176).
- Skills: deterministic-verification (+ normalization reference: conformance fixtures, intent-bearing
  defaults stay explicit), write-isolated-verifier (golden never derived from the read — no tautology).
- **Empirical probe (LocalStack, pinned image):** Cloud Control `GetResource` on a *plain* S3 bucket
  returns server-defaulted posture: `BucketEncryption` (SSE-S3/AES256, BucketKeyEnabled=false),
  `OwnershipControls` (BucketOwnerEnforced), `PublicAccessBlockConfiguration` (all four true), plus
  `AbacStatus: "Disabled"`. Matches real AWS defaults (grounded live in the AWS user guide:
  SSE-S3 base encryption since 2023-01-05; Object Ownership default = BucketOwnerEnforced;
  BPA on by default for new buckets).
- **Real AWS::S3::Bucket schema (fetched from AWS's public schema bundle):** top-level
  `readOnlyProperties` = Arn, DomainName, DualStackDomainName, RegionalDomainName, WebsiteURL —
  exactly the registry's `read_only_paths`; `tagProperty` = Tags; `AbacStatus` is a real, WRITABLE
  enum property (server-defaulted "Disabled") → goldens must declare it. (Nested readOnly paths
  under MetadataConfiguration/* exist but are out of Phase-1 corpus scope — note, don't code.)

## Deliverables

- [x] **Round-trip smoke** `py/packages/infra-local/tests/test_localstack_grade_roundtrip.py`:
      deploy a tagged bucket (S3 API: `assayops:address` + a user tag + versioning Enabled) →
      `DeployedStateReader.read_resource` (the verifier's production read) → adapter `normalize`
      (default_registry) → `grade_deployment` (synthetic GoldenRegistry) → **reward 1** with the
      posture-declaring golden (declared constants in the test — never computed from the read).
      Negative control: the minimal pre-#155 golden (BucketName+Versioning only) → **reward 0**
      with the diff naming the posture properties (proves non-vacuous, pins the issue's exact gap).
- [x] **Wiring:** infra-local pyproject (mypy_path + pythonpath for verifier/adapter-terraform/
      diff-ir/contracts/replay src; pydantic.mypy plugin; follow_imports=silent overrides mirroring
      the verifier's), package.json workspace deps, infra-local turbo.json (`typecheck` dependsOn
      `^typecheck` — the #152/#31 cache-edge pattern).
- [x] **NORMALIZATION.md:** the corpus-contract note — goldens make server-defaulted intent-bearing
      posture explicit; Phase-1 S3 = BucketEncryption / PublicAccessBlockConfiguration /
      OwnershipControls / AbacStatus; pin a type's golden shape to a real read (the round-trip smoke)
      before authoring tasks of that type.
- [x] **adapter-terraform README:** extend the corpus-contract callout (deploy-tag already there)
      with the golden-posture half + pointer.
- [x] **infra-local README:** scope now includes the adapter↔golden grade round-trip.
- [x] **Trackers:** ISSUES.md #155 entry → resolved; PROGRAM.md Right Now + Recently Landed.
- [x] `bun run verify` green + `just smoke` green (LocalStack) + negative-control proof.
- [x] PR #178 `Closes #155`; 4-pass review (Claude adversarial + testing + maintainability + Codex
      xhigh) — findings validated, fixed (smoke-workflow sibling triggers, fresh fixtures,
      missing-tag real-read test, substrate-honest wording); Codex xhigh re-review on the fixed diff.

## Boundaries honored

- No adapter/verifier production-code change expected (corpus requirements, not adapter bugs).
- Smoke stays out of the hermetic gate (infra-local has `smoke`, never `test` — nested CLAUDE.md).
- Synthetic fixtures only (I11 residency); no real corpus content.
- No fixture-change surfaces (contracts/vectors, tools/red-team untouched).
