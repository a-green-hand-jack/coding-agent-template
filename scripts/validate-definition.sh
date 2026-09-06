#!/usr/bin/env bash
set -euo pipefail
name="${1:?usage: $0 <agent-name>}"
dir="src/$name"
test -f "$dir/agent.yaml"
test -f "$dir/runtime/identity.md"
test -f "$dir/runtime/opencode.json"
test -f "$dir/runtime/memory-policy.md"
test -d "$dir/runtime/knowledge"
test -d "$dir/runtime/skills"
test -d "$dir/runtime/workflows"
find "$dir/runtime/skills" -type f -name SKILL.md -print -quit | grep -q .
python3 -m json.tool "$dir/runtime/opencode.json" >/dev/null
python3 - "$dir/runtime/opencode.json" "$name" <<'PY'
import json
import sys

config = json.load(open(sys.argv[1], encoding="utf-8"))
name = sys.argv[2]
assert config.get("$schema") == "https://opencode.ai/config.json"
assert config.get("default_agent") == name
assert name in config.get("agent", {})
assert config["agent"][name].get("prompt")
assert "./skills" in config.get("skills", [])
PY
echo "validated $dir"
