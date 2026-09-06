#!/usr/bin/env bash
set -euo pipefail
name="${AGENT_NAME:-example-agent}"
provider="${LLM_PROVIDER:-openai}"
model="${LLM_MODEL:-gpt-5.6}"
provider_key_prefix="$(printf '%s' "$provider" | tr '[:lower:]-.' '[:upper:]__')"
api_key_env=""
api_key_stdin=false
env_file="${ENV_FILE:-.env}"
bundle=""
workspace="${E2E_WORKSPACE:-}"
auth_file="${OPENCODE_AUTH_FILE:-}"
no_build=false

usage() {
  printf '%s\n' "Usage: $0 [options] <task>" "" \
    "Options:" \
    "  --provider NAME       OpenCode provider name (default: openai)" \
    "  --model NAME          Model name (default: gpt-5.6)" \
    "  --api-key-env NAME    Read the provider key from this host variable" \
    "  --api-key-stdin       Read the provider key from stdin (never shell history)" \
    "  --env-file PATH       Load additional variables from PATH" \
    "  --bundle PATH         Mount a read-only provider bundle" \
    "  --auth-file PATH      Mount one explicit OpenCode auth store read-only" \
    "  --workspace PATH      Mount PATH as the clean container workspace" \
    "  --no-build            Reuse the existing image for this Agent" \
    "  --agent NAME          Build and run a different src/<agent>" \
    "  -h, --help            Show this help"
}

while (($#)); do
  case "$1" in
    --provider) provider="${2:?missing value for --provider}"; shift 2 ;;
    --model) model="${2:?missing value for --model}"; shift 2 ;;
    --api-key-env) api_key_env="${2:?missing value for --api-key-env}"; shift 2 ;;
    --api-key-stdin) api_key_stdin=true; shift ;;
    --env-file) env_file="${2:?missing value for --env-file}"; shift 2 ;;
    --bundle) bundle="${2:?missing value for --bundle}"; shift 2 ;;
    --auth-file) auth_file="${2:?missing value for --auth-file}"; shift 2 ;;
    --workspace) workspace="${2:?missing value for --workspace}"; shift 2 ;;
    --no-build) no_build=true; shift ;;
    --agent) name="${2:?missing value for --agent}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    *) break ;;
  esac
done

task=()
while (($#)); do task+=("$1"); shift; done
if ((${#task[@]} == 0)); then usage >&2; exit 2; fi

if [[ "$no_build" != true ]]; then
  docker build --build-arg AGENT_NAME="$name" -t "$name:e2e" -f docker/Dockerfile . >&2
fi
env_args=()
env_args+=(--env "LLM_PROVIDER=$provider" --env "LLM_MODEL=$model")
if [[ -n "${LLM_VARIANT:-}" ]]; then
  env_args+=(--env "LLM_VARIANT=$LLM_VARIANT")
fi
if [[ -n "${AGENT_OUTPUT_FORMAT:-}" ]]; then
  env_args+=(--env "AGENT_OUTPUT_FORMAT=$AGENT_OUTPUT_FORMAT")
fi
if [[ -n "$api_key_env" ]]; then
  [[ -n "${!api_key_env:-}" ]] || { printf '%s is not set\n' "$api_key_env" >&2; exit 2; }
  env_args+=(--env "${api_key_env}=${!api_key_env}")
elif [[ "$api_key_stdin" == true ]]; then
  IFS= read -r api_key
  [[ -n "$api_key" ]] || { printf 'provider key from stdin is empty\n' >&2; exit 2; }
  env_args+=(--env "${provider_key_prefix}_API_KEY=$api_key")
else
  key_variable="${provider_key_prefix}_API_KEY"
  if [[ -n "${!key_variable:-}" ]]; then
    env_args+=(--env "$key_variable=${!key_variable}")
  fi
fi

bundle_args=()
if [[ -n "$bundle" ]]; then
  [[ -f "$bundle/manifest.json" && -f "$bundle/credential" ]] || { echo "invalid provider bundle" >&2; exit 2; }
  bundle_key_env="$(sed -n 's/.*"credential_env":"\([A-Za-z_][A-Za-z0-9_]*\)".*/\1/p' "$bundle/manifest.json")"
  [[ -n "$bundle_key_env" ]] || { echo "invalid provider bundle manifest" >&2; exit 2; }
  env_args+=(--env "$bundle_key_env=$(<"$bundle/credential")")
  bundle_args=(--mount "type=bind,src=$(realpath "$bundle"),dst=/run/provider-bundle,readonly")
fi

workspace_args=()
if [[ -n "$workspace" ]]; then
  [[ -d "$workspace" ]] || { echo "workspace directory does not exist: $workspace" >&2; exit 2; }
  workspace_args=(--mount "type=bind,src=$(realpath "$workspace"),dst=/workspace")
fi

auth_args=()
if [[ -n "$auth_file" ]]; then
  [[ -f "$auth_file" ]] || { echo "auth file does not exist: $auth_file" >&2; exit 2; }
  auth_args=(--env AGENT_AUTH_STORE=1 --mount "type=bind,src=$(realpath "$auth_file"),dst=/root/.local/share/opencode/auth.json,readonly")
fi

env_file_args=()
if [[ -f "$env_file" ]]; then
  env_file_args=(--env-file "$env_file")
fi

tty_args=()
if [[ -t 0 && -t 1 ]]; then
  tty_args=(-it)
fi
docker run --rm "${tty_args[@]}" "${env_file_args[@]}" "${env_args[@]}" "${bundle_args[@]}" "${workspace_args[@]}" "${auth_args[@]}" "$name:e2e" "${task[@]}"
