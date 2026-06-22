# AssayOps — DECISIONS (the frozen floor)

> **⚠️ SETTLED — flag, don't silently deviate.**
> Everything in this file is either a **locked** architecture decision or a load-bearing
> **implementation** choice. It was ratified by the gstack plan reviews (`/plan-eng-review`,
> `/plan-ceo-review`) and a two-reviewer adversarial pass — **Claude Opus 4.8 (max)** + **Codex
> GPT-5.5 (xhigh)** — both of whom affirmed the trust model is faithfully implemented and all
> tasks are mapped. **Do not re-litigate it and do not quietly work around it.** If your task
> looks like it requires deviating from a decision here, **stop and flag it** (comment on the
> issue / raise it) — never code around it. *A plausible-but-wrong verifier is worse than none;
> when unsure, prove it or flag it.*

This is the **frozen floor every agent reads before touching code**: the load-bearing *why* and
*rules*, distilled out of the `brain` plans and ported into this repo so they're reachable here
**without checking out the sibling `brain` repo**.

- **DECISIONS.md (this file) = *why / rules*.** The settled decisions, the trust boundary, the
  threat bar, the eval bar, the non-negotiables.
- **`docs/ARCHITECTURE.md` (E0-1, #17) = *how / where*.** The structural package map + episode
  data-flow. It **links here** for the trust model rather than restating it — **no duplicated
  trust model** across the two.
- **`assay-brain` skill (E0-7, #73) = deep recall.** On-demand query of the full `brain` wiki /
  `raw/plans/` / articles / VISION — needs the `brain` sibling + `qmd`, degrades gracefully. This
  file is the always-on floor; `assay-brain` is the rest of the iceberg.

**The bar this file must clear (AC):** a fresh agent given *only* `assay-ops` can explain **why
the verifier never runs the agent's `cdk synth` / `terraform plan`** — without `brain`. See §1.

### Provenance convention

Each decision is tagged and cited to its source plan in the `brain` repo (see [Sources](#sources)):

- **[locked]** — decided upstream in a locked plan; cited. Do not re-open.
- **[impl]** — an implementation choice made in the implementation plan (research-backed); cited.
- **[spike]** — a known unknown requiring a timeboxed investigation before commit.

When a decision and the brain plan ever conflict, **the brain plans win** — fix this file.

---

## 1. Trust model (the moat, in one diagram) — *the rule that defines the product*

**[locked — eng-arch §Trust model]**

```
 ACCOUNT A — agent trust domain (creds scoped to playground only)     ║  ACCOUNT B — verifier trust domain (agent: ZERO creds/network)
 ───────────────────────────────────────────────────────────────     ║  ──────────────────────────────────────────────────────────
 Direct orchestration (A-spike) → Harbor at Phase-2 scale [3A,T12]    ║
   │ Daytona sandbox / LocalStack-in-container per episode            ║
   │ (real-AWS sandbox account from the Orgs pool for the eval slice) ║
   ▼                                                                  ║
 OpenEnv env server (Python) ◀─ step/reset/state ─▶ Agent (policy)    ║
   │ agent deploys; agent synth/plan runs HERE, in a disposable       ║
   │ sandbox, treated as untrusted data  [T1]                         ║
   ▼                                                                  ║
 DEPLOYED resource state (just cloud resources = data)                ║
   │                                                                  ║
   └── deployed state ── READ-ONLY cross-account ───────────────────▶ ║  WRITE-ISOLATED VERIFIER (Python)  [1C, T1]
        (agent has no path here)                                      ║    • regenerate AssayOps golden target (code+seed) [2A]
                                                                      ║    • per-tool adapter → normalized diff IR [6A]
                                                                      ║    • NEVER runs agent synth/plan; reads state only [T1]
                                                                      ║    • transient/genuine classifier + K-run quarantine [7A]
                                                                      ║          │ reward∈{0,1} + diff report
                                                                      ║          ▼
 Trajectories (obs/actions) ──────────────┐                           ║    KMS-SIGNED, S3-Object-Lock WORM REWARD RECORDS [4B]
                                          │                           ║    keyed by trajectory_id, in account B
                                          ▼          ◀── READ-ONLY ────╫──────────┘
                              Python TRAINER (join on trajectory_id; contract via codegen [5A])
                                • SFT on gold trajectories
                                • headline lift on OOD/external-anchor slice [T2]; ≥3 seeds, threshold, contamination check
```

### The boundary rule (the one paragraph everything else serves)

The boundary (`║`) is an **AWS Organizations account/trust-domain split** (decision **T3**):

- **Account A** = a vended/reset **sandbox** account — the agent's trust domain; its creds reach
  the playground **only**.
- **Account B** = the **verifier/reward** account — the agent has **zero credentials and zero
  network path** to it. **There is no A→B trust path** [1C].
- The verifier runs **entirely in B**, reads the **deployed resource state read-only** across the
  boundary (Cloud Control `GetResource`/`ListResources` + CloudFormation drift), and **never runs
  agent code**. Reward is computed and stored in B and reaches the trainer **only as read-only,
  KMS-signed records** [4B]. **Reward never depends on executing agent code.**

### Why the verifier never runs the agent's `cdk synth` / `terraform plan` *(the AC bar — self-contained)*

This is the single most important rule in the system, and it must be explainable from this repo alone.

- Running the agent's `cdk synth` or `terraform plan` means **executing agent-authored code inside
  the trusted grader.** That is *exactly* the reward-hacking surface the product exists to close —
  see threat vectors **#4 (CDK-synth escape)** and **#5 (terraform provider-plugin abuse)** in §5:
  malicious construct code or a hostile provider plugin runs with the grader's trust and forges a
  passing reward. This was the one **architecture hole** the eng-review closed (the verifier was
  *implicitly* executing agent code via synth/plan); the fix is decision **T1**.
- So instead, the flow is inverted: the agent's `synth`/`plan` and the deploy run **A-side, in a
  disposable sandbox, treated as untrusted data.** The agent **deploys** real resources. The
  verifier in **account B** then reads only the **deployed resource state** (read-only,
  cross-account) and compares it against AssayOps's **independently regenerated golden target**
  (code+seed) [2A], producing `reward ∈ {0,1}` + a diff report.
- Because the grader shares **no process, no filesystem, no account, no network** with the agent,
  the reward is **execution-grounded and un-gameable** — that is the moat. The headline claim is a
  **passed attack list** (§5), never the word "provably."

---

## 2. Locked architecture decisions (1C–T3)

**[locked — eng-arch §Locked decisions]** — these are settled. The `T1`/`T2`/`T3` rows are the
Codex-added decisions (they also appear as tasks in §3; the overlap is intentional).

| #  | Decision | Source |
|----|----------|--------|
| **1C** | Verifier isolation = separate AWS **account/trust domain** (Orgs); agent zero creds/net to B | Arch 1 |
| **2A** | Ground truth = **reproducible ephemeral target** (code+seed); reward = zero **normalized** diff | Arch 2 |
| **3A** | **Harbor for rollouts only** (Daytona-first / Modal-GPU); reward owned by account-B verifier | Arch 3 |
| **4B** | Reward delivery = out-of-band **KMS-signed, S3 Object Lock WORM** records, read-only to trainer | Arch 4 |
| **5A** | **One contract schema** → codegen TS + Python (no hand-maintained dual types) | CQ 5 |
| **6A** | **Per-tool IaC adapters** → one normalized diff IR → shared reward core (TF A-spike = engine) | CQ 6 |
| **7A** | Determinism = transient/genuine classifier + K-run reproduce + **quarantine** flaky tasks | Test 7 |
| **8A** | Episode lifecycle = **snapshot-restore + delta apply**; LocalStack-first | Perf 8 |
| **T1** | Verifier grades **deployed state read-only** vs AssayOps's golden; **never runs agent synth/plan** | Codex |
| **T2** | Headline lift on an **OOD slice** (hand-authored + external anchor); same-generator secondary | Codex |
| **T3** | **Real AWS from day one** for eval/proof slice + fidelity-diff; bulk on LocalStack; Orgs account pool (Control Tower AFT) | Codex |

**Noted (not re-litigated):** Harbor integration **deferred to Phase-2 scale** (the A-spike uses
direct orchestration). 4B signing **kept** (Codex called it premature; chosen deliberately for
audit-grade provenance as a selling point, reaffirmed by the KMS + Object Lock account design).

---

## 3. Locked tasks (T1–T13) → Epic mapping

**[locked — eng-arch §Implementation tasks; mapping from impl-plan §6]**

**Phases (T0-relative)** [proof-first §Recommended approach]. The build clock is **~13–15 weeks from
T0** (= team closed: a verbal yes + a start date + a named first deliverable); the windows **overlap by
design** (parallel lanes — a small team runs ≤2 phases at once). The `Phase` column below maps to:

- **0 — Gate (pre-T0):** close the team + scout; the build proceeds **regardless of the Henry intro**.
- **1 — A-spike + substrate (wk 1–5):** the write-isolated verifier + deterministic replay on a small
  **Terraform** slice (engine validation, **not** the CDK proof corpus), plus the foundational substrate
  (contracts, reward ledger, account infra + T7); exit = the **§5 15-vector bar** (proof-first's 6
  starter attacks → eng-arch's 14 → the read-side 15th) each demonstrated to fail + a measured LocalStack
  cost/trajectory.
- **2 — Ship the corpus (wk 4–10), separable:** **N ≈ 30–50** CDK drift&debug tasks; if the window
  slips, cut to the **~30** floor, or drop to **proof-only** (private eval, skip the public leaderboard).
- **3 — Lift demo (wk 8–12):** **SFT** on gold trajectories; **hard-gated on the RL/eval owner**; the
  proof must clear the §6 bar **before** Phase 4.
- **4 — Pitch (wk ~13–15):** **gated on the proof clearing the bar, not a fixed date.**

| Task | What | Prio | Epic | Lane | Phase |
|------|------|------|------|------|-------|
| **T1** | Verifier core: account-B, deployed-state read-only grading, normalized-diff IR, **never runs agent synth/plan** | P1 | E2 | A | 1 |
| **T2** | Terraform adapter → IR (the A-spike engine) | P1 | E3 | A | 1 |
| **T3** | CDK adapter (synth in disposable A-side sandbox; verifier reads deployed resources/CFN) | P2 | E3 | A | 2 |
| **T4** | Reward ledger: KMS-signed + S3 Object Lock WORM, append-only, trajectory-keyed, cross-account read-only | P1 | E4 | A | 1 |
| **T5** | Contract schema (JSON Schema) + TS/Python codegen + reward-record round-trip test | P1 | E1 | A | 1 |
| **T6** | Account infra: Orgs OUs + sandbox-account pool (Control Tower AFT / StackSets) + verifier account | P1 | E8 | B | 1 |
| **T7** | **Account-A guardrails: SCPs + budget caps + region/resource limits (cost-bomb defense)** | **P1, BLOCKING** | E9 | B | 1 |
| **T8** | Determinism policy: transient/genuine classifier, K-run reproduce, quarantine non-deterministic tasks | P1 | E6 | A/C | 1 |
| **T9** | Episode lifecycle: snapshot-restore + delta apply; LocalStack bulk + real-AWS eval slice + fidelity-diff sample | P1 | E7 | C | 1 |
| **T10** | Threat-model red-team suite (the 15 vectors in §5) — the Phase-1 exit bar | P1 | E10 | A/B | 1 |
| **T11** | Eval harness: OOD/external-anchor headline + baselines + seeds/threshold/contamination/determinism | P1 | E13 | D | 2→3 |
| **T12** | Orchestration: direct for the A-spike; adopt Harbor at Phase-2 scale (spike-gate fallback) | P2 | E7 | C | 1→2 |
| **T13** | Task-authoring pipeline: authoring rate, gold-trajectory QA, anti-shallow-template-variation | P2 | E11 | D | 2 |

All 13 locked tasks are mapped: **T1→E2, T2/T3→E3, T4→E4, T5→E1, T6→E8, T7→E9, T8→E6, T9/T12→E7,
T10→E10, T11→E13, T13→E11** — plus the env-server (E5), trainer (E12), and GTM (E15) surfaces.

> **Lanes (parallel worktrees) [eng-arch §Parallelization].** A = the IP · B = account infra (Orgs +
> pool + T7) · C = episode lifecycle/orchestration (**waits on B's account pool, T6**) · D = eval-task
> authoring. **A and C both touch the verifier/episode boundary — coordinate or sequence; start C only
> after B lands the account pool.** Launch A + B + D in parallel.

> **T7 is P1-blocking [locked — eng-arch §Failure modes].** Isolating the verifier does **not**
> isolate the agent's *spend*. Account A can run cost-bombs / quota exhaustion / region-spanning
> resources, silent until the bill. **No real-AWS episode runs until T7 (SCP + budget + region
> caps) exists; until then, all A/C work runs on LocalStack only.**

> **LocalStack now requires an auth token [2026-03-23 single-image change].** The free tokenless
> community edition was retired; the licensed "LocalStack for AWS" image needs `LOCALSTACK_AUTH_TOKEN`
> (a CI/local **secret, never committed**). This does **not** change the **LocalStack-first /
> bulk-on-LocalStack** substrate (8A / T3 / T9). The free **Hobby** tier (non-commercial use, includes
> CI) covers the current R&D stage — the choice for now; clearly-commercial / production use moves to a
> paid plan (Base+), whose cost folds into the **T7 budget** and the **LocalStack↔real-CFN drift /
> unit-economics spike**. Free-emulator
> alternatives (moto/Floci/MiniStack) were rejected: they don't serve the Cloud Control `GetResource`
> read path the verifier (T1) grades against.

---

## 4. Implementation decisions (I1–I11)

**[impl — implementation-plan §0; language split rebaselined by E17, 2026-06-22]** — new calls made
*beneath* the locked architecture (it adds no new architecture; it specifies *how* to build what the
locked plans already decided). The core is **Python-first**: the **proof-critical core is Python**
(verifier, diff/reward core, IaC adapters, reward ledger, deterministic replay, the OpenEnv env-server,
episode orchestration) — Python's home turf (boto3 deployed-state reads + diff normalization) and the
home of the one hard ecosystem anchor, **train/eval** (TRL · Inspect AI · OpenEnv). **TypeScript stays
where it has a product/distribution job:** the generated public `@assayops/contracts`, `assay-web`,
dashboards, npm consumers, optional CDK/task-authoring tooling. Bridged by **one codegen'd contract
schema** [5A] — a neutral JSON Schema neither language owns. *E17 (the 2026-06-22 polyglot
reconsideration) supersedes the implementation-plan's original "TypeScript for the IP"; the moat is
language-independent (§1/§8), so the pivot leaves the trust floor untouched. Raw-plan + wiki sync is a
tracked follow-up.*

**I1 — One polyglot monorepo `assay-ops` + 2 satellite repos** (`assay-cloud-org`, `assay-web`).
Co-locate the TS↔Python seam so a contract change lands atomically with both generated sides in one
PR; split out only the two seams with a *different blast radius / audience* (`assay-cloud-org` can
nuke real AWS accounts; the leaderboard is a public surface). *[impl — founder choice 2026-06-17]*

**I2 — Python (UV) owns the proof-critical core lane; TypeScript (Bun + Turborepo + Biome) owns the
consumer/tooling lane; Turborepo stays the single umbrella** driving both. UV owns the core packages'
deps + venv (mypy · ruff · pytest); Bun/Turbo/Biome own the TS surface (tsc · Biome · `bun test`). One
task graph + cache keeps `turbo run typecheck lint test` as the single `verify` gate across both lanes —
the Python packages expose it via thin wrapper `package.json` scripts → `uv run`; no Nx/Bazel/Pants.
Turborepo is language-agnostic (vercel/turborepo#1077), so it orchestrates a Python-majority repo
unchanged. *[impl — rebaselined by E17: UV is the core, Turbo the umbrella]*

**I3 — Contract schema = JSON Schema (Draft 2020-12) source of truth** — neutral and public, neither
language owns it. Codegen roles: `datamodel-code-generator`→**Pydantic v2** is the **internal core
contract** (the Python verifier/ledger import it; runtime-validated at I/O boundaries);
`quicktype`→**TypeScript** is the **public/web binding** (`@assayops/contracts`, `assay-web`, npm
consumers). The **account-B verifier (Python) signs** over **RFC 8785 JCS canonical JSON** (record → JCS
→ UTF-8 → SHA-256 → **KMS asymmetric ECDSA P-256, `MessageType=DIGEST`**); the optional TS side
**verifies** the same bytes — so byte-parity is **Python-signer ↔ TS-consumer**. Protobuf is
*disqualified*: its spec says serialization is non-canonical, which breaks KMS signing across runtimes.
JCS pins every serialization degree of freedom and ships a cross-language conformance suite. **Zod, if
used, is TS-app ergonomics only — never the canonical contract source.** *[impl — realizes 5A + 4B;
codegen roles rebaselined by E17]*

**I4 — Track work in GitHub Issues + Projects v2** in `assay-ops` (issue-type `Epic` via label,
sub-issues, dependencies, roadmap; all `gh`-CLI-driveable). Zero new tool/auth/sync for a 3-person
GitHub-native team. Revisit Linear at ~8 people / ~300 active issues. *[impl — founder choice]*

**I5 — OpenEnv-native Python env-server** (`create_app` / FastAPI) implementing the OpenEnv HTTP/WS wire
contract (`/reset`, `/step`, `/state`, `/health`, `/metadata`, `/schema`, `/ws`…) — matching the
reference shape that TRL's OpenEnv integration drives. It runs in **account A (agent-reachable), so it
never computes the graded reward**: the **OpenEnv reward-boundary invariant** (§8, *non-waivable*) —
`step()`/terminal reward is at most a non-graded/zero shaping signal; the graded reward is the account-B
verifier's KMS-signed WORM record, joined by `trajectory_id`, and the trainer trains on *that*, never the
env's `step()`. `/schema` serves the **canonical JSON Schemas / generated artifacts**, not types derived
from a TS app. *[impl — rebaselined by E17 to OpenEnv-native Python; supersedes the TS-first env plan]*

**I6 — Trainer stack = TRL v1.0** (`SFTTrainer` + LoRA) on **Qwen3-Coder-30B-A3B-Instruct**
(Apache-2.0) primary / **Qwen2.5-Coder-7B/14B** dense baseline; eval via **Inspect AI** (custom
`Scorer` = the deploy-verifier). HF-ecosystem-native end-to-end; Apache-2.0 avoids license landmines
in a commercial deal; Inspect gives native pass@k + clustered stderr. *[impl — realizes Phase-3]*

**I7 — Node / the CDK Toolkit is a *toolchain* dependency, not a core-language forcing function.** The
`cdk` CLI (jsii needs a Node runtime to process constructs) is invoked as a subprocess — exactly like
`terraform` (Go) or `git` (C) — and does **not** make any AssayOps component TypeScript. **AWS CDK
Python is first-class**, so trusted CDK task/golden authoring can be Python or TS (a separate call kept
out of the verifier-language decision); the verifier **never runs the agent's `synth`/`plan` regardless
of language** [T1, §1]. Node stays installed for the CDK Toolkit; the core is Python. *[impl —
rebaselined by E17; corrects the earlier "CDK forces TypeScript" category error]*

**I8 — Pin everything:** `oven/bun:1.3.x`, `ghcr.io/astral-sh/uv:<ver>`, `openenv[core]==0.3.x`,
model revisions by commit hash. OpenEnv is pre-1.0 ("expect rough edges"); Bun
workspace-in-Docker `--frozen-lockfile` issues; reproducible eval requires pinned model revs. *[impl]*

**I9 — Cleno is a template, not a clone.** Scaffold `assay-ops` fresh, lifting Cleno's TS tooling
skeleton (Bun+Turbo+Biome + shared `typescript-config`/`biome-config` packages) and its
**AI-operating layer** (`CLAUDE.md` + `AGENTS.md` symlink, PROGRAM.md, ISSUES.md,
`tasks/{todo,lessons}.md`, the **`verify`-gate + locked-fixtures loop**); `assay-web` reuses only
Cleno's Bun/Biome + AI-operating-layer conventions, **not** its TanStack web app (see I10). Cleno is
TS-only + a full-stack web app — wrong spine for a polyglot backend-services + Python-trainer core;
a wholesale clone+force-push is demolition, not a head start. The portable value is its config +
conventions + the **verifiable-loop discipline** ("the agent never edits the grader" — which *is*
the AssayOps write-isolated-verifier thesis). *[impl, founder input]*

**I10 — `assay-web` = Next.js (App Router) on Vercel**, not TanStack Start. Leaderboard = a React
component using **TanStack Table** (headless) over published JSON on a **prerendered/ISR** page;
**three-tier split** — public Next reader ← versioned results store (Git-JSON / HF Dataset) ←
**private Inspect-AI grader** (the E13 harness behind a FastAPI/queue wrapper; verifier + gold never
deployed to Vercel). The leaderboard is a `/leaderboard` route *inside* `assay-web`, **not** its own
repo. Evidence: 6/8 benchmark-company sites are Next-on-Vercel; every Python-eval leaderboard (HF,
SWE-bench, Terminal-Bench) keeps the grader **out** of the web app — the same write-isolation
boundary AssayOps sells. *[impl, founder-driven + analog research]*

**I11 — No application database and no auth provider through the proof (Phase 0–3).** The reward
ledger's system of record is **S3 Object Lock (WORM)**, not a DB; trajectory/gold corpus + held-out
eval = **S3 / private HF Dataset**; task specs + published results = **Git**; analysis is
**DuckDB/SQLite over the JSONL/Parquet** (a query engine over files, no standing service). Core
"auth" = **AWS IAM + KMS + an env-server bearer token**. A DB/auth appears **only at Phase-2
productization**, scoped to where it's needed: default to **submission-by-PR** (Git = store +
identity + audit, SWE-bench pattern); if richer UX is wanted, **Drizzle + plain Postgres** + **GitHub
OAuth (Auth.js)** — *not* Convex/Supabase-platform/Clerk/BetterAuth (WorkOS only if a lab later
requires SAML/SSO). **We do NOT open-source the leaderboard or
the site.** The RL-env companies open their **harness / environment / verifier framework** to drive
adoption — copying their "open" would mean **open-sourcing the moat**. The **only** genuinely-public
artifact is the **result/submission schema** (`@assayops/contracts`), plus *optionally and later* a
small public sample task split. Everything else — **site code, held-out eval set, gold trajectories,
verifier internals** — private (the moat). A mutable DB row for rewards would break the
tamper-evident-ledger trust model that *is* the product. *[impl, founder Q 2026-06-18 + wiki analogs]*

---

## 5. Threat model — the Phase-1 exit bar (the 15 vectors)

**[locked — eng-arch §Threat model; 15th promoted per impl-plan §13 review C1]**

This 15-row table is the **canonical Phase-1 exit bar**. Its **`Attack vector` column is kept
verbatim-identical with issue #56 (E10-1)**'s 15-vector list (#56 owns the red-team fixtures in
`tools/red-team`); the *Defense* and *Source* columns are annotations carried from the
eng-architecture plan. It is the 14 eng-arch vectors **+ read-side state-read spoofing** (the
moat-defeating 15th, promoted out of spike #63). **Any change to the vectors is made in #56 in a
`fixture-change` PR and mirrored here** — do not edit it casually.

| #  | Attack vector | Defense | Source |
|----|---------------|---------|--------|
| 1  | fs write to grader path | 1C separate account/FS | review |
| 2  | conftest/env-var injection | verifier diffs out-of-band, never runs agent test code | review |
| 3  | monkey-patch evaluator / fake exit codes | 1C out-of-process in B; T1 reads deployed state | review |
| 4  | CDK-synth escape | T1: verifier never synths; synth runs A-side disposable | **Codex** |
| 5  | terraform provider-plugin abuse | T1: verifier reads deployed state, not agent's plan | **Codex** |
| 6  | network MITM on reward | 4B no in-band reward; no agent net path to B | review |
| 7  | state-file edit ("looks clean") | 2A verifier regenerates golden + reads B-side state | review |
| 8  | timer manipulation | verifier clock in B | review |
| 9  | reward-record forgery/overwrite | 4B KMS-sign + WORM; zero agent creds to B | review |
| 10 | cross-account assume-role (A→B) | 1C no A→B trust | review |
| 11 | IAM escalation in account A | SCP guardrails (T7) | **Codex** |
| 12 | network egress / data exfil | Daytona net-block + SCP egress controls | **Codex** |
| 13 | cost-bomb / quota / region-span | SCP + budget caps + region limits (T7) — **critical gap today** | **Codex** |
| 14 | benchmark / eval leakage | OOD held-out + private eval + contamination check (T2) | **Codex** |
| 15 | **read-side state-read spoofing** — crafted IaC that fools the verifier's *read* of deployed state into a false "in-sync" (the moat-defeating 15th; promoted from spike #63 per review C1). KMS/WORM protect the **write** path; this protects the **read** path. | verifier read-path hardening: golden regenerated independently (2A) + deployed-state read coverage; the E10 read-path test set | **review C1** |

> **R1 kill-criterion [locked — proof-first §Risks; impl-plan §10]:** the red-team suite (T10/E10)
> is the gate. **Any open vector ⇒ STOP.** Do **not** make any public or proof claim on a gameable
> reward (the #1 thesis risk) — harden first. The exit-bar artifact (E10-3) is what gates Phase 2.

---

## 6. Eval rigor (the proof must clear this bar)

**[locked — eng-arch §Eval design + proof-first §Success Criteria; rollout floors from impl-plan §7]**

The proof is an **eval-to-performance lift** on an open model SFT'd on AssayOps environments. A
number without this rigor is dismissible by a post-training lead in 60 seconds — so it is mandatory.

- **Headline metric:** lift on an **out-of-distribution (OOD) slice** — hand-authored tasks
  *structurally different* from the generator **+ an external anchor the training never touched**
  (cite-only SWE-InfraBench, no task reuse). Same-generator held-out is a **secondary** number.
- **Baselines:** same model **zero-shot**; same model **SFT'd on non-AssayOps infra data**; **and**
  **synthetic-task-gen / rejection-sampling** baselines (prove AssayOps's environments beat cheap
  alternatives).
- **Rigor (all required):**
  - **≥30 held-out tasks.**
  - **≥3 seeds** with variance (floor **n ≥ 8 rollouts/task**).
  - **Clustered standard errors** (cluster by task).
  - **Pre-registered threshold ≈ +8–10 points** pass-rate over the strongest baseline.
  - **Contamination check** — post-cutoff fresh configs/regions/names, no train/test overlap,
    private held-out state never published.
  - **Verifier-determinism check** — golden ×K → identical reward.
- **Open [spike]:** corpus scale — 30–50 tasks is thin for low-variance lift; pair the first proof
  with the procedural-generation **scaling story** for the lab conversation.

---

## 7. Risks & kill-criteria (R1–R6)

**[locked — proof-first §Risks & Kill Criteria]** — R1 is the load-bearing one (see §5).

- **R1 — Verifier still tamperable at end of Phase 1.** Any open attack-list item ⇒ **STOP**; no
  claim on a gameable reward. *(The §5 gate.)*
- **R2 — Frontier models score too high** (best model > ~45% on our tasks, above the 34%
  SWE-InfraBench anchor) ⇒ tasks too easy / gap closing ⇒ re-scope harder.
- **R3 — LocalStack fidelity too low to be lab-credible** ⇒ move fidelity-critical cases to capped
  real cloud; test explicitly in Phase 1 + scouting *(spike: LocalStack↔real-CFN drift parity)*.
- **R4 — No measurable lift in Phase 3** (< threshold after budgeted iterations) ⇒ proof failed;
  diagnose (data quality / task difficulty / eval design) **before** spending the Henry intro.
- **R5 — Team doesn't close** (no RL/eval owner) ⇒ founder backstops (slower) or lead GTM with the
  benchmark alone; Phase 3 is **hard-gated** on the RL/eval owner.
- **R6 — Henry routing fails** ⇒ build proceeds (pitch is gated on the artifact, not on Henry);
  open parallel buyer paths.

**Benchmark posture & the 12-month flywheel [locked — roadmap].** **D1=C — private now, publish
gated:** public benchmark publication is decided right after the first Anthropic conversation (**gated on
safety + whether the warm/Henry path materialized**); never open-source the harness/verifier/corpus/site
(I11). The roadmap also commits **three directional bets** beyond the proof — *distinct from the
build-epics E1–E3* — (1) the **lab-agnostic / second-buyer** posture (any first exclusive is
**time-limited**); (2) the
**ELT data-pipeline second act**, architecture-ready via the 6A adapters, built only **after** the cloud
proof; (3) **publishing the verifier-isolation design** as thought-leadership — the safe category-stake
(it leaks nothing, unlike the corpus) and the early-attention move. *Rejected:* leading with a public
benchmark; a single-lab-only bet; skipping ELT.

---

## 8. Agent non-negotiables checklist

The hard rules. Violating any of these is a trust-boundary break, not a style nit. **If a task
appears to require breaking one, stop and flag it — don't code around it.**

- [ ] **The verifier NEVER runs the agent's `cdk synth` / `terraform plan`** (or any agent code).
      Synth/plan runs A-side in a disposable sandbox, treated as untrusted data. The verifier reads
      **deployed state read-only** and compares to the independently regenerated golden. **[T1, §1]**
- [ ] **The verifier runs in account B; the agent has zero creds + zero network to B; there is no
      A→B trust path.** **[1C]**
- [ ] **Reward never depends on executing agent code.** `reward ∈ {0,1}` from a normalized diff. **[T1, 2A]**
- [ ] **Reward records are KMS-signed + S3 Object Lock (WORM), append-only, trajectory-keyed.**
      Never a mutable DB row — that would break the tamper-evident ledger that *is* the product. **[4B, I11]**
- [ ] **OpenEnv reward-boundary invariant (non-waivable).** The OpenEnv env-server runs in **account A**
      (agent-reachable), so it **never computes the graded reward.** Its `step()` / terminal reward is at
      most a **non-graded, zero shaping signal**; the **graded training reward is delivered exclusively by
      the account-B write-isolated verifier** as a KMS-signed WORM record, joined to the episode by
      `trajectory_id` — and the trainer trains on **that**, never on the env's `step()` reward. OpenEnv's
      idiom is environment-owned reward; AssayOps does **not** follow it for the graded signal. **[1C, 4B, T1, I5]**
- [ ] **One contract schema → codegen both languages.** Never hand-maintain dual TS/Python types;
      generated artifacts are committed; the CI byte-parity (JCS) gate must stay green. **[5A, I3]**
- [ ] **Locked fixtures are off-limits.** Edit `contracts/vectors` only in `fixture-change` PRs from
      **#28**; edit `tools/red-team` only in `fixture-change` PRs from **#56**. All other PRs are barred.
- [ ] **The 15-vector red-team suite is the Phase-1 exit bar. R1: any open vector ⇒ STOP** — no
      public/proof claim on a gameable reward. **[§5, T10]**
- [ ] **T7 cost-bomb guardrails are P1-blocking.** No real-AWS episode until they exist; LocalStack
      only until then. **[T7, §3]**
- [ ] **Any lift claim must clear the §6 eval rigor** (OOD slice, ≥3 seeds, clustered SEs,
      contamination + verifier-determinism checks, pre-registered +8–10 pt threshold). **[T2, T11]**
- [ ] **Gold trajectories + held-out eval live in a private data store, never committed to any code
      repo** (contamination control + moat). **[I11]**
- [ ] **Benchmark is private-now, publish-gated (D1=C); never open-source the
      harness/verifier/corpus/site.** The only public artifact is `@assayops/contracts` (plus,
      optionally and later, a small public sample task split). **[I11, roadmap]**
- [ ] **Build only the IP; reuse the rest.** Build: verifier core, diff IR + adapters, reward ledger,
      contract schema, determinism + replay, episode lifecycle, the Python OpenEnv env-server, red-team
      suite, eval-harness wiring, task corpus, account infra + guardrails. **Reuse, don't rebuild:**
      OpenEnv, Fleet Harbor (rollouts only), LocalStack, Daytona/Modal, Control Tower AFT, KMS + S3
      Object Lock, terraform/cdk CLIs. **[eng-arch]**
- [ ] **The proof's training is SFT-only — do NOT build the RL/GRPO training loop before the proof**
      (it's a post-proof stretch, off the critical path). The reward ledger/verifier an RL loop would
      consume is **not** deferred — it's the core moat, built regardless. Deferred too:
      migration/incident/cost task families (after drift&debug) + the Pulumi adapter (cheap via 6A).
      **[eng-arch / proof-first]**
- [ ] **Don't re-litigate a decision in this file.** It's settled — **flag, don't silently deviate.**
      For the deeper *why* beyond this floor, query the `assay-brain` skill (#73).

---

## Sources

This file is distilled from the locked plans in the sibling **`brain`** repo
(`AssayInc/brain`). The substance lives here so this repo stands alone; cite these to trace or to
go deeper (via the `assay-brain` skill, #73). **On any conflict, the brain plans win — fix this file.**

| Tag in this doc | Plan (in `brain/raw/plans/`) | Supplies |
|---|---|---|
| eng-arch | `assay-eng-architecture-2026-06-17.md` | Trust model, locked decisions 1C–T3, tasks T1–T13, the threat table (14 vectors; promoted to the 15-vector §5 bar here), eval design |
| proof-first | `assay-proof-first-plan-2026-06-16.md` | The 5 phases (T0-relative), risks & kill-criteria R1–R6, pre-registered success criteria |
| roadmap | `assay-strategic-roadmap-2026-06-17.md` | D1=C benchmark posture; the 12-month flywheel (lab-agnostic · ELT second act · published verifier-isolation) |
| impl-plan | `assayops-implementation-plan-2026-06-17.md` | Implementation decisions I1–I11, T→Epic mapping, the 15th-vector promotion, this provenance convention |

**Related issues:** #56 (E10-1) owns the canonical 15-vector table + red-team fixtures · #17 (E0-1)
owns `docs/ARCHITECTURE.md` (the *how/where*) · #18 (E0-6) owns `CLAUDE.md` (which links here) ·
#73 (E0-7) owns the `assay-brain` deep-recall skill.
