#!/usr/bin/env bash
set -euo pipefail
name="${1:?usage: $0 <agent-name>}"
dir="src/$name"
test -f "$dir/agent.yaml"
test -f "$dir/runtime/identity.md"
test -f "$dir/runtime/opencode.json"
test -f "$dir/runtime/memory-policy.md"
test -d "$dir/runtime/knowledge"
test -d "$dir/runtime/workflows"
python3 -m json.tool "$dir/runtime/opencode.json" >/dev/null
echo "validated $dir"
