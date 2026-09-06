#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:-hewo}"
task_file="${2:-benchmarks/tasks/example-task.md}"
backend="${AGENT_BACKEND:-${HEWO_BACKEND:-opencode}}"
run_dir="${BENCHMARK_RUN_DIR:-$root/artifacts/benchmark-$(date +%Y%m%d-%H%M%S)}"
workspace="$run_dir/workspace"
mkdir -p "$workspace" "$workspace/artifacts"

task_prompt="$(sed '/^#/d; /^$/d' "$task_file" | tr '\n' ' ')"
trajectory="$run_dir/trajectory.jsonl"
scrubbed="$run_dir/trajectory.scrubbed.jsonl"
stderr_log="$run_dir/stderr.log"

export AGENT_OUTPUT_FORMAT=json
auth_args=()
[[ -n "${OPENCODE_AUTH_FILE:-}" ]] && auth_args+=(--auth-file "$OPENCODE_AUTH_FILE")
[[ -n "${CODEX_AUTH_FILE:-}" ]] && auth_args+=(--codex-auth-file "$CODEX_AUTH_FILE")
[[ -n "${CLAUDE_CREDENTIALS_FILE:-}" ]] && auth_args+=(--claude-credentials-file "$CLAUDE_CREDENTIALS_FILE")
[[ -n "${CLAUDE_API_KEY_FILE:-}" ]] && auth_args+=(--claude-api-key-file "$CLAUDE_API_KEY_FILE")
./docker/run-e2e.sh --agent "$name" --backend "$backend" --workspace "$workspace" "${auth_args[@]}" "$task_prompt" \
  >"$trajectory" 2>"$stderr_log"

ARTIFACT_PATH="$workspace/artifacts/hewo-smoke.md" \
  ./benchmarks/verifiers/example-verifier.sh
./scripts/collect-trace.sh "$trajectory" "$scrubbed" >/dev/null

version="$(./scripts/build-release.sh "$name" 0.1.0 >/dev/null 2>&1 && sed -n 's/.*"version":"\([^"]*\)".*/\1/p' "release/$name-0.1.0/release-manifest.json")"
case "$backend" in
  opencode) runtime_binary=opencode ;;
  codex) runtime_binary=codex ;;
  claude) runtime_binary=claude ;;
  *) echo "unsupported backend: $backend" >&2; exit 2 ;;
esac
runtime_version="$(docker run --rm --entrypoint "$runtime_binary" "$name:e2e" --version 2>/dev/null | tail -n 1)"
definition_revision="$(git rev-parse HEAD)+worktree-$(git diff --binary -- src/"$name" | sha256sum | cut -d' ' -f1)"
model_name="${LLM_MODEL:-}"
if [[ -z "$model_name" ]]; then
  case "$backend" in
    opencode) model_name="gpt-5.6" ;;
    codex) model_name="gpt-5.5" ;;
    claude) model_name="sonnet" ;;
  esac
fi
model_ref="$model_name"
if [[ "$backend" == opencode && "$model_name" != */* ]]; then
  model_ref="${LLM_PROVIDER:-openai}/$model_name"
fi
printf '{"benchmark":"hewo-infrastructure-smoke","agent":"%s","backend":"%s","version":"%s","model":"%s","runtime":"%s","definition_revision":"%s","task":"%s","artifact":"%s","trajectory":"%s","scrubbed_trajectory":"%s"}\n' \
  "$name" "$backend" "${version:-unknown}" "$model_ref" "${runtime_version:-unknown}" "$definition_revision" "$task_file" "$workspace/artifacts/hewo-smoke.md" "$trajectory" "$scrubbed"
echo "evidence directory: $run_dir"
