#!/usr/bin/env bash
# One provider-backed benchmark run, and the evidence record for it.
#
# Everything that decides the outcome is pinned before the container starts:
# the image (by ID, not by tag), the definition revision, and — when this script
# runs from a frozen snapshot — the verifier and the trace collector too. The
# previous version computed the definition revision *after* the container
# finished, so editing the product during a long run stamped the evidence with a
# revision that had never run.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:-hewo}"
task_file="${2:-benchmarks/tasks/example-task.md}"
backend="${AGENT_BACKEND:-${HEWO_BACKEND:-pi}}"
provider="${LLM_PROVIDER:-}"
model="${LLM_MODEL:-}"
# A second-granularity name let two runs launched in the same second share an
# evidence directory. The suffix is echoed back in the record below so the
# directory stays discoverable.
run_dir="${BENCHMARK_RUN_DIR:-$root/artifacts/benchmark-$(date +%Y%m%d-%H%M%S)-$$}"
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

# Resolve the subject BEFORE the run, in one of three ways:
#  1. this script is executing from a frozen snapshot (the loop's background
#     mode), so the snapshot's own record is authoritative;
#  2. a caller pinned it explicitly through the environment;
#  3. standalone use, so freeze and build here and now.
snapshot_root=""
cleanup_snapshot() { [[ -n "$snapshot_root" ]] && rm -rf "$snapshot_root"; return 0; }
trap cleanup_snapshot EXIT

definition_revision="${AGENT_DEFINITION_REVISION:-}"
image_id="${AGENT_IMAGE_ID:-}"
if [[ -f "$root/.frozen.json" ]]; then
  definition_revision="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["definition_revision"])' "$root/.frozen.json")"
  if [[ -z "$image_id" ]]; then
    while IFS='=' read -r key value; do
      [[ "$key" == AGENT_IMAGE_ID ]] && image_id="$value"
    done < <("$root/scripts/build-agent-image.sh" --context "$root")
  fi
elif [[ -z "$image_id" || -z "$definition_revision" ]]; then
  snapshot_root="$(mktemp -d "${TMPDIR:-/tmp}/agent-benchmark.XXXXXX")"
  while IFS='=' read -r key value; do
    case "$key" in
      AGENT_DEFINITION_REVISION) definition_revision="$value" ;;
    esac
  done < <("$root/scripts/freeze-agent-run.sh" --agent "$name" --into "$snapshot_root/snapshot")
  while IFS='=' read -r key value; do
    [[ "$key" == AGENT_IMAGE_ID ]] && image_id="$value"
  done < <("$root/scripts/build-agent-image.sh" --context "$snapshot_root/snapshot")
fi
[[ -n "$image_id" && -n "$definition_revision" ]] || {
  echo "could not pin the image and definition revision before the run" >&2
  exit 2
}

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
./docker/run-hewo-e2e.sh --agent "$name" --backend "$backend" --provider "$provider" --model "$model" \
  --image "$image_id" --workspace "$workspace" "${auth_args[@]}" "$task_prompt" \
  >"$trajectory" 2>"$stderr_log"

# The verifier decides pass/fail, so it is part of the run, not part of the
# report. Executed through the same (possibly frozen) root as everything else.
ARTIFACT_PATH="$workspace/artifacts/hewo-smoke.md" \
  ./benchmarks/verifiers/example-verifier.sh
./scripts/collect-trace.sh "$trajectory" "$scrubbed" >/dev/null

# Fail closed on subject drift: the image that answered must still be the image
# that was pinned. A concurrent build that moved the tag, or a manual retag,
# makes this run blocked evidence rather than Agent behavior.
image_id_after="$(docker image inspect --format '{{.Id}}' "$image_id" 2>/dev/null || true)"
if [[ "$image_id_after" != "$image_id" ]]; then
  echo "image identity changed during the run; this is blocked evidence, not agent behavior" >&2
  exit 2
fi

# The version is a property of the definition, so it is read from the runtime
# manifest directly. It used to come from a release build that also did
# `rm -rf release/<name>-0.1.0`, which collided between concurrent runs and
# pinned every record to the literal version 0.1.0.
version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("version","unknown"))' "$root/src/$name/runtime/package.json")"
runtime_binary=pi
runtime_version="$(docker run --rm --entrypoint "$runtime_binary" "$image_id" --version 2>/dev/null | tail -n 1)"
model_name="$model"
model_ref="$model_name"
printf '{"benchmark":"hewo-infrastructure-smoke","agent":"%s","backend":"%s","provider":"%s","version":"%s","model":"%s","credential_source":"%s","runtime":"%s","image_id":"%s","definition_revision":"%s","task":"%s","artifact":"%s","trajectory":"%s","scrubbed_trajectory":"%s","run_dir":"%s"}\n' \
  "$name" "$backend" "$provider" "${version:-unknown}" "$model_ref" "$credential_source" "${runtime_version:-unknown}" "$image_id" "$definition_revision" "$task_file" "$workspace/artifacts/hewo-smoke.md" "$trajectory" "$scrubbed" "$run_dir"
echo "evidence directory: $run_dir"
