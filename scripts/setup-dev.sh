#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m venv "${VIRTUAL_ENV_PATH:-$root/.venv}"
"${VIRTUAL_ENV_PATH:-$root/.venv}/bin/python" -m pip install --upgrade pip
"${VIRTUAL_ENV_PATH:-$root/.venv}/bin/pip" install -r "$root/requirements-dev.txt"
if command -v npm >/dev/null 2>&1 && test -f "$root/package-lock.json"; then
  npm ci
fi
echo "development environments ready; activate with: source .venv/bin/activate"
