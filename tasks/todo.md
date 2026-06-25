# Tasks — todo

Plan-first scratchpad for the current piece of work (see `CLAUDE.md`/`AGENTS.md` → **Agent Operating
Loop**). Ephemeral per-session — durable records go to GitHub/PROGRAM.md/DECISIONS.md, not here.

---

## E3-2 (#35) — Terraform adapter → diff-IR (T2, the A-spike engine) — DONE, awaiting `/review` (branch `e3-2-terraform-adapter`)

**Result:** `py/packages/adapter-terraform` built TDD (40 hermetic tests, all ACs + every founder-required
fail-closed case); `infra-local` tag-bridge smoke proves Cloud Control returns `assayops:address` for
`AWS::S3::Bucket` (ran green on local LocalStack). `bun run verify` green **26/26** (forced, 0-cached);
both lockfiles frozen-clean. Stale-issue `+ CFN drift` dropped (floor §1 wins). Remaining: PR + `/review`.

**Goal:** a new **pure** `py/packages/adapter-terraform` (`assayops_adapter_terraform`) that normalizes
already-enumerated **B-side Cloud Control deployed-state reads** into the landed diff-ir
`NormalizedState(DEPLOYED_READ)` (#34), which `grade()` diffs against the golden (#75). No boto3, no
plan/state/provider, no discovery — fail closed, deterministic.

**Grounding / reconciliation (issue vs DECISIONS + brain + founder spec):**
- Issue body "Cloud Control + **CFN drift**" is **STALE** → DECISIONS.md §1 (E3-4 / #80) locks **Terraform =
  Cloud Control `GetResource`/`ListResources` ONLY** (Terraform creates no CFN stack ⇒ drift has nothing to
  target; CFN drift = the CDK/T3 path, #66). Frozen floor wins → comment on #35.
- #35 = **pure normalization**. The boto3 read + closed-world enumeration = **#30/#141/#53**; reward→ledger
  wiring = **#32**; the malicious-provider/poisoned-state fixtures = **#56** (which "feeds #35" — not built, so
  #35 proves the property with its own representative fixture).
- Address bridge (founder decision): reserved **`assayops:address`** tag, under a **per-type support registry**
  (the #80 matrix), fail-closed. Untrusted tag value, validated as a logical address.

**Design:**
- Input: `Iterable[DeployedResourceRead | UnreadableResource]` (settled, already-enumerated) + a
  `BridgeRegistry`. Output: `NormalizedState(DEPLOYED_READ)` or a fail-closed `AdapterError`.
- Per supported type: read **exactly one** case-sensitive `assayops:address` from the schema-declared
  `tagging.tagProperty` (default `Tags`); value untrusted → validate as logical address → `address`; drop
  **only** that bridge tag; keep user tags sorted; drop schema `readOnlyProperties`; sort set-valued props.
- Fail closed: missing/duplicate/malformed/case-wrong/reserved-`assayops:*`/wrong-shape tag, unknown/
  unsupported type, unreadable record, duplicate logical address. Extra resources → emitted (grade→`added`),
  never filtered away. Cloud Control `Identifier` / natural keys are **never** the address.
- NEVER run terraform / load providers / read `.tfstate` / read plan JSON / discover by tag.

**TDD checklist (each → a failing test FIRST):**
- [ ] happy: tagged read → `NormalizedResource(address=<tag>)`; `grade` vs matching golden → reward 1 (AC1 / NSYNC)
- [ ] drop server-filled `readOnlyProperties` (Arn/DomainName/…); keep intent (VersioningConfiguration)
- [ ] address tag: missing / duplicate / malformed-value / case-wrong → fail closed
- [ ] reserved `assayops:*` (non-address) tag → fail closed
- [ ] wrong-shape `tagProperty` (not a list of `{Key,Value}` strings) → fail closed
- [ ] unsupported/unknown type → fail closed (AC4); `UnreadableResource` record → fail closed
- [ ] non-default `tagProperty` (registry-configurable) read correctly
- [ ] user tags preserved + sorted; only the bridge tag stripped; no-user-tags drops the tag property
- [ ] AC2: deployed matches golden, a differing "plan" is never an input → reward 1 (state-only, no plan dep)
- [ ] AC3: a poisoned `.tfstate` / malicious-provider fixture is never an input → reward unaffected
- [ ] determinism: shuffled reads/tags → identical `NormalizedState`; two reads of one correct deploy → same IR
- [ ] duplicate logical address across reads → fail closed
- [ ] extra deployed resource → `grade` → `added` (never filtered)
- [ ] infra-local smoke: real Cloud Control `GetResource` returns `assayops:address` at `tagProperty` for
      `AWS::S3::Bucket` (#80; runs in `localstack-smoke.yml` CI — no local `LOCALSTACK_AUTH_TOKEN`)

**Wiring:** new uv + bun workspace member (mirror diff-ir `pyproject`/`package.json`; resolve diff-ir +
contracts via `mypy_path`/`pythonpath`). `uv lock` + `bun install` (**both** lockfiles — the bun-lock lesson),
verify with `bun install --frozen-lockfile`. `bun run verify` green.

**Close-out:** README + docstrings (flag the bridge convention); comment #35 (CFN-drift staleness + the
`assayops:address` bridge + a corpus deploy-tagging note for #76/#13); update `PROGRAM.md`/`ISSUES.md`;
cross-model `/review` (Claude + Codex `gpt-5.5` xhigh); focused PR `Closes #35` (leaf — E3 epic #4 stays open).
