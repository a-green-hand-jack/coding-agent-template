#!/usr/bin/env bash
set -euo pipefail
input="${1:?usage: $0 <trace-file> [output-file]}"
output="${2:-${input%.*}.scrubbed.jsonl}"
sed -E 's/(OPENAI_API_KEY|ANTHROPIC_API_KEY|API_KEY|TOKEN|Authorization)[=:][^ ,"}]+/\1=[REDACTED]/Ig; s#/(Users|home)/[^ ]+#/[USER_PATH_REDACTED]#g' "$input" > "$output"
echo "wrote $output"
