#!/usr/bin/env bash
# Project-internal, product-external evaluation loop.
#
# This is deliberately a foreground C2 runner.  Background registration and
# cleanup belong to C3 and are not implemented here.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

agent="${AGENT_NAME:-hewo}"
backend="${AGENT_BACKEND:-${HEWO_BACKEND:-opencode}}"
provider="${LLM_PROVIDER:-}"
model="${LLM_MODEL:-}"
workspace=""
task_file=""
run_dir="${BENCHMARK_RUN_DIR:-}"
allow_unauthenticated=false
credential_flag=""
credential_value=""
positionals=()

usage() {
  cat <<'EOF'
Usage: ./scripts/run-agent-loop.sh [options] [task prompt]

Run the project-internal evaluation loop in this order:
  definition validation -> consistency audit -> infrastructure health -> benchmark

Options:
  --agent NAME                    Agent name (default: hewo)
  --backend NAME                  opencode, codex, claude, or pi
  --provider NAME                 Provider name
  --model NAME                    Model name
  --auth-file PATH                OpenCode auth store (opencode only)
  --api-key-env NAME              Key environment (opencode, or OPENAI_API_KEY for codex)
  --codex-auth-file PATH          Codex auth store (codex only)
  --claude-credentials-file PATH  Claude credentials (claude only)
  --claude-api-key-file PATH      Claude API key file (claude only)
  --pi-auth-file PATH             pi auth store (pi only)
  --credential-source SPEC         Explicit source, e.g. --credential-source --auth-file PATH
                                  or --credential-source PATH (backend default)
  --workspace PATH                Benchmark workspace directory
  --task-file PATH                Benchmark task file
  --run-dir PATH                  Benchmark evidence directory
  --allow-unauthenticated         Skip the provider-backed benchmark stage;
                                  successful runs are infrastructure-only (exit 3)
  -h, --help                      Show this help

Credential matrix (mismatches are rejected before any stage runs):
  opencode: --auth-file or --api-key-env
  codex:    --codex-auth-file or --api-key-env OPENAI_API_KEY
  claude:   --claude-credentials-file or --claude-api-key-file
  pi:       --pi-auth-file

The benchmark stage remains the single implementation of Docker E2E,
verification, and trace scrubbing. This runner only validates and orchestrates.
EOF
}

# Emit a concise machine-readable rejection record as well as a human-readable
# diagnostic. No provider command has been started when this function is used.
reject() {
  local message="$1"
  printf 'error: %s\n' "$message" >&2
  python3 - "$message" "$agent" "$backend" "$provider" "$model" <<'PY'
import json
import sys

message, agent, backend, provider, model = sys.argv[1:]
print(json.dumps({
    "summary_version": 1,
    "result": "rejected",
    "mode": "preflight",
    "agent": agent,
    "backend": backend,
    "provider": provider,
    "model": model,
    "error": message,
}, ensure_ascii=False, separators=(",", ":")))
PY
  exit 2
}

need_value() {
  local option="$1"
  (($# >= 2)) || reject "missing value for $option"
  [[ -n "$2" ]] || reject "empty value for $option"
}

set_credential() {
  local flag="$1"
  local value="$2"
  if [[ -n "$credential_flag" ]]; then
    reject "multiple credential sources supplied ($credential_flag and $flag)"
  fi
  credential_flag="$flag"
  credential_value="$value"
}

canonical_credential_flag() {
  case "$1" in
    --auth-file|auth-file) printf '%s' '--auth-file' ;;
    --api-key-env|api-key-env) printf '%s' '--api-key-env' ;;
    --codex-auth-file|codex-auth-file) printf '%s' '--codex-auth-file' ;;
    --claude-credentials-file|claude-credentials-file) printf '%s' '--claude-credentials-file' ;;
    --claude-api-key-file|claude-api-key-file) printf '%s' '--claude-api-key-file' ;;
    --pi-auth-file|pi-auth-file) printf '%s' '--pi-auth-file' ;;
    --bundle|bundle) printf '%s' '--bundle' ;;
    *) return 1 ;;
  esac
}

# Parse --credential-source in a few explicit, secret-free forms. A bare path
# is mapped to the backend's auth-store source after backend normalization.
parse_credential_source() {
  local spec="$1"
  local value="${2:-}"
  local flag

  if [[ "$spec" == *=* ]]; then
    value="${spec#*=}"
    spec="${spec%%=*}"
  fi
  if flag="$(canonical_credential_flag "$spec" 2>/dev/null)"; then
    [[ -n "$value" ]] || reject "missing value for --credential-source $spec"
    set_credential "$flag" "$value"
    return
  fi
  if [[ "$spec" == env:* ]]; then
    set_credential '--api-key-env' "${spec#env:}"
    return
  fi
  if [[ -n "$value" ]]; then
    reject "unknown credential source: $spec"
  fi
  # --credential-source PATH: infer the backend-specific read-only auth file.
  set_credential '--auto' "$spec"
}

while (($#)); do
  case "$1" in
    --agent)
      need_value "$1" "${2:-}"; agent="$2"; shift 2 ;;
    --agent=*) agent="${1#*=}"; [[ -n "$agent" ]] || reject 'empty value for --agent'; shift ;;
    --backend)
      need_value "$1" "${2:-}"; backend="$2"; shift 2 ;;
    --backend=*) backend="${1#*=}"; [[ -n "$backend" ]] || reject 'empty value for --backend'; shift ;;
    --provider)
      need_value "$1" "${2:-}"; provider="$2"; shift 2 ;;
    --provider=*) provider="${1#*=}"; [[ -n "$provider" ]] || reject 'empty value for --provider'; shift ;;
    --model)
      need_value "$1" "${2:-}"; model="$2"; shift 2 ;;
    --model=*) model="${1#*=}"; [[ -n "$model" ]] || reject 'empty value for --model'; shift ;;
    --workspace)
      need_value "$1" "${2:-}"; workspace="$2"; shift 2 ;;
    --workspace=*) workspace="${1#*=}"; [[ -n "$workspace" ]] || reject 'empty value for --workspace'; shift ;;
    --task-file)
      need_value "$1" "${2:-}"; task_file="$2"; shift 2 ;;
    --task-file=*) task_file="${1#*=}"; [[ -n "$task_file" ]] || reject 'empty value for --task-file'; shift ;;
    --run-dir)
      need_value "$1" "${2:-}"; run_dir="$2"; shift 2 ;;
    --run-dir=*) run_dir="${1#*=}"; [[ -n "$run_dir" ]] || reject 'empty value for --run-dir'; shift ;;
    --allow-unauthenticated) allow_unauthenticated=true; shift ;;
    --auth-file)
      need_value "$1" "${2:-}"; set_credential '--auth-file' "$2"; shift 2 ;;
    --auth-file=*) set_credential '--auth-file' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --auth-file'; shift ;;
    --api-key-env)
      need_value "$1" "${2:-}"; set_credential '--api-key-env' "$2"; shift 2 ;;
    --api-key-env=*) set_credential '--api-key-env' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --api-key-env'; shift ;;
    --codex-auth-file)
      need_value "$1" "${2:-}"; set_credential '--codex-auth-file' "$2"; shift 2 ;;
    --codex-auth-file=*) set_credential '--codex-auth-file' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --codex-auth-file'; shift ;;
    --claude-credentials-file)
      need_value "$1" "${2:-}"; set_credential '--claude-credentials-file' "$2"; shift 2 ;;
    --claude-credentials-file=*) set_credential '--claude-credentials-file' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --claude-credentials-file'; shift ;;
    --claude-api-key-file)
      need_value "$1" "${2:-}"; set_credential '--claude-api-key-file' "$2"; shift 2 ;;
    --claude-api-key-file=*) set_credential '--claude-api-key-file' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --claude-api-key-file'; shift ;;
    --pi-auth-file)
      need_value "$1" "${2:-}"; set_credential '--pi-auth-file' "$2"; shift 2 ;;
    --pi-auth-file=*) set_credential '--pi-auth-file' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --pi-auth-file'; shift ;;
    --bundle)
      need_value "$1" "${2:-}"; set_credential '--bundle' "$2"; shift 2 ;;
    --bundle=*) set_credential '--bundle' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --bundle'; shift ;;
    --credential-source)
      need_value "$1" "${2:-}"
      source_spec="$2"
      shift 2
      case "$source_spec" in
        --auth-file|auth-file|--api-key-env|api-key-env|--codex-auth-file|codex-auth-file|--claude-credentials-file|claude-credentials-file|--claude-api-key-file|claude-api-key-file|--pi-auth-file|pi-auth-file|--bundle|bundle)
          need_value '--credential-source' "${1:-}"
          parse_credential_source "$source_spec" "$1"
          shift ;;
        *) parse_credential_source "$source_spec" ;;
      esac
      ;;
    --credential-source=*) parse_credential_source "${1#*=}"; shift ;;
    --)
      shift
      while (($#)); do positionals+=("$1"); shift; done
      ;;
    -h|--help) usage; exit 0 ;;
    -*) reject "unknown option: $1" ;;
    *) positionals+=("$1"); shift ;;
  esac
done

case "$backend" in
  open-code) backend='opencode' ;;
  claude-code) backend='claude' ;;
  opencode|codex|claude|pi) ;;
  *) reject "unsupported backend: $backend" ;;
esac

case "$backend" in
  opencode) [[ -n "$provider" ]] || provider='openai'; [[ -n "$model" ]] || model='gpt-5.6' ;;
  codex) [[ -n "$provider" ]] || provider='openai'; [[ -n "$model" ]] || model='gpt-5.5' ;;
  claude) [[ -n "$provider" ]] || provider='anthropic'; [[ -n "$model" ]] || model='sonnet' ;;
  pi) [[ -n "$provider" ]] || provider='openai'; [[ -n "$model" ]] || model='gpt-5.5' ;;
esac

[[ "$agent" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || reject "invalid agent name: $agent"
[[ -n "$provider" ]] || reject 'provider must not be empty'
[[ -n "$model" ]] || reject 'model must not be empty'

if [[ "$credential_flag" == '--auto' ]]; then
  case "$backend" in
    opencode) credential_flag='--auth-file' ;;
    codex) credential_flag='--codex-auth-file' ;;
    claude) credential_flag='--claude-credentials-file' ;;
    pi) credential_flag='--pi-auth-file' ;;
  esac
fi

# Validate the complete source/backend matrix before creating a run directory or
# starting any of the four stages.
if [[ -n "$credential_flag" ]]; then
  case "$backend:$credential_flag" in
    opencode:--auth-file|opencode:--api-key-env) ;;
    codex:--codex-auth-file|codex:--api-key-env)
      if [[ "$credential_flag" == '--api-key-env' && "$credential_value" != 'OPENAI_API_KEY' ]]; then
        reject 'codex --api-key-env must be OPENAI_API_KEY'
      fi
      ;;
    claude:--claude-credentials-file|claude:--claude-api-key-file) ;;
    pi:--pi-auth-file) ;;
    *) reject "credential source $credential_flag does not match backend $backend" ;;
  esac

  case "$credential_flag" in
    --api-key-env)
      [[ "$credential_value" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || reject "invalid key environment name: $credential_value"
      [[ -n "${!credential_value:-}" ]] || reject "credential environment $credential_value is not set"
      ;;
    --auth-file|--codex-auth-file|--claude-credentials-file|--claude-api-key-file|--pi-auth-file)
      [[ -f "$credential_value" ]] || reject "credential file does not exist: $credential_value"
      ;;
    --bundle)
      reject 'provider bundles are not in the C2 credential matrix; use the backend-specific source flag'
      ;;
  esac
elif [[ "$allow_unauthenticated" != true ]]; then
  reject 'no credential source supplied; use an allowed source flag or --allow-unauthenticated'
fi

# Resolve the task only after argument and credential preflight. A positional
# non-file argument is a convenience task prompt; --task-file remains explicit.
tmp_dir=''
if ((${#positionals[@]} > 0)); then
  if [[ -n "$task_file" ]]; then
    reject 'do not combine --task-file with a positional task prompt'
  fi
  if ((${#positionals[@]} == 1)) && [[ -f "${positionals[0]}" ]]; then
    task_file="${positionals[0]}"
  else
    tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/agent-loop.XXXXXX")" || reject 'could not create temporary loop directory'
    task_file="$tmp_dir/task.md"
    printf '%s\n' "${positionals[*]}" >"$task_file" || reject 'could not write temporary task file'
  fi
fi
if [[ -z "$task_file" ]]; then
  task_file='benchmarks/tasks/example-task.md'
fi
if [[ "$task_file" != /* ]]; then task_file="$root/$task_file"; fi
if [[ "$allow_unauthenticated" != true ]]; then
  [[ -f "$task_file" ]] || reject "task file does not exist: $task_file"
fi

if [[ -n "$workspace" ]]; then
  mkdir -p "$workspace" || reject "could not create workspace: $workspace"
  workspace="$(cd "$workspace" && pwd)"
fi
if [[ -n "$run_dir" ]]; then
  mkdir -p "$run_dir" || reject "could not create run directory: $run_dir"
  run_dir="$(cd "$run_dir" && pwd)"
fi

if [[ -z "$tmp_dir" ]]; then
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/agent-loop.XXXXXX")" || exit 2
fi
trap 'rm -rf "$tmp_dir"' EXIT
stage_file="$tmp_dir/stages.tsv"
: >"$stage_file"

run_stage() {
  local stage="$1"
  shift
  local log="$tmp_dir/${stage}.log"
  local code
  "$@" >"$log" 2>&1
  code=$?
  # Keep command diagnostics out of stdout so stdout remains one JSON record.
  cat "$log" >&2
  if [[ "$code" -eq 0 ]]; then
    printf '%s\tpassed\t0\n' "$stage" >>"$stage_file"
  else
    printf '%s\tfailed\t%s\n' "$stage" "$code" >>"$stage_file"
  fi
  return "$code"
}

record_skipped() {
  printf '%s\tskipped\t-\n' "$1" >>"$stage_file"
}

# The preflight stages intentionally use the exact repository entrypoints from
# the plan. Do not replace these with duplicated checks or backend commands.
loop_status=0
if run_stage definition_validation ./scripts/validate-definition.sh "$agent"; then
  :
else
  loop_status=1
fi
if [[ "$loop_status" -eq 0 ]]; then
  if run_stage consistency_audit python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent "$agent" --strict; then
    :
  else
    loop_status=1
  fi
else
  record_skipped consistency_audit
fi
if [[ "$loop_status" -eq 0 ]]; then
  if run_stage infrastructure_health python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py --agent "$agent"; then
    :
  else
    loop_status=1
  fi
else
  record_skipped infrastructure_health
fi

benchmark_summary_file="$tmp_dir/benchmark-summary.json"
benchmark_ran=false
if [[ "$allow_unauthenticated" == true ]]; then
  record_skipped benchmark
elif [[ "$loop_status" -ne 0 ]]; then
  record_skipped benchmark
else
  # Pass only the selected credential source into the benchmark convention;
  # the benchmark maps it to the explicit Docker helper flag.
  unset OPENCODE_AUTH_FILE CODEX_AUTH_FILE CLAUDE_CREDENTIALS_FILE CLAUDE_API_KEY_FILE PI_AUTH_FILE BENCHMARK_API_KEY_ENV BENCHMARK_WORKSPACE
  export AGENT_BACKEND="$backend" LLM_PROVIDER="$provider" LLM_MODEL="$model"
  case "$credential_flag" in
    --auth-file) export OPENCODE_AUTH_FILE="$credential_value" ;;
    --codex-auth-file) export CODEX_AUTH_FILE="$credential_value" ;;
    --claude-credentials-file) export CLAUDE_CREDENTIALS_FILE="$credential_value" ;;
    --claude-api-key-file) export CLAUDE_API_KEY_FILE="$credential_value" ;;
    --pi-auth-file) export PI_AUTH_FILE="$credential_value" ;;
    --api-key-env)
      export BENCHMARK_API_KEY_ENV="$credential_value"
      export "$credential_value"
      ;;
  esac
  [[ -n "$workspace" ]] && export BENCHMARK_WORKSPACE="$workspace"
  [[ -n "$run_dir" ]] && export BENCHMARK_RUN_DIR="$run_dir"

  benchmark_ran=true
  if run_stage benchmark ./scripts/run-benchmark.sh "$agent" "$task_file"; then
    :
  else
    loop_status=1
  fi

  # Extract the benchmark's own JSON record without trusting incidental command
  # output. A successful benchmark with no machine-readable record is a loop
  # failure, not a passing provider-backed result.
  python3 - "$tmp_dir/benchmark.log" "$benchmark_summary_file" <<'PY'
import json
import sys

source, destination = sys.argv[1:]
found = None
try:
    lines = open(source, encoding="utf-8", errors="replace").read().splitlines()
except OSError:
    lines = []
for line in reversed(lines):
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        continue
    if isinstance(value, dict) and ("artifact" in value or "scrubbed_trajectory" in value):
        found = value
        break
if found is None:
    raise SystemExit(1)
with open(destination, "w", encoding="utf-8") as handle:
    json.dump(found, handle, ensure_ascii=False)
PY
  parse_status=$?
  if [[ "$parse_status" -ne 0 ]]; then
    printf 'error: benchmark did not produce a machine-readable summary\n' >&2
    loop_status=1
  fi
fi

if [[ "$allow_unauthenticated" == true && "$loop_status" -eq 0 ]]; then
  result='infrastructure-only'
  mode='infrastructure-only'
  result_code=3
elif [[ "$loop_status" -eq 0 ]]; then
  result='passed'
  mode='provider-backed'
  result_code=0
else
  result='failed'
  mode='provider-backed'
  result_code=1
fi

# Build the final record with Python so paths, task names, and diagnostics are
# JSON escaped correctly. The credential value is never read or emitted; only
# its allowlisted flag/path (or environment variable name) is reported.
python3 - "$stage_file" "$benchmark_summary_file" "$agent" "$backend" "$provider" "$model" "$credential_flag" "$credential_value" "$task_file" "$workspace" "$run_dir" "$result" "$mode" "$result_code" "$benchmark_ran" <<'PY'
import json
import os
import sys

(
    stage_path,
    benchmark_path,
    agent,
    backend,
    provider,
    model,
    credential_flag,
    credential_value,
    task_file,
    workspace,
    run_dir,
    result,
    mode,
    result_code,
    benchmark_ran,
) = sys.argv[1:]

stages = {}
try:
    lines = open(stage_path, encoding="utf-8").read().splitlines()
except OSError:
    lines = []
for line in lines:
    parts = line.split("\t")
    if len(parts) != 3:
        continue
    name, status, code = parts
    item = {"status": status}
    if code != "-":
        try:
            item["exit_code"] = int(code)
        except ValueError:
            item["exit_code"] = code
    stages[name] = item

benchmark = None
if os.path.isfile(benchmark_path):
    try:
        with open(benchmark_path, encoding="utf-8") as handle:
            benchmark = json.load(handle)
    except (OSError, json.JSONDecodeError):
        benchmark = None

if credential_flag:
    credential = {"flag": credential_flag}
    if credential_flag == "--api-key-env":
        credential["environment"] = credential_value
        credential["display"] = f"{credential_flag} {credential_value}"
    else:
        credential["path"] = credential_value
        credential["display"] = f"{credential_flag} {credential_value}"
else:
    credential = {"flag": None, "display": "none"}

artifact_paths = {
    "artifact": benchmark.get("artifact") if isinstance(benchmark, dict) else None,
    "trajectory": benchmark.get("trajectory") if isinstance(benchmark, dict) else None,
    "scrubbed_trajectory": benchmark.get("scrubbed_trajectory") if isinstance(benchmark, dict) else None,
}
summary = {
    "summary_version": 1,
    "result": result,
    "mode": mode,
    "exit_code": int(result_code),
    "agent": agent,
    "backend": backend,
    "provider": provider,
    "model": model,
    "credential_source": credential["display"],
    "credential_source_flag": credential.get("flag"),
    "credential_source_path": credential.get("path"),
    "credential": credential,
    "task_file": task_file,
    "workspace": workspace or None,
    "run_dir": run_dir or None,
    "stages": stages,
    "stage_results": [dict({"stage": name}, **value) for name, value in stages.items()],
    "artifact_paths": artifact_paths,
    "artifact": artifact_paths["artifact"],
    "trajectory": artifact_paths["trajectory"],
    "scrubbed_trajectory": artifact_paths["scrubbed_trajectory"],
    "benchmark": benchmark,
    "benchmark_ran": benchmark_ran == "true",
}
print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
PY

exit "$result_code"
