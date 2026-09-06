#!/usr/bin/env bash
set -euo pipefail
name="${AGENT_NAME:-example-agent}"
docker build --build-arg AGENT_NAME="$name" -t "$name:e2e" -f docker/Dockerfile .
env_args=()
for variable in LLM_PROVIDER LLM_MODEL OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL ANTHROPIC_API_KEY ANTHROPIC_BASE_URL ANTHROPIC_MODEL; do
  if [[ -n "${!variable:-}" ]]; then
    env_args+=(--env "$variable=${!variable}")
  fi
done

env_file_args=()
if [[ -f "${ENV_FILE:-.env}" ]]; then
  env_file_args=(--env-file "${ENV_FILE:-.env}")
fi

docker run --rm -it "${env_file_args[@]}" "${env_args[@]}" "$name:e2e" "$@"
