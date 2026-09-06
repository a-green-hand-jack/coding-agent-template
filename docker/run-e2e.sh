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

usage() {
  printf '%s\n' "Usage: $0 [options] <task>" "" \
    "Options:" \
    "  --provider NAME       OpenCode provider name (default: openai)" \
    "  --model NAME          Model name (default: gpt-5.6)" \
    "  --api-key-env NAME    Read the provider key from this host variable" \
    "  --api-key-stdin       Read the provider key from stdin (never shell history)" \
    "  --env-file PATH       Load additional variables from PATH" \
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

docker build --build-arg AGENT_NAME="$name" -t "$name:e2e" -f docker/Dockerfile .
env_args=()
env_args+=(--env "LLM_PROVIDER=$provider" --env "LLM_MODEL=$model")
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

env_file_args=()
if [[ -f "$env_file" ]]; then
  env_file_args=(--env-file "$env_file")
fi

tty_args=()
if [[ -t 0 && -t 1 ]]; then
  tty_args=(-it)
fi
docker run --rm "${tty_args[@]}" "${env_file_args[@]}" "${env_args[@]}" "${bundle_args[@]}" "$name:e2e" "${task[@]}"
