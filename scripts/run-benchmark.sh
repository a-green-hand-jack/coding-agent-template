#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:-hewo}"
task_file="${2:-benchmarks/tasks/example-task.md}"
backend="${AGENT_BACKEND:-${HEWO_BACKEND:-pi}}"
provider="${LLM_PROVIDER:-}"
model="${LLM_MODEL:-}"
run_dir="${BENCHMARK_RUN_DIR:-$root/artifacts/benchmark-$(date +%Y%m%d-%H%M%S)}"
workspace="${BENCHMARK_WORKSPACE:-${E2E_WORKSPACE:-$run_dir/workspace}}"
# pi is the only supported backend; any other request is a hard error.
case "$backend" in
  pi|pi-coding-agent) backend="pi" ;;
  *) echo "unsupported backend: $backend (this Agent supports pi only)" >&2; exit 2 ;;
esac
[[ -n "$provider" ]] || provider="openai"
[[ -n "$model" ]] || model="gpt-5.5"
mkdir -p "$run_dir" "$workspace" "$workspace/artifacts"

task_prompt="$(sed '/^#/d; /^$/d' "$task_file" | tr '\n' ' ')"
trajectory="$run_dir/trajectory.jsonl"
scrubbed="$run_dir/trajectory.scrubbed.jsonl"
stderr_log="$run_dir/stderr.log"

export AGENT_OUTPUT_FORMAT=json
export AGENT_BACKEND="$backend" LLM_PROVIDER="$provider" LLM_MODEL="$model"
auth_args=()
credential_source="none"
if [[ -n "${PI_AUTH_FILE:-}" ]]; then
  auth_args+=(--pi-auth-file "$PI_AUTH_FILE")
  credential_source="--pi-auth-file $PI_AUTH_FILE"
fi
if [[ -n "${PI_MODELS_FILE:-}" ]]; then
  auth_args+=(--pi-models-file "$PI_MODELS_FILE")
fi
if [[ -n "${BENCHMARK_API_KEY_ENV:-}" ]]; then
  [[ "${BENCHMARK_API_KEY_ENV}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "invalid benchmark API key environment" >&2; exit 2; }
  [[ -n "${!BENCHMARK_API_KEY_ENV:-}" ]] || { echo "${BENCHMARK_API_KEY_ENV} is not set" >&2; exit 2; }
  auth_args+=(--api-key-env "$BENCHMARK_API_KEY_ENV")
  credential_source="--api-key-env $BENCHMARK_API_KEY_ENV"
fi
./docker/run-hewo-e2e.sh --agent "$name" --backend "$backend" --provider "$provider" --model "$model" --workspace "$workspace" "${auth_args[@]}" "$task_prompt" \
  >"$trajectory" 2>"$stderr_log"

ARTIFACT_PATH="$workspace/artifacts/hewo-smoke.md" \
  ./benchmarks/verifiers/example-verifier.sh
./scripts/collect-trace.sh "$trajectory" "$scrubbed" >/dev/null

version="$(./scripts/build-release.sh "$name" 0.1.0 >/dev/null 2>&1 && sed -n 's/.*"version":"\([^"]*\)".*/\1/p' "release/$name-0.1.0/release-manifest.json")"
runtime_binary=pi
runtime_version="$(docker run --rm --entrypoint "$runtime_binary" "$name:e2e" --version 2>/dev/null | tail -n 1)"
definition_revision="$(git rev-parse HEAD)+worktree-$(git diff --binary -- src/"$name" | sha256sum | cut -d' ' -f1)"
model_name="$model"
model_ref="$model_name"
printf '{"benchmark":"hewo-infrastructure-smoke","agent":"%s","backend":"%s","provider":"%s","version":"%s","model":"%s","credential_source":"%s","runtime":"%s","definition_revision":"%s","task":"%s","artifact":"%s","trajectory":"%s","scrubbed_trajectory":"%s"}\n' \
  "$name" "$backend" "$provider" "${version:-unknown}" "$model_ref" "$credential_source" "${runtime_version:-unknown}" "$definition_revision" "$task_file" "$workspace/artifacts/hewo-smoke.md" "$trajectory" "$scrubbed"
echo "evidence directory: $run_dir"
