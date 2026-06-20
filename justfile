# AssayOps task runner. LocalStack dev loop for the verifier's Cloud Control read path.
# The contract-schema lane adds `just codegen` later.

compose := "docker compose -f infra-local/docker-compose.yml"

# List available recipes
default:
    @just --list

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
