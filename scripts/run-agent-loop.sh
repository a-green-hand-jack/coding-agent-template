#!/usr/bin/env bash
# Project-internal, product-external evaluation loop.
#
# Long provider-backed validation can be submitted as a registered background
# run (`--background`) so the developer session stays interactive.  A
# registered run records secret-free metadata only, is queryable
# (`--list-runs`, `--run-status`) and is removed once its result is consumed
# (`--clean-run`).
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

agent="${AGENT_NAME:-hewo}"
backend="${AGENT_BACKEND:-${HEWO_BACKEND:-pi}}"
provider="${LLM_PROVIDER:-}"
model="${LLM_MODEL:-}"
workspace=""
task_file=""
run_dir="${BENCHMARK_RUN_DIR:-}"
allow_unauthenticated=false
credential_flag=""
credential_value=""
positionals=()
background=false
query_action=""
query_id=""

# Registered background runs live outside the repository so evidence is never
# committed by accident.
state_root="${AGENT_LOOP_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-loop}"
runs_root="$state_root/runs"

usage() {
  cat <<'EOF'
Usage: ./scripts/run-agent-loop.sh [options] [task prompt]

Run the project-internal evaluation loop in this order:
  definition validation -> consistency audit -> infrastructure health -> benchmark

Options:
  --agent NAME                    Agent name (default: hewo)
  --backend NAME                  pi only (alias: pi-coding-agent)
  --provider NAME                 pi provider name (default: openai)
  --model NAME                    pi model pattern (default: gpt-5.5)
  --pi-auth-file PATH             pi auth store, mounted read-only
  --api-key-env NAME              Host variable holding the provider key
  --credential-source SPEC         Explicit source, e.g. --credential-source --pi-auth-file PATH
                                  or --credential-source PATH (pi auth store)
  --workspace PATH                Benchmark workspace directory
  --task-file PATH                Benchmark task file
  --run-dir PATH                  Benchmark evidence directory
  --allow-unauthenticated         Skip the provider-backed benchmark stage;
                                  successful runs are infrastructure-only (exit 3)
  -h, --help                      Show this help

Registered background runs (for long provider-backed validation):
  --background                    Validate the invocation, then detach the loop
                                  and print the run record as JSON
  --list-runs                     List registered runs as JSON
  --run-status ID                 Print one run's record, including its summary
  --clean-run ID|all              Remove a finished run once consumed

A background run is registered under
$AGENT_LOOP_STATE_DIR (default ${XDG_STATE_HOME:-$HOME/.local/state}/agent-loop).
Its metadata records the credential-source flag and path or variable NAME only,
never a credential value. The whole preflight (backend, credential matrix,
task, workspace) runs in the foreground, so an invalid invocation is rejected
before anything is detached.

Credential matrix (mismatches are rejected before any stage runs):
  pi: --pi-auth-file PATH or --api-key-env NAME

Backends other than pi are rejected; there is no fallback default.

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
    --api-key-env|api-key-env) printf '%s' '--api-key-env' ;;
    --pi-auth-file|pi-auth-file) printf '%s' '--pi-auth-file' ;;
    *) return 1 ;;
  esac
}

# Parse --credential-source in a few explicit, secret-free forms. A bare path
# is mapped to the pi auth store after backend normalization.
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
  # --credential-source PATH: infer the pi read-only auth store.
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
    --background) background=true; shift ;;
    --list-runs) query_action='list'; shift ;;
    --run-status)
      need_value "$1" "${2:-}"; query_action='status'; query_id="$2"; shift 2 ;;
    --run-status=*) query_action='status'; query_id="${1#*=}"; [[ -n "$query_id" ]] || reject 'empty value for --run-status'; shift ;;
    --clean-run)
      need_value "$1" "${2:-}"; query_action='clean'; query_id="$2"; shift 2 ;;
    --clean-run=*) query_action='clean'; query_id="${1#*=}"; [[ -n "$query_id" ]] || reject 'empty value for --clean-run'; shift ;;
    --api-key-env)
      need_value "$1" "${2:-}"; set_credential '--api-key-env' "$2"; shift 2 ;;
    --api-key-env=*) set_credential '--api-key-env' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --api-key-env'; shift ;;
    --pi-auth-file)
      need_value "$1" "${2:-}"; set_credential '--pi-auth-file' "$2"; shift 2 ;;
    --pi-auth-file=*) set_credential '--pi-auth-file' "${1#*=}"; [[ -n "$credential_value" ]] || reject 'empty value for --pi-auth-file'; shift ;;
    --bundle|--bundle=*)
      # Accepted by name only so the diagnostic stays specific instead of
      # degrading to "unknown option". The benchmark stage has no bundle path.
      reject 'provider bundles are not in this runner'"'"'s credential matrix; use --pi-auth-file or --api-key-env' ;;
    --credential-source)
      need_value "$1" "${2:-}"
      source_spec="$2"
      shift 2
      case "$source_spec" in
        --api-key-env|api-key-env|--pi-auth-file|pi-auth-file)
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

# --- Registered background runs ---------------------------------------------
# Queries are pure reads of the run registry and must not be affected by the
# backend/credential preflight below.

run_id_re='^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}$'

query_error() {
  printf 'error: %s\n' "$1" >&2
  python3 -c 'import json,sys; print(json.dumps({"summary_version":1,"result":"rejected","mode":"registry","error":sys.argv[1]},ensure_ascii=False,separators=(",",":")))' "$1"
  exit 2
}

# Read one run's directory into a JSON object. `state` is derived from the
# recorded exit code, or from whether the process is still alive, so a killed
# run does not stay "running" forever.
emit_run_record() {
  python3 - "$1" <<'PY'
import json
import os
import sys

run = sys.argv[1]


def read(name):
    try:
        with open(os.path.join(run, name), encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


record = {"run_id": os.path.basename(run)}
try:
    with open(os.path.join(run, "meta.json"), encoding="utf-8") as handle:
        record.update(json.load(handle))
except (OSError, json.JSONDecodeError):
    record["meta_error"] = "run metadata is missing or unreadable"

exit_code = read("exit_code")
pid = read("pid")
if exit_code:
    code = int(exit_code) if exit_code.lstrip("-").isdigit() else exit_code
    record["exit_code"] = code
    record["state"] = {0: "completed", 3: "infrastructure-only"}.get(code, "failed")
elif pid.isdigit() and os.path.isdir(f"/proc/{pid}"):
    record["state"] = "running"
    record["pid"] = int(pid)
elif pid:
    record["state"] = "abandoned"
    record["detail"] = "the run process is gone and recorded no exit code"
else:
    record["state"] = "unknown"

record["log"] = os.path.join(run, "output.log")
summary_path = os.path.join(run, "summary.json")
if os.path.isfile(summary_path):
    try:
        with open(summary_path, encoding="utf-8") as handle:
            record["summary"] = json.load(handle)
    except (OSError, json.JSONDecodeError):
        record["summary"] = None
        record["summary_error"] = "the run produced no machine-readable summary"
print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
PY
}

if [[ -n "$query_action" ]]; then
  case "$query_action" in
    list)
      if [[ ! -d "$runs_root" ]]; then
        printf '[]\n'
        exit 0
      fi
      records=()
      for run in "$runs_root"/*; do
        [[ -d "$run" ]] || continue
        records+=("$(emit_run_record "$run")")
      done
      if ((${#records[@]} == 0)); then
        printf '[]\n'
      else
        printf '%s\n' "${records[@]}" | python3 -c 'import json,sys; print(json.dumps([json.loads(line) for line in sys.stdin if line.strip()],ensure_ascii=False,separators=(",",":")))'
      fi
      exit 0 ;;
    status)
      [[ "$query_id" =~ $run_id_re ]] || query_error "invalid run id: $query_id"
      [[ -d "$runs_root/$query_id" ]] || query_error "no such registered run: $query_id"
      emit_run_record "$runs_root/$query_id"
      exit 0 ;;
    clean)
      if [[ "$query_id" == all ]]; then
        removed=()
        if [[ -d "$runs_root" ]]; then
          for run in "$runs_root"/*; do
            [[ -d "$run" ]] || continue
            # A live run is never removed: that would orphan the process and
            # lose the only record of it.
            if [[ "$(emit_run_record "$run" | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')" == running ]]; then
              continue
            fi
            rm -rf "$run" && removed+=("$(basename "$run")")
          done
        fi
        printf '%s' "${removed[*]:-}" | python3 -c 'import json,sys; ids=sys.stdin.read().split(); print(json.dumps({"summary_version":1,"result":"cleaned","removed":ids,"count":len(ids)},ensure_ascii=False,separators=(",",":")))'
        exit 0
      fi
      [[ "$query_id" =~ $run_id_re ]] || query_error "invalid run id: $query_id"
      [[ -d "$runs_root/$query_id" ]] || query_error "no such registered run: $query_id"
      if [[ "$(emit_run_record "$runs_root/$query_id" | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')" == running ]]; then
        query_error "run $query_id is still running; wait for it or stop it first"
      fi
      rm -rf "$runs_root/$query_id"
      python3 -c 'import json,sys; print(json.dumps({"summary_version":1,"result":"cleaned","removed":[sys.argv[1]],"count":1},ensure_ascii=False,separators=(",",":")))' "$query_id"
      exit 0 ;;
  esac
fi

if [[ "$background" == true && -n "${AGENT_LOOP_BACKGROUND_CHILD:-}" ]]; then
  reject 'a background run must not request another background run'
fi

# pi is the only supported backend. Another backend is rejected outright rather
# than coerced to pi.
case "$backend" in
  pi|pi-coding-agent) backend='pi' ;;
  *) reject "unsupported backend: $backend (this Agent supports pi only)" ;;
esac

[[ -n "$provider" ]] || provider='openai'
[[ -n "$model" ]] || model='gpt-5.5'

[[ "$agent" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || reject "invalid agent name: $agent"
[[ -n "$provider" ]] || reject 'provider must not be empty'
[[ -n "$model" ]] || reject 'model must not be empty'

if [[ "$credential_flag" == '--auto' ]]; then
  credential_flag='--pi-auth-file'
fi

# Validate the complete source/backend matrix before creating a run directory or
# starting any of the four stages.
if [[ -n "$credential_flag" ]]; then
  case "$backend:$credential_flag" in
    pi:--pi-auth-file|pi:--api-key-env) ;;
    *) reject "credential source $credential_flag does not match backend $backend" ;;
  esac

  case "$credential_flag" in
    --api-key-env)
      [[ "$credential_value" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || reject "invalid key environment name: $credential_value"
      [[ -n "${!credential_value:-}" ]] || reject "credential environment $credential_value is not set"
      ;;
    --pi-auth-file)
      [[ -f "$credential_value" ]] || reject "credential file does not exist: $credential_value"
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

# The full preflight has now passed, so the invocation is known to be valid.
# Only at this point is it safe to detach: an invalid invocation must fail in
# the developer's terminal, never inside a background run they have to query.
if [[ "$background" == true ]]; then
  run_id="$(date -u +%Y%m%dT%H%M%SZ)-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
  run="$runs_root/$run_id"
  mkdir -p "$run" || reject "could not create the run registry entry: $run"
  chmod 700 "$state_root" "$run" 2>/dev/null || true

  # The task travels with the run: the parent's temporary directory is removed
  # when the parent exits, which would delete a prompt written from argv.
  cp "$task_file" "$run/task.md" || reject "could not stage the task file for the background run"

  child_args=(
    --agent "$agent"
    --backend "$backend"
    --provider "$provider"
    --model "$model"
    --task-file "$run/task.md"
  )
  [[ -n "$workspace" ]] && child_args+=(--workspace "$workspace")
  [[ -n "$run_dir" ]] && child_args+=(--run-dir "$run_dir")
  [[ "$allow_unauthenticated" == true ]] && child_args+=(--allow-unauthenticated)
  [[ -n "$credential_flag" ]] && child_args+=("$credential_flag" "$credential_value")

  # Secret-free metadata only: the credential-source flag plus its path or the
  # NAME of the environment variable, never a credential value.
  python3 - "$run/meta.json" "$run_id" "$agent" "$backend" "$provider" "$model" \
    "$credential_flag" "$credential_value" "$run/task.md" "$workspace" "$run_dir" \
    "$allow_unauthenticated" <<'PY'
import json
import sys
from datetime import datetime, timezone

(
    destination,
    run_id,
    agent,
    backend,
    provider,
    model,
    credential_flag,
    credential_value,
    task_file,
    workspace,
    run_dir,
    allow_unauthenticated,
) = sys.argv[1:]

if credential_flag == "--api-key-env":
    credential = {"flag": credential_flag, "environment": credential_value,
                  "display": f"{credential_flag} {credential_value}"}
elif credential_flag:
    credential = {"flag": credential_flag, "path": credential_value,
                  "display": f"{credential_flag} {credential_value}"}
else:
    credential = {"flag": None, "display": "none"}

with open(destination, "w", encoding="utf-8") as handle:
    json.dump(
        {
            "registry_version": 1,
            "run_id": run_id,
            "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": agent,
            "backend": backend,
            "provider": provider,
            "model": model,
            "credential_source": credential["display"],
            "credential": credential,
            "task_file": task_file,
            "workspace": workspace or None,
            "run_dir": run_dir or None,
            "mode": "infrastructure-only" if allow_unauthenticated == "true" else "provider-backed",
        },
        handle,
        ensure_ascii=False,
    )
PY

  # setsid where available so the run survives the developer's shell; the loop
  # records its own exit code so a query can tell "finished" from "killed".
  launcher=(setsid)
  command -v setsid >/dev/null 2>&1 || launcher=(nohup)
  AGENT_LOOP_BACKGROUND_CHILD=1 "${launcher[@]}" bash -c '
    run="$1"; shift
    script="$1"; shift
    "$script" "$@" >"$run/summary.json" 2>"$run/output.log"
    code=$?
    printf "%s\n" "$code" >"$run/exit_code"
  ' _ "$run" "$root/scripts/run-agent-loop.sh" "${child_args[@]}" >/dev/null 2>&1 &
  child_pid=$!
  printf '%s\n' "$child_pid" >"$run/pid"
  disown "$child_pid" 2>/dev/null || true

  rm -rf "${tmp_dir:-/nonexistent}"
  emit_run_record "$run"
  printf 'registered background run %s; query it with --run-status %s\n' "$run_id" "$run_id" >&2
  exit 0
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
  unset PI_AUTH_FILE BENCHMARK_API_KEY_ENV BENCHMARK_WORKSPACE
  export AGENT_BACKEND="$backend" LLM_PROVIDER="$provider" LLM_MODEL="$model"
  case "$credential_flag" in
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
