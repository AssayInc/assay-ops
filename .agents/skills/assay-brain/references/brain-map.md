# Assay Brain — map, cheatsheet, and delegation

Deeper reference for the `assay-brain` skill. Read this when you need to know *where* something lives in
the brain, want finer control over qmd than the helper gives, or are handing off to `wiki-query`.

> The authoritative, current catalog is always `assay-brain map` (i.e. `<brain>/wiki/index.md`). The
> cluster list below is a stable orientation, not a substitute — pages are added/renamed as the research
> sharpens, so confirm against the live catalog before citing an exact filename.

## What lives where (wiki clusters)

- **`synthesis/`** — the cross-cutting argument. `assay-thesis` (RL-env demand × deterministic infra
  verification × judgment-beats-labor). Start here for "what's the core thesis".
- **`projects/assay/`** — the project hub and the locked plans: `assay` (wedge, the five task families,
  business model, name), `proof-first-plan` (the execution/GTM plan: benchmark-as-eval → private lift demo
  → Anthropic pitch), `eng-architecture` (the proof-critical subsystems — verifier, replay, reward ledger,
  eval — the two-account trust model, the 11 decisions), `strategic-roadmap` (the 12-month flywheel),
  `founding-team`. Start here for "what's our plan / position".
- **`concepts/` — RL environments & verification (Assay core):** `rl-environments`,
  `deterministic-verification`, `long-horizon-gap`, `cloud-iac-wedge`, `data-foundry`, `reward-hacking`,
  `sandbox-orchestration`, `write-isolated-verifier`, `iac-verification-primitives`, `retries-and-backoff`,
  `eval-to-performance-proof`.
- **`concepts/` — market, demand & adjacency:** `infra-agent-demand`, `benchmark-saturation`,
  `environment-economics`, `data-pipeline-adjacency`.
- **`concepts/` — AI agents & coding agents:** `agent-harness`, `agent-vs-automation`,
  `agentic-engineering`, `claude-code-architecture`, `code-act`, `computer-use-automation`,
  `context-engineering`, `file-based-memory`, `mcp-code-execution`, `loop-engineering`, `loopy-era`,
  `autoresearch-eval-loop`, `llm-wiki-pattern`, `efficiency-is-intelligence`.
- **`concepts/` — founder & product philosophy:** `strategic-filters`, `defensibility-moat`,
  `validate-before-building`, `product-market-fit`, `ai-native-startup-lifecycle`, `one-person-unicorn`,
  `ai-first-service-company`, `requests-for-startups`, `boil-the-ocean`,
  `frighteningly-ambitious-startup-ideas`, `how-to-do-great-work`, `relentlessly-resourceful`,
  `ai-consumer-renaissance`.
- **`entities/`** — labs, the RL-env/data-foundry landscape, harnesses/sandboxes, cloud tooling, people:
  `anthropic`, `wing-vc`, `epoch-ai`; `hud`, `prime-intellect`, `openenv`, `mercor`, `surge`, `fleet-ai`,
  `turing`, `scale-ai`, `halluminate`, `veris-ai`, `snorkel`, `bugcrowd`, `applied-compute`,
  `hugging-face`; `harbor`, `daytona`, `modal`, `claude-code`, `deepagents`, `manus`, `paperclip`,
  `openshell`, `mastra`, `hermes`, `claude-fable-5`; `localstack`, `bun`, `turborepo`, `dbt-labs`;
  `andrej-karpathy`, `paul-graham`, `brian-chesky`.
- **`references/`** — durable source-backed pages. Benchmarks & evidence: `nsync` (the
  terraform-plan-against-live-state paper, the canonical deterministic-verification citation),
  `swe-infrabench`, `swe-evo`, `swe-bench-pro`, `iac-eval`, `multi-iac-eval`, `terminal-bench`,
  `elt-bench`, `rlef`, `metr-time-horizon`, `long-horizon-benchmarks`, `spotify-honk`, `endless-terminals`,
  `reward-hacking-evidence`, `assay-market-deep-research-2026-06`, `ai-data-labeling-industry`,
  `founders-playbook`. **AWS / IaC verification primitives:** `aws-cdk`, `aws-cloudformation`,
  `aws-cloud-control-api`, `aws-organizations-org-formation`.
- **`skills/`** — durable how-to pages: `context-engineering-practices`.

## Raw sources (`<brain>/raw/`)

Go here only when a wiki page cites a source, or the wiki is too shallow. Navigate by directory — don't
hardcode individual filenames (this folder churns):

- `VISION.md` — the working strategy hypothesis (canonical here; ingested as a wiki source).
- `plans/` — the locked strategy/architecture plans the wiki distills (eng-architecture, proof-first,
  strategic-roadmap, the implementation plan). The source for "what did we actually decide".
- `deepresearch/` — full research memos the wiki distills into citable pages.
- `conversations/` — incl. the founding conversation (`assay-founding-conversation.md`).
- `papers/`, `articles/`, `transcriptions/`, `assets/` — supporting source material.
- `repos/` — cloned reference codebases (**gitignored**; not present in a fresh clone — regenerate with
  `<brain>/scripts/fetch-references.sh`). See the landscape `entities/` and benchmark `references/` pages
  for what's there without cloning.

The `assay-brain-papers` qmd collection indexes the raw sources: `qmd ask`/`search` via the helper only hit
`assay-brain-wiki`; to search raw material use qmd directly with `-c assay-brain-papers` (see cheatsheet).

## qmd cheatsheet (when the helper isn't enough)

The helper wraps the common cases. Reach for raw qmd when you need lex/vec control, negation, the papers
collection, or to fetch a doc by id. Collections: `assay-brain-wiki` (vault), `assay-brain-papers` (raw).

```bash
# Lexical — exact names, API calls, paths, error strings:
qmd search "Cloud Control GetResource drift detection" -c assay-brain-wiki -n 8 --files

# Hybrid lex+vec with separate lines (more control than `assay-brain ask`):
#   keep punctuation/operator tokens on lex; write vec as plain prose;
#   vec does NOT support `-term` negation — only lex does.
qmd query $'lex: write-isolated verifier WORM Object Lock\nvec: how is the reward made impossible for the agent to forge' -c assay-brain-wiki -n 8 --files

# Vector-only recall (concepts, fuzzy):
qmd vsearch "grading deployed infrastructure against ground truth without running the agent's plan" -c assay-brain-wiki -n 8 --files

# Search the raw source corpus instead of the compiled wiki:
qmd query $'lex: terraform plan\nvec: deterministic verification against live cloud state' -c assay-brain-papers -n 8 --files

# Fetch a ranked doc by id (ids come from --files output like #ab12cd):
qmd get "#ab12cd"
```

If `qmd` is missing or a collection isn't built, the helper falls back to grep over `<brain>/wiki`; raw
qmd commands will just error — fall back to `Grep` over `<brain>/wiki` (frontmatter
`^(title|tags|aliases|summary):` first, content second) yourself.

## Delegating to `wiki-query`

Use `assay-brain` for locating the brain and quick/medium retrieval. Escalate to the **`wiki-query`**
skill for deep work: multi-page synthesis, typed-relationship traversal (`extends`/`contradicts`/…),
gap analysis, and lifecycle-/staleness-aware citations with a query log.

`wiki-query` resolves its vault from config that is currently empty, so supply it first:

```bash
# Option A — for this invocation only (preferred on a machine with more than one brain):
eval "$(assay-brain env)"   # exports OBSIDIAN_VAULT_PATH=<brain>/wiki, QMD_WIKI_COLLECTION=assay-brain-wiki, …
# then invoke the wiki-query skill

# Option B — once per machine (durable; makes every generic wiki-* skill resolve the brain):
assay-brain setup           # writes ~/.obsidian-wiki/config
```

`assay-brain setup` writes `~/.obsidian-wiki/config` (mode 600, atomic write; idempotent — a no-op if
already correct, otherwise it timestamp-backs-up any existing real config to `config.bak.<ts>` and
refuses to write through a symlink) with `OBSIDIAN_VAULT_PATH`, `OBSIDIAN_SOURCES_DIR`,
`QMD_WIKI_COLLECTION`, `QMD_PAPERS_COLLECTION`, `QMD_TRANSPORT=cli`, `QMD_CLI_SEARCH_MODE=quality`. It
lives in `$HOME`, never the repo, because the absolute brain path is per-machine. That config is
**machine-global** — it points at one brain at a time, so on a machine that also has another brain (e.g.
a sibling `cleno` brain) prefer the per-invocation `eval "$(assay-brain env)"`. Re-run `setup` after
moving or re-cloning the brain.

## Locating / cloning the brain

The brain is expected as a **sibling checkout** (`../brain`) of whatever Assay repo you're in. The helper
also accepts `$ASSAY_BRAIN_PATH` and falls back to `~/Projects/Assay/brain`. If none resolve:

```bash
git clone https://github.com/AssayInc/brain ../brain   # tracked wiki/ + raw/ come with it
```

A fresh clone has the full `wiki/` and the tracked `raw/` sources, but **not** `raw/repos/` (gitignored).
The qmd collections are local indexes; if `assay-brain doctor` shows the collection isn't live on a new
machine, the markdown vault is still fully usable via `map`/`Read`/grep.
