# Contributing

AssayOps is write-isolated verification infrastructure: **correctness and the trust boundary outrank
speed and cleverness.** Before your first change, read [`DECISIONS.md`](./DECISIONS.md) (the frozen
floor — trust model, locked decisions, threat bar) and the quality bar in [`CLAUDE.md`](./CLAUDE.md) /
[`AGENTS.md`](./AGENTS.md) (one constitution; `AGENTS.md` is a symlink to it).

## Setup

One-time setup — prerequisites, install, and the gate — is the README
**[Get started](./README.md#get-started)**. The single local gate is:

```sh
bun run verify   # turbo run typecheck lint test, across the TS and Python lanes
```

## Workflow

1. **Branch off `main`** — never push to `main` directly.
2. **Make the smallest change** that meets the issue's acceptance criteria; every changed line should
   trace to the issue (no drive-by refactors, no speculative abstraction).
3. **`bun run verify` green** locally — the same gate runs on every PR.
4. **Open a focused PR** with **`Closes #<issue>`** in the description, so the issue closes on merge.
5. **`/review`** and address findings before asking for a merge.
6. **Merge** only on green CI + an approving review **and** the maintainer's explicit go-ahead.

## Trust boundary (non-negotiable)

The grader is the product. The [`DECISIONS.md` §8 checklist](./DECISIONS.md#8-agent-non-negotiables-checklist)
is binding — above all, **the agent that writes code never edits what scores it**: change
`contracts/vectors` / `tools/red-team` only in their owning `fixture-change` PRs. If a task seems to
require breaking a non-negotiable, **stop and flag it on the issue** — don't code around it.

## Secrets

Secret-scanning **push protection** is enabled — GitHub blocks a push that contains a detected
credential. Keep secrets out of the repo: put local values in a gitignored `.env` (see the README). If
a push is blocked, remove the secret from your commits rather than bypassing the block.
