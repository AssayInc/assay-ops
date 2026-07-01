# AssayOps task runner: the contract-schema codegen lane (`just codegen`) + the LocalStack dev loop
# for the verifier's Cloud Control read path.

compose := "docker compose -f py/packages/infra-local/docker-compose.yml"

# List available recipes
default:
    @just --list

# Regenerate the committed contract types from contracts/schemas/ — TS interfaces (quicktype) + Python
# Pydantic v2 models (datamodel-code-generator). Both generators are pinned (bun.lock / uv.lock) and run
# with fixed flags, so re-running produces no diff — the precondition for the #29 regenerate-and-diff gate.
codegen:
    #!/usr/bin/env bash
    set -euo pipefail
    # TypeScript: plain interfaces, no runtime converters. quicktype reads the WHOLE schema dir — the same
    # set datamodel-codegen consumes below — so a newly added schema reaches BOTH generators. (A hardcoded
    # file list let a new schema's TS type silently go ungenerated, which the #29 parity gate then couldn't
    # see as drift.) LC_ALL=C fixes the glob's sort order, hence quicktype's output order, across machines;
    # it sorts the current schemas identically to the prior explicit alphabetical list, so output stays
    # byte-identical. quicktype has no `unknown` option, so the deliberately-open diff-IR / trajectory fields
    # emit `any` — the generated file is carved out of Biome lint (tsc still typechecks).
    ( export LC_ALL=C
      bunx quicktype --src-lang schema --lang typescript --just-types \
        --out ts/packages/contracts/src/generated.ts \
        contracts/schemas/*.schema.json )
    # quicktype widens the binary `reward` (schema enum [0,1]) to `number` — it cannot emit a numeric
    # literal union (verified). Pin the DECISIONS.md §8 invariant into the public TS type, but ONLY the
    # RewardRecord.reward field: a blanket file-wide rewrite would silently narrow any future unrelated
    # `reward: number;` field. Isolate the RewardRecord interface block and fail CLOSED on any quicktype-format
    # drift — block not a single isolated interface, or not exactly one `reward: number;` in it — before
    # rewriting, so the binary invariant can never be silently dropped or applied to the wrong field. The Python
    # `Reward` enum already encodes the same.
    gen=ts/packages/contracts/src/generated.ts
    block=$(perl -ne 'print if /^export interface RewardRecord \{/ .. /^\}/' "$gen")
    # The block must be EXACTLY the RewardRecord interface: exactly one `export interface` header (so a
    # quicktype-drifted indented `}` can't bleed the flip-flop range forward into a later interface) and a
    # top-level `}` as its last line (so it isn't an unterminated run to EOF). Fail closed otherwise.
    headers=$(printf '%s\n' "$block" | grep -c '^export interface ' || true)
    if [ "${headers:-0}" -ne 1 ] || [ "$(printf '%s\n' "$block" | tail -1)" != "}" ]; then
      echo 'codegen: could not isolate the RewardRecord interface block (quicktype output changed?)' >&2
      exit 1
    fi
    reward_fields=$(printf '%s\n' "$block" | grep -c '^[[:space:]]*reward: number;' || true)
    if [ "${reward_fields:-0}" -ne 1 ]; then
      echo "codegen: expected exactly one 'reward: number;' in the RewardRecord interface, found ${reward_fields:-0} (quicktype output changed?)" >&2
      exit 1
    fi
    perl -i -pe 's/\breward: number;/reward: 0 | 1;/ if /^export interface RewardRecord \{/ .. /^\}/' "$gen"
    # Backstop: the pin landed INSIDE the RewardRecord block (not a stray `reward: 0 | 1;` elsewhere in the file).
    perl -ne 'print if /^export interface RewardRecord \{/ .. /^\}/' "$gen" | grep -q '^[[:space:]]*reward: 0 | 1;' || { echo 'codegen: reward 0|1 pin did not apply to RewardRecord (quicktype output changed?)' >&2; exit 1; }
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
    : "${LOCALSTACK_AUTH_TOKEN:?Set LOCALSTACK_AUTH_TOKEN in your environment or .env (see py/packages/infra-local/README.md) - licensed LocalStack for AWS requires it}"
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

# Run the boto3 Cloud Control read-path + adapter↔golden grade round-trip smokes (Python — the
# verifier's read SDK) against a running LocalStack
smoke:
    cd py/packages/infra-local && bun run smoke
