# AssayOps task runner: the contract-schema codegen lane (`just codegen`) + the LocalStack dev loop
# for the verifier's Cloud Control read path.

compose := "docker compose -f infra-local/docker-compose.yml"

# List available recipes
default:
    @just --list

# Regenerate the committed contract types from contracts/schemas/ — TS interfaces (quicktype) + Python
# Pydantic v2 models (datamodel-code-generator). Both generators are pinned (bun.lock / uv.lock) and run
# with fixed flags, so re-running produces no diff — the precondition for the #29 regenerate-and-diff gate.
codegen:
    #!/usr/bin/env bash
    set -euo pipefail
    # TypeScript: plain interfaces, no runtime converters. Schemas passed in a fixed order for
    # deterministic output. quicktype has no `unknown` option, so the deliberately-open diff-IR /
    # trajectory fields emit `any` — the generated file is carved out of Biome lint (tsc still typechecks).
    bunx quicktype --src-lang schema --lang typescript --just-types \
      --out ts/packages/contracts/src/generated.ts \
      contracts/schemas/diff-ir.schema.json \
      contracts/schemas/reward-record.schema.json \
      contracts/schemas/task-spec.schema.json \
      contracts/schemas/trajectory.schema.json
    # quicktype widens the binary `reward` (schema enum [0,1]) to `number` — it cannot emit a numeric
    # literal union (verified). Pin the DECISIONS.md §8 invariant into the public TS type with one
    # targeted, anchored rewrite (a single unique field, not a blanket pass), and assert it landed so a
    # quicktype-format change can't silently drop it. The Python `Reward` enum already encodes the same.
    perl -i -pe 's/\breward: number;/reward: 0 | 1;/' ts/packages/contracts/src/generated.ts
    grep -q 'reward: 0 | 1;' ts/packages/contracts/src/generated.ts || { echo 'codegen: reward 0|1 rewrite did not apply (quicktype output changed?)' >&2; exit 1; }
    # Python: --use-annotated emits Annotated[str, Field(...)] (mypy --strict-valid; the default
    # constr()/conint() are not valid type expressions); --disable-timestamp drops the header stamp so
    # output is reproducible. Directory input -> a modular `models/` package. The long schema-description
    # strings trip ruff E501 (no formatter wraps them), so the generated package is carved out of ruff lint.
    # datamodel-codegen does not prune its --output dir, so wipe it first — a removed/renamed schema must
    # not leave an orphan module (the hand-written assayops_contracts/__init__.py one level up is untouched).
    rm -rf py/packages/contracts/src/assayops_contracts/models
    uv run --frozen datamodel-codegen \
      --input contracts/schemas --input-file-type jsonschema \
      --output-model-type pydantic_v2.BaseModel \
      --use-annotated --disable-timestamp \
      --formatters ruff-check ruff-format \
      --target-python-version 3.12 \
      --output py/packages/contracts/src/assayops_contracts/models

# Regenerate the locked JCS golden-vector corpus (contracts/vectors/jcs-golden.json) from the authored
# record set. Deterministic (rfc8785 + sha256, both pinned) -> re-running produces no diff (the #29
# parity-gate precondition). Edit the record set ONLY in a `fixture-change` PR (DECISIONS.md Section 8):
# the agent that writes code never edits the grader. PYTHONPATH mirrors how pytest resolves the package src.
vectors:
    PYTHONPATH=py/packages/contracts/src uv run --frozen python py/packages/contracts/scripts/gen_vectors.py
    @echo "wrote contracts/vectors/jcs-golden.json"

# Bring licensed LocalStack up and wait for the gateway to report healthy.
# Requires LOCALSTACK_AUTH_TOKEN, taken from the environment or a gitignored .env (never committed).
up:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${LOCALSTACK_AUTH_TOKEN:-}" ] && [ -f .env ]; then
      # Tolerate an optional `export ` prefix and surrounding single/double quotes.
      val="$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?LOCALSTACK_AUTH_TOKEN=//p' .env | head -1)"
      val="${val%\"}"; val="${val#\"}"
      val="${val%\'}"; val="${val#\'}"
      export LOCALSTACK_AUTH_TOKEN="$val"
    fi
    : "${LOCALSTACK_AUTH_TOKEN:?Set LOCALSTACK_AUTH_TOKEN in your environment or .env (see infra-local/README.md) - licensed LocalStack for AWS requires it}"
    {{compose}} up -d
    echo "Waiting for the LocalStack gateway at http://localhost:4566 ..."
    for _ in $(seq 1 60); do
      if curl -sf http://localhost:4566/_localstack/health >/dev/null 2>&1; then
        echo "LocalStack ready"
        exit 0
      fi
      sleep 2
    done
    echo "LocalStack did not become healthy within 120s" >&2
    exit 1

# Tear down LocalStack and remove its volumes
down:
    {{compose}} down --volumes

# Follow LocalStack logs
logs:
    {{compose}} logs -f

# Run the Cloud Control smoke test against a running LocalStack
smoke:
    cd infra-local && bun run smoke
