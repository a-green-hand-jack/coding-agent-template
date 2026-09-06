#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:-hewo}"
task_file="${2:-benchmarks/tasks/example-task.md}"
run_dir="${BENCHMARK_RUN_DIR:-$root/artifacts/benchmark-$(date +%Y%m%d-%H%M%S)}"
workspace="$run_dir/workspace"
mkdir -p "$workspace" "$workspace/artifacts"

task_prompt="$(sed '/^#/d; /^$/d' "$task_file" | tr '\n' ' ')"
trajectory="$run_dir/trajectory.jsonl"
scrubbed="$run_dir/trajectory.scrubbed.jsonl"
stderr_log="$run_dir/stderr.log"

export AGENT_OUTPUT_FORMAT=json
./docker/run-e2e.sh --agent "$name" --workspace "$workspace" "$task_prompt" \
  >"$trajectory" 2>"$stderr_log"

ARTIFACT_PATH="$workspace/artifacts/hewo-smoke.md" \
  ./benchmarks/verifiers/example-verifier.sh
./scripts/collect-trace.sh "$trajectory" "$scrubbed" >/dev/null

version="$(./scripts/build-release.sh "$name" 0.1.0 >/dev/null 2>&1 && sed -n 's/.*"version":"\([^"]*\)".*/\1/p' "release/$name-0.1.0/release-manifest.json")"
runtime_version="$(docker run --rm --entrypoint opencode "$name:e2e" --version 2>/dev/null | tail -n 1)"
definition_revision="$(git rev-parse HEAD)+worktree-$(git diff --binary -- src/"$name" | sha256sum | cut -d' ' -f1)"
model="${LLM_PROVIDER:-openai}/${LLM_MODEL:-gpt-5.6}"
printf '{"benchmark":"hewo-infrastructure-smoke","agent":"%s","version":"%s","model":"%s","runtime":"%s","definition_revision":"%s","task":"%s","artifact":"%s","trajectory":"%s","scrubbed_trajectory":"%s"}\n' \
  "$name" "${version:-unknown}" "$model" "${runtime_version:-unknown}" "$definition_revision" "$task_file" "$workspace/artifacts/hewo-smoke.md" "$trajectory" "$scrubbed"
echo "evidence directory: $run_dir"
