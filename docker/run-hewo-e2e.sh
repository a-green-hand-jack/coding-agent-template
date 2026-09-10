#!/usr/bin/env bash
# 开发与用户执行同一条 pi 原生命令；此文件只负责构建、注入与证据。
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${AGENT_NAME:-hewo}"
backend="${AGENT_BACKEND:-${HEWO_BACKEND:-pi}}"
provider="${LLM_PROVIDER:-}"
model="${LLM_MODEL:-}"
pi_auth_file="${PI_AUTH_FILE:-}"
pi_models_file="${PI_MODELS_FILE:-}"
workspace="${E2E_WORKSPACE:-}"
api_key_env=""; api_key_stdin=false; bundle=""
image=""; no_build=false; release_mode=false; artifact=""
allow_unauthenticated=false
usage() {
  printf '%s\n' "Usage: $0 [options] <task or pi arguments>" \
    '  --agent NAME           Agent name (default hewo)' \
    '  --backend NAME         pi only (alias pi-coding-agent)' \
    '  --provider NAME        Actual pi provider (required for model requests)' \
    '  --model NAME           Actual pi model ID (required for model requests)' \
    '  --pi-auth-file PATH    Mount one auth store read-only' \
    '  --pi-models-file PATH  Mount a model catalog read-only' \
    '  --api-key-env NAME     Read one host key variable' \
    '  --api-key-stdin        Read a key from stdin' \
    '  --bundle PATH          Mount a provider bundle read-only' \
    '  --workspace PATH       Mount the task workspace' \
    '  --release, --user-path Install only from a release artifact, then run pi' \
    '  --artifact PATH        Existing release tar.gz (implies --release)' \
    '  --image REF            Reuse an image; resolve and run its immutable ID' \
    '  --no-build             Reuse <agent>:e2e' \
    '  --allow-unauthenticated Infrastructure-only --help/--version checks' \
    '  --                     End helper options, pass remaining arguments to pi'
}
while (($#)); do
  case "$1" in
    --agent) name="${2:?missing agent}"; shift 2 ;;
    --backend) backend="${2:?missing backend}"; shift 2 ;;
    --provider) provider="${2:?missing provider}"; shift 2 ;;
    --model) model="${2:?missing model}"; shift 2 ;;
    --pi-auth-file) pi_auth_file="${2:?missing auth path}"; shift 2 ;;
    --pi-models-file) pi_models_file="${2:?missing models path}"; shift 2 ;;
    --api-key-env) api_key_env="${2:?missing variable}"; shift 2 ;;
    --api-key-stdin) api_key_stdin=true; shift ;;
    --bundle) bundle="${2:?missing bundle}"; shift 2 ;;
    --workspace) workspace="${2:?missing workspace}"; shift 2 ;;
    --release|--user-path) release_mode=true; shift ;;
    --artifact) artifact="${2:?missing artifact}"; release_mode=true; shift 2 ;;
    --image) image="${2:?missing image}"; shift 2 ;;
    --no-build) no_build=true; shift ;;
    --allow-unauthenticated) allow_unauthenticated=true; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
    *) break ;;
  esac
done
fail() { printf '%s\n' "$*" >&2; exit 2; }
[[ "$name" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]] || fail 'invalid agent name'
case "$backend" in pi|pi-coding-agent) backend=pi ;; *) fail "unsupported backend: $backend" ;; esac
(($#)) || { usage >&2; exit 2; }
# Do not let native arguments silently override the metadata or the package boundary.
for arg in "$@"; do
  case "$arg" in
    --provider|--provider=*|--model|--model=*|--api-key|--api-key=*|-e|--extension|--extension=*)
      fail "use helper options for provider/model/credentials; runtime loading is fixed: $arg" ;;
  esac
done
if [[ "$allow_unauthenticated" == true ]]; then
  [[ $# == 1 && ( "$1" == --help || "$1" == --version ) ]] || fail 'unauthenticated mode only supports -- --help or -- --version'
else
  [[ -n "$provider" && -n "$model" ]] || fail '--provider and --model are required'
fi
[[ "$release_mode" != true || ( -z "$image" && "$no_build" != true ) ]] || fail '--release cannot reuse an image: it must install the artifact'
credential_sources=(); env_args=(); mount_args=()
key_sources=0
[[ -z "$api_key_env" ]] || key_sources=$((key_sources + 1))
[[ "$api_key_stdin" != true ]] || key_sources=$((key_sources + 1))
[[ -z "$bundle" ]] || key_sources=$((key_sources + 1))
((key_sources <= 1)) || fail 'select only one API key source'
if [[ -n "$api_key_env" ]]; then
  [[ "$api_key_env" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || fail 'invalid key variable name'
  [[ -n "${!api_key_env:-}" ]] || fail "$api_key_env is not set"
  export E2E_PROVIDER_KEY="${!api_key_env}"
  env_args+=(--env E2E_PROVIDER_KEY)
  credential_sources+=("--api-key-env $api_key_env")
elif [[ "$api_key_stdin" == true ]]; then
  IFS= read -r E2E_PROVIDER_KEY || [[ -n "${E2E_PROVIDER_KEY:-}" ]]
  [[ -n "${E2E_PROVIDER_KEY:-}" ]] || fail 'provider key from stdin is empty'
  export E2E_PROVIDER_KEY
  env_args+=(--env E2E_PROVIDER_KEY)
  credential_sources+=(--api-key-stdin)
elif [[ -n "$bundle" ]]; then
  [[ -f "$bundle/manifest.json" && -f "$bundle/credential" ]] || fail 'invalid provider bundle'
  python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); assert m.get("provider")==sys.argv[2] and m.get("model")==sys.argv[3], "bundle provider/model mismatch"' "$bundle/manifest.json" "$provider" "$model"
  mount_args+=(--mount "type=bind,src=$(realpath "$bundle"),dst=/run/provider-bundle,readonly")
  credential_sources+=("--bundle $bundle")
fi
if [[ -n "$pi_auth_file" ]]; then
  [[ -f "$pi_auth_file" ]] || fail 'pi auth file does not exist'
  mount_args+=(--mount "type=bind,src=$(realpath "$pi_auth_file"),dst=/root/.pi/agent/auth.json,readonly")
  credential_sources+=("--pi-auth-file $pi_auth_file")
  if [[ -z "$pi_models_file" && -f "$(dirname "$pi_auth_file")/models.json" ]]; then
    pi_models_file="$(dirname "$pi_auth_file")/models.json"
  fi
fi
if [[ -n "$pi_models_file" ]]; then
  [[ -f "$pi_models_file" ]] || fail 'pi models file does not exist'
  mount_args+=(--mount "type=bind,src=$(realpath "$pi_models_file"),dst=/root/.pi/agent/models.json,readonly")
fi
[[ "$allow_unauthenticated" == true || ${#credential_sources[@]} -gt 0 ]] || fail 'no provider credential injected: use --pi-auth-file, --api-key-env, --api-key-stdin or --bundle'
if [[ -n "$workspace" ]]; then
  [[ -d "$workspace" ]] || fail 'workspace directory does not exist'
  mount_args+=(--mount "type=bind,src=$(realpath "$workspace"),dst=/workspace")
fi
for var in OPENAI_BASE_URL ANTHROPIC_BASE_URL; do
  [[ -z "${!var:-}" ]] || env_args+=(--env "$var")
done
scratch=""
cleanup() { if [[ -n "$scratch" ]]; then rm -rf -- "$scratch"; fi; }
trap cleanup EXIT
install_mode=current
if [[ "$release_mode" == true ]]; then
  install_mode=release
  scratch="$(mktemp -d "${TMPDIR:-/tmp}/agent-e2e.XXXXXX")"
  if [[ -z "$artifact" ]]; then
    "$root/.agents/scripts/freeze-agent-run.sh" --agent "$name" --into "$scratch/snapshot" >/dev/null
    version="${RELEASE_VERSION:-0.1.0}"
    "$scratch/snapshot/scripts/build-release.sh" "$name" "$version" >&2
    artifact="$scratch/snapshot/release/$name-$version.tar.gz"
  fi
  [[ -f "$artifact" ]] || fail 'release artifact does not exist'
  mkdir "$scratch/context"
  # Validate/extract once; parity compares precisely the payload installed below.
  python3 - "$artifact" "$scratch/context" "${scratch}/snapshot/src/$name/runtime" <<'PY'
import hashlib, pathlib, sys, tarfile
archive, destination, source = map(pathlib.Path, sys.argv[1:])
with tarfile.open(archive, 'r:gz') as tf:
    for m in tf.getmembers():
        p = pathlib.PurePosixPath(m.name)
        if p.is_absolute() or '..' in p.parts or m.issym() or m.islnk() or not (m.isdir() or m.isfile()):
            raise SystemExit('unsafe release member')
        if set(p.parts) & {'AGENTS.md', 'CLAUDE.md', '.agents', 'development', '.env', 'auth.json'}:
            raise SystemExit('development/credential file in release')
    tf.extractall(destination)
roots = list(destination.glob('*/runtime-package'))
if len(roots) != 1 or not (roots[0].parent / 'install.sh').is_file():
    raise SystemExit('release must contain one installer and runtime-package')
roots[0].parent.rename(destination / 'payload')
def files(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and not set(p.relative_to(root).parts) &
            {'AGENTS.md', 'CLAUDE.md', 'node_modules', '__pycache__', 'build'}
            and not any(x.endswith('.egg-info') for x in p.parts)}
if source.is_dir():
    if files(source) != files(destination / 'payload/runtime-package'):
        raise SystemExit('source/release artifact parity failed')
    print('artifact parity: OK', file=sys.stderr)
print('release archive structure: OK', file=sys.stderr)
PY
  # A clean dependency image receives only the extracted archive, never source.
  cat > "$scratch/context/Dockerfile" <<'DOCKER'
FROM node:22-bookworm-slim
ARG PI_PACKAGE=@earendil-works/pi-coding-agent
ARG PI_VERSION=latest
ARG AGENT_NAME=hewo
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --break-system-packages --no-cache-dir uv && npm install --global "${PI_PACKAGE}@${PI_VERSION}" --ignore-scripts --no-audit --no-fund
COPY payload /opt/release
RUN PREFIX=/opt/install AGENT_NAME="$AGENT_NAME" /opt/release/install.sh && test -f "/opt/install/lib/$AGENT_NAME/runtime-package/package.json" && diff -r --exclude=node_modules /opt/release/runtime-package "/opt/install/lib/$AGENT_NAME/runtime-package" && rm -rf /opt/release && mkdir -p /workspace /root/.pi/agent
WORKDIR /workspace
DOCKER
  docker build --build-arg "AGENT_NAME=$name" --build-arg "PI_PACKAGE=${PI_PACKAGE:-@earendil-works/pi-coding-agent}" --build-arg "PI_VERSION=${PI_VERSION:-latest}" --iidfile "$scratch/image-id" "$scratch/context" >&2
  image="$(<"$scratch/image-id")"
elif [[ -z "$image" && "$no_build" != true ]]; then
  scratch="$(mktemp -d "${TMPDIR:-/tmp}/agent-e2e.XXXXXX")"
  "$root/.agents/scripts/freeze-agent-run.sh" --agent "$name" --into "$scratch/snapshot" >/dev/null
  build_result="$("$root/.agents/scripts/build-agent-image.sh" --context "$scratch/snapshot")"
  while IFS='=' read -r key value; do [[ "$key" != AGENT_IMAGE_ID ]] || image="$value"; done <<< "$build_result"
else
  image="${image:-$name:e2e}"
fi
image_id="$(docker image inspect --format '{{.Id}}' "$image")"
[[ "$image_id" =~ ^sha256:[0-9a-f]{64}$ ]] || fail 'image did not resolve to an immutable ID'
credential_source=none
if ((${#credential_sources[@]})); then credential_source="$(IFS=,; printf '%s' "${credential_sources[*]}")"; fi
pi_args=(--no-session --no-context-files --no-extensions --no-skills --no-prompt-templates --no-themes -e "/opt/install/lib/$name/runtime-package")
[[ -z "$provider" ]] || pi_args+=(--provider "$provider")
[[ -z "$model" ]] || pi_args+=(--model "$model")
[[ -z "${LLM_VARIANT:-}" ]] || pi_args+=(--thinking "$LLM_VARIANT")
[[ -z "${AGENT_OUTPUT_FORMAT:-}" ]] || pi_args+=(--mode "$AGENT_OUTPUT_FORMAT")
pi_args+=(--print "$@")
printf 'run: backend=%s provider=%s model=%s credential_source=%s image=%s install=%s\n' "$backend" "$provider" "$model" "$credential_source" "$image_id" "$install_mode" >&2
set +e
docker run --rm "${env_args[@]}" "${mount_args[@]}" \
  --env PI_CODING_AGENT_DIR=/root/.pi/agent \
  --env "PATH=/opt/install/lib/$name/environment/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  --entrypoint bash "$image_id" -c '
    key_args=()
    if [[ -f /run/provider-bundle/credential ]]; then E2E_PROVIDER_KEY="$(</run/provider-bundle/credential)"; fi
    if [[ -n "${E2E_PROVIDER_KEY:-}" ]]; then key_args=(--api-key "$E2E_PROVIDER_KEY"); fi
    unset E2E_PROVIDER_KEY
    exec pi "${key_args[@]}" "$@"
  ' pi "${pi_args[@]}"
run_status=$?
set -e
run_mode=blocked
if [[ "$allow_unauthenticated" == true || " $* " == *' --help '* || " $* " == *' --version '* ]]; then run_mode=infrastructure-only
elif ((run_status == 0)); then run_mode=agent-behavior; fi
printf 'evidence: backend=%s provider=%s model=%s credential_source=%s image=%s install=%s exit=%s mode=%s\n' "$backend" "$provider" "$model" "$credential_source" "$image_id" "$install_mode" "$run_status" "$run_mode" >&2
exit "$run_status"
