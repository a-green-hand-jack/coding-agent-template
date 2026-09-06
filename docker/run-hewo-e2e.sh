#!/usr/bin/env bash
set -euo pipefail
name="${AGENT_NAME:-hewo}"
backend="${AGENT_BACKEND:-${HEWO_BACKEND:-opencode}}"
provider="${LLM_PROVIDER:-}"
model="${LLM_MODEL:-}"
api_key_env=""
api_key_stdin=false
env_file="${ENV_FILE:-.env}"
bundle=""
workspace="${E2E_WORKSPACE:-}"
auth_file="${OPENCODE_AUTH_FILE:-}"
codex_auth_file="${CODEX_AUTH_FILE:-}"
claude_credentials_file="${CLAUDE_CREDENTIALS_FILE:-}"
claude_api_key_file="${CLAUDE_API_KEY_FILE:-}"
codex_sandbox_mode="${CODEX_SANDBOX_MODE:-workspace-write}"
no_build=false

usage() {
  printf '%s\n' "Usage: $0 [options] <task>" "" \
    "Options:" \
    "  --backend NAME       Backend: opencode, codex, or claude" \
    "  --provider NAME       OpenCode provider name (backend-specific default)" \
    "  --model NAME          Model name (backend-specific default)" \
    "  --api-key-env NAME    Read the provider key from this host variable" \
    "  --api-key-stdin       Read the provider key from stdin (never shell history)" \
    "  --env-file PATH       Load additional variables from PATH" \
    "  --bundle PATH         Mount a read-only provider bundle" \
    "  --auth-file PATH      Mount one explicit OpenCode auth store read-only" \
    "  --codex-auth-file PATH Mount one explicit Codex auth store read-only" \
    "  --claude-credentials-file PATH Mount Claude credentials read-only" \
    "  --claude-api-key-file PATH Mount one Claude API key file read-only" \
    "  --codex-sandbox-mode MODE Codex sandbox: read-only, workspace-write, or danger-full-access" \
    "  --workspace PATH      Mount PATH as the clean container workspace" \
    "  --no-build            Reuse the existing image for this Agent" \
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
    --auth-file) auth_file="${2:?missing value for --auth-file}"; shift 2 ;;
    --codex-auth-file) codex_auth_file="${2:?missing value for --codex-auth-file}"; shift 2 ;;
    --claude-credentials-file) claude_credentials_file="${2:?missing value for --claude-credentials-file}"; shift 2 ;;
    --claude-api-key-file) claude_api_key_file="${2:?missing value for --claude-api-key-file}"; shift 2 ;;
    --codex-sandbox-mode) codex_sandbox_mode="${2:?missing value for --codex-sandbox-mode}"; shift 2 ;;
    --workspace) workspace="${2:?missing value for --workspace}"; shift 2 ;;
    --no-build) no_build=true; shift ;;
    --agent) name="${2:?missing value for --agent}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    *) break ;;
  esac
done

case "$backend" in
  open-code) backend="opencode" ;;
  claude-code) backend="claude" ;;
esac
case "$backend" in
  opencode) [[ -n "$provider" ]] || provider="openai" ;;
  codex) [[ -n "$provider" ]] || provider="openai" ;;
  claude) [[ -n "$provider" ]] || provider="anthropic" ;;
  *) echo "unsupported backend: $backend (expected opencode, codex, or claude)" >&2; exit 2 ;;
esac
provider_key_prefix="$(printf '%s' "$provider" | tr '[:lower:]-.' '[:upper:]__')"
if [[ -z "$model" ]]; then
  case "$backend" in
    opencode) model="gpt-5.6" ;;
    codex) model="gpt-5.5" ;;
    claude) model="sonnet" ;;
  esac
fi

task=()
while (($#)); do task+=("$1"); shift; done
if ((${#task[@]} == 0)); then usage >&2; exit 2; fi

if [[ "$no_build" != true ]]; then
  docker build --build-arg AGENT_NAME="$name" -t "$name:e2e" -f docker/Dockerfile . >&2
fi
env_args=()
env_args+=(--env "AGENT_BACKEND=$backend" --env "LLM_PROVIDER=$provider" --env "LLM_MODEL=$model" --env "CODEX_SANDBOX_MODE=$codex_sandbox_mode")
if [[ -n "${LLM_VARIANT:-}" ]]; then
  env_args+=(--env "LLM_VARIANT=$LLM_VARIANT")
fi
if [[ -n "${AGENT_OUTPUT_FORMAT:-}" ]]; then
  env_args+=(--env "AGENT_OUTPUT_FORMAT=$AGENT_OUTPUT_FORMAT")
fi
if [[ -n "$api_key_env" ]]; then
  [[ -n "${!api_key_env:-}" ]] || { printf '%s is not set\n' "$api_key_env" >&2; exit 2; }
  case "$backend" in
    codex) env_args+=(--env "OPENAI_API_KEY=${!api_key_env}") ;;
    claude) env_args+=(--env "ANTHROPIC_API_KEY=${!api_key_env}") ;;
    *) env_args+=(--env "${api_key_env}=${!api_key_env}") ;;
  esac
elif [[ "$api_key_stdin" == true ]]; then
  IFS= read -r api_key
  [[ -n "$api_key" ]] || { printf 'provider key from stdin is empty\n' >&2; exit 2; }
  case "$backend" in
    codex) env_args+=(--env "OPENAI_API_KEY=$api_key") ;;
    claude) env_args+=(--env "ANTHROPIC_API_KEY=$api_key") ;;
    *) env_args+=(--env "${provider_key_prefix}_API_KEY=$api_key") ;;
  esac
else
  key_variable="${provider_key_prefix}_API_KEY"
  [[ "$backend" == codex ]] && key_variable=OPENAI_API_KEY
  [[ "$backend" == claude ]] && key_variable=ANTHROPIC_API_KEY
  if [[ -n "${!key_variable:-}" ]]; then
    env_args+=(--env "$key_variable=${!key_variable}")
  fi
fi

passthrough_envs=()
case "$backend" in
  opencode|codex) passthrough_envs=(OPENAI_BASE_URL) ;;
  claude) passthrough_envs=(ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN) ;;
esac
for passthrough_env in "${passthrough_envs[@]}"; do
  if [[ -n "${!passthrough_env:-}" ]]; then
    env_args+=(--env "$passthrough_env=${!passthrough_env}")
  fi
done

case "$backend" in
  opencode)
    [[ -z "$codex_auth_file" && -z "$claude_credentials_file" && -z "$claude_api_key_file" ]] || {
      echo "credential option does not match selected OpenCode backend" >&2
      exit 2
    }
    ;;
  codex)
    [[ -z "$auth_file" && -z "$claude_credentials_file" && -z "$claude_api_key_file" ]] || {
      echo "credential option does not match selected Codex backend" >&2
      exit 2
    }
    ;;
  claude)
    [[ -z "$auth_file" && -z "$codex_auth_file" ]] || {
      echo "credential option does not match selected Claude backend" >&2
      exit 2
    }
    ;;
esac

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

codex_auth_args=()
if [[ -n "$codex_auth_file" ]]; then
  [[ -f "$codex_auth_file" ]] || { echo "Codex auth file does not exist: $codex_auth_file" >&2; exit 2; }
  codex_auth_args=(--env CODEX_AUTH_STORE=1 --env CODEX_HOME=/root/.codex --mount "type=bind,src=$(realpath "$codex_auth_file"),dst=/root/.codex/auth.json,readonly")
fi

claude_auth_args=()
if [[ -n "$claude_credentials_file" ]]; then
  [[ -f "$claude_credentials_file" ]] || { echo "Claude credentials file does not exist: $claude_credentials_file" >&2; exit 2; }
  claude_auth_args=(--env CLAUDE_AUTH_STORE=1 --env CLAUDE_CONFIG_DIR=/root/.claude --mount "type=bind,src=$(realpath "$claude_credentials_file"),dst=/root/.claude/.credentials.json,readonly")
fi
if [[ -n "$claude_api_key_file" ]]; then
  [[ -f "$claude_api_key_file" ]] || { echo "Claude API key file does not exist: $claude_api_key_file" >&2; exit 2; }
  claude_auth_args+=(--env ANTHROPIC_API_KEY_FILE=/run/secrets/anthropic_api_key --mount "type=bind,src=$(realpath "$claude_api_key_file"),dst=/run/secrets/anthropic_api_key,readonly")
fi

env_file_args=()
if [[ -f "$env_file" ]]; then
  env_file_args=(--env-file "$env_file")
fi

tty_args=()
if [[ -t 0 && -t 1 ]]; then
  tty_args=(-it)
fi
docker run --rm "${tty_args[@]}" "${env_file_args[@]}" "${env_args[@]}" "${bundle_args[@]}" "${workspace_args[@]}" "${auth_args[@]}" "${codex_auth_args[@]}" "${claude_auth_args[@]}" "$name:e2e" "${task[@]}"
