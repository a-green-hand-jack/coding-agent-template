#!/usr/bin/env bash
set -euo pipefail
name="${AGENT_NAME:-example-agent}"
docker build --build-arg AGENT_NAME="$name" -t "$name:e2e" -f docker/Dockerfile .
docker run --rm -it --env-file "${ENV_FILE:-.env}" "$name:e2e" "$@"
