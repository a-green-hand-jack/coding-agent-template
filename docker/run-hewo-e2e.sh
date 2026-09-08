#!/usr/bin/env bash
set -euo pipefail
name="${AGENT_NAME:-hewo}"
backend="${AGENT_BACKEND:-${HEWO_BACKEND:-pi}}"
provider="${LLM_PROVIDER:-}"
model="${LLM_MODEL:-}"
api_key_env=""
api_key_stdin=false
env_file="${ENV_FILE:-.env}"
bundle=""
workspace="${E2E_WORKSPACE:-}"
pi_auth_file="${PI_AUTH_FILE:-}"
pi_models_file="${PI_MODELS_FILE:-}"
no_build=false
allow_unauthenticated=false
credential_sources=()

usage() {
  printf '%s\n' "Usage: $0 [options] <task>" "" \
    "Options:" \
    "  --backend NAME        Backend: pi only (alias: pi-coding-agent)" \
    "  --provider NAME       pi provider name (default: openai)" \
    "  --model NAME          pi model pattern (default: gpt-5.5)" \
    "  --api-key-env NAME    Read the provider key from this host variable" \
    "  --api-key-stdin       Read the provider key from stdin (never shell history)" \
    "  --env-file PATH       Load additional variables from PATH" \
    "  --bundle PATH         Mount a read-only provider bundle" \
    "  --pi-auth-file PATH   Mount one pi auth store read-only" \
    "  --pi-models-file PATH Mount one pi model catalog read-only" \
    "  --workspace PATH      Mount PATH as the clean container workspace" \
    "  --no-build            Reuse the existing image for this Agent" \
    "  --allow-unauthenticated Run without a provider credential (infrastructure-only)" \
    "  --agent NAME          Build and run a different src/<agent>" \
    "  -h, --help            Show this help"
}

while (($#)); do
  case "$1" in
    --backend) backend="${2:?missing value for --backend}"; shift 2 ;;
    --provider) provider="${2:?missing value for --provider}"; shift 2 ;;
    --model) model="${2:?missing value for --model}"; shift 2 ;;
    --api-key-env) api_key_env="${2:?missing value for --api-key-env}"; shift 2 ;;
    --api-key-stdin) api_key_stdin=true; shift ;;
    --env-file) env_file="${2:?missing value for --env-file}"; shift 2 ;;
    --bundle) bundle="${2:?missing value for --bundle}"; shift 2 ;;
    --pi-auth-file) pi_auth_file="${2:?missing value for --pi-auth-file}"; shift 2 ;;
    --pi-models-file) pi_models_file="${2:?missing value for --pi-models-file}"; shift 2 ;;
    --workspace) workspace="${2:?missing value for --workspace}"; shift 2 ;;
    --no-build) no_build=true; shift ;;
    --allow-unauthenticated) allow_unauthenticated=true; shift ;;
    --agent) name="${2:?missing value for --agent}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    *) break ;;
  esac
done

# pi is the only supported backend. An explicit request for anything else is a
# hard error, never a silent coercion to pi.
case "$backend" in
  pi|pi-coding-agent) backend="pi" ;;
  *)
    printf 'unsupported backend: %s (this Agent supports pi only)\n' "$backend" >&2
    exit 2
    ;;
esac
[[ -n "$provider" ]] || provider="openai"
provider_key_prefix="$(printf '%s' "$provider" | tr '[:lower:]-.' '[:upper:]__')"
[[ -n "$model" ]] || model="gpt-5.5"

task=()
while (($#)); do task+=("$1"); shift; done
if ((${#task[@]} == 0)); then usage >&2; exit 2; fi

if [[ "$no_build" != true ]]; then
  docker build --build-arg AGENT_NAME="$name" -t "$name:e2e" -f docker/Dockerfile . >&2
fi
env_args=()
env_args+=(--env "AGENT_BACKEND=$backend" --env "LLM_PROVIDER=$provider" --env "LLM_MODEL=$model")
if [[ -n "${LLM_VARIANT:-}" ]]; then
  env_args+=(--env "LLM_VARIANT=$LLM_VARIANT")
fi
if [[ -n "${AGENT_OUTPUT_FORMAT:-}" ]]; then
  env_args+=(--env "AGENT_OUTPUT_FORMAT=$AGENT_OUTPUT_FORMAT")
fi
if [[ -n "$api_key_env" ]]; then
  [[ -n "${!api_key_env:-}" ]] || { printf '%s is not set\n' "$api_key_env" >&2; exit 2; }
  env_args+=(--env "${provider_key_prefix}_API_KEY=${!api_key_env}")
  credential_sources+=("--api-key-env $api_key_env")
elif [[ "$api_key_stdin" == true ]]; then
  IFS= read -r api_key
  [[ -n "$api_key" ]] || { printf 'provider key from stdin is empty\n' >&2; exit 2; }
  env_args+=(--env "${provider_key_prefix}_API_KEY=$api_key")
  credential_sources+=("--api-key-stdin")
else
  key_variable="${provider_key_prefix}_API_KEY"
  if [[ -n "${!key_variable:-}" ]]; then
    env_args+=(--env "$key_variable=${!key_variable}")
    credential_sources+=("env:$key_variable")
  fi
fi

# Fail closed: a task run needs an injected provider credential. Without one,
# the run is infrastructure-only at best and must not be reported as E2E.
if [[ "$allow_unauthenticated" != true ]]; then
  guard_key_variable="${provider_key_prefix}_API_KEY"
  has_credential=false
  [[ "${#credential_sources[@]}" -gt 0 ]] && has_credential=true
  [[ -n "$bundle" ]] && has_credential=true
  [[ -n "$pi_auth_file" ]] && has_credential=true
  [[ -n "${!guard_key_variable:-}" ]] && has_credential=true
  if [[ -f "$env_file" ]] && grep -qE '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*(_API_KEY|_AUTH_TOKEN)=' "$env_file"; then
    has_credential=true
    credential_sources+=("--env-file $env_file")
  fi
  if [[ "$has_credential" != true ]]; then
    printf '%s\n' \
      'error: no provider credential injected; a task run cannot be E2E evidence.' \
      'Inject one of:' \
      '  --api-key-env NAME | --api-key-stdin | --bundle PATH' \
      '  --pi-auth-file PATH' \
      "or export $guard_key_variable." \
      'Pass --allow-unauthenticated only for infrastructure-only smokes' \
      '(build/--help).' >&2
    exit 2
  fi
fi

# pi provider endpoint overrides (not credentials): pass through when set.
passthrough_envs=(OPENAI_BASE_URL ANTHROPIC_BASE_URL)
for passthrough_env in "${passthrough_envs[@]}"; do
  if [[ -n "${!passthrough_env:-}" ]]; then
    env_args+=(--env "$passthrough_env=${!passthrough_env}")
  fi
done

bundle_args=()
if [[ -n "$bundle" ]]; then
  [[ -f "$bundle/manifest.json" && -f "$bundle/credential" ]] || { echo "invalid provider bundle" >&2; exit 2; }
  bundle_key_env="$(sed -n 's/.*"credential_env":"\([A-Za-z_][A-Za-z0-9_]*\)".*/\1/p' "$bundle/manifest.json")"
  [[ -n "$bundle_key_env" ]] || { echo "invalid provider bundle manifest" >&2; exit 2; }
  env_args+=(--env "$bundle_key_env=$(<"$bundle/credential")")
  bundle_args=(--mount "type=bind,src=$(realpath "$bundle"),dst=/run/provider-bundle,readonly")
  credential_sources+=("--bundle $bundle")
fi

workspace_args=()
if [[ -n "$workspace" ]]; then
  [[ -d "$workspace" ]] || { echo "workspace directory does not exist: $workspace" >&2; exit 2; }
  workspace_args=(--mount "type=bind,src=$(realpath "$workspace"),dst=/workspace")
fi

pi_auth_args=()
if [[ -n "$pi_auth_file" ]]; then
  [[ -f "$pi_auth_file" ]] || { echo "pi auth file does not exist: $pi_auth_file" >&2; exit 2; }
  pi_auth_args=(--env PI_AUTH_STORE=1 --env PI_CODING_AGENT_DIR=/root/.pi/agent --mount "type=bind,src=$(realpath "$pi_auth_file"),dst=/root/.pi/agent/auth.json,readonly")
  credential_sources+=("--pi-auth-file $pi_auth_file")
  if [[ -z "$pi_models_file" ]]; then
    candidate_models_file="$(dirname "$pi_auth_file")/models.json"
    [[ -f "$candidate_models_file" ]] && pi_models_file="$candidate_models_file"
  fi
  if [[ -n "$pi_models_file" ]]; then
    [[ -f "$pi_models_file" ]] || { echo "pi models file does not exist: $pi_models_file" >&2; exit 2; }
    pi_auth_args+=(--mount "type=bind,src=$(realpath "$pi_models_file"),dst=/root/.pi/agent/models.json,readonly")
  fi
fi

env_file_args=()
if [[ -f "$env_file" ]]; then
  env_file_args=(--env-file "$env_file")
fi

# Evidence line on stderr: stdout stays the agent transcript. Only credential
# metadata (flag plus path or variable name) is printed, never a key value.
credential_source="none"
if ((${#credential_sources[@]} > 0)); then
  credential_source="$(printf '%s,' "${credential_sources[@]}")"
  credential_source="${credential_source%,}"
fi
run_mode="agent-behavior"
[[ "$credential_source" == none ]] && run_mode="infrastructure-only"
printf 'evidence: backend=%s provider=%s model=%s credential_source=%s mode=%s\n' \
  "$backend" "$provider" "$model" "$credential_source" "$run_mode" >&2

tty_args=()
if [[ -t 0 && -t 1 ]]; then
  tty_args=(-it)
fi
docker run --rm "${tty_args[@]}" "${env_file_args[@]}" "${env_args[@]}" "${bundle_args[@]}" "${workspace_args[@]}" "${pi_auth_args[@]}" "$name:e2e" "${task[@]}"
