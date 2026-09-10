#!/usr/bin/env bash
set -euo pipefail

provider="${1:?usage: $0 <provider> <model> <key-env> <output-dir>}"
model="${2:?usage: $0 <provider> <model> <key-env> <output-dir>}"
key_env="${3:?usage: $0 <provider> <model> <key-env> <output-dir>}"
output="${4:?usage: $0 <provider> <model> <key-env> <output-dir>}"

[[ "$key_env" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo "invalid key environment variable" >&2; exit 2; }
[[ -n "${!key_env:-}" ]] || { echo "$key_env is not set" >&2; exit 2; }
umask 077
mkdir -p "$output"
printf '{"provider":"%s","model":"%s","credential_env":"%s","version":1}\n' \
  "$provider" "$model" "$key_env" > "$output/manifest.json"
printf '%s' "${!key_env}" > "$output/credential"
chmod 600 "$output/credential" "$output/manifest.json"
echo "$output"
