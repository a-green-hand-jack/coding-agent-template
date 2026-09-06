#!/usr/bin/env bash
set -euo pipefail
name="${1:?usage: $0 <agent-name>}"
dir="src/$name"
test -f "$dir/identity.md"
test -f "$dir/opencode.json"
test -f "$dir/memory-policy.md"
python3 -m json.tool "$dir/opencode.json" >/dev/null
echo "validated $dir"
