#!/usr/bin/env bash
# 开发主入口之一：准备可复用环境并安装当前 runtime；不执行产品请求。
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
name="${AGENT_NAME:-hewo}"
environment="${VIRTUAL_ENV_PATH:-${VIRTUAL_ENV:-$root/.venv}}"
command -v uv >/dev/null || { printf 'Install uv before running setup-dev.sh.\n' >&2; exit 2; }
if [[ ! -x "$environment/bin/python" ]]; then
  uv venv "$environment" --python python3
fi
uv pip install --python "$environment/bin/python" -r "$root/requirements-dev.txt"
if [[ -f "$root/package-lock.json" ]]; then npm ci --ignore-scripts --no-audit --no-fund; fi
command -v pi >/dev/null || { printf 'Install pi yourself: npm install -g @earendil-works/pi-coding-agent\n' >&2; exit 2; }
AGENT_NAME="$name" PREFIX="${PREFIX:-$HOME/.local}" "$root/distribution/install.sh"
printf 'development environment: %s\n' "$environment"
printf 'tools PATH: %s/lib/%s/environment/bin\n' "${PREFIX:-$HOME/.local}" "$name"
printf 'runtime package: %s/lib/%s/runtime-package\n' "${PREFIX:-$HOME/.local}" "$name"
printf 'Use pi native loading as documented in USER.md; validate product requests only via docker/run-hewo-e2e.sh.\n'
