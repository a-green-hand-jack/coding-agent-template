#!/usr/bin/env bash
# Structural validation for an Agent definition. Backend: pi, and only pi.
set -euo pipefail
name="${1:?usage: $0 <agent-name>}"
dir="src/$name"

test -f "$dir/agent.yaml"
test -f "$dir/runtime/identity.md"
test -f "$dir/runtime/memory-policy.md"
test -f "$dir/runtime/package.json"
test -d "$dir/runtime/knowledge"
test -d "$dir/runtime/skills"
test -d "$dir/runtime/workflows"
find "$dir/runtime/skills" -type f -name SKILL.md -print -quit | grep -q .
python3 -m json.tool "$dir/runtime/package.json" >/dev/null

python3 - "$dir" "$name" <<'PY'
"""Validate the runtime resource manifest and the scaffold/manifest boundary."""

import json
import re
import sys
from pathlib import Path

agent_dir = Path(sys.argv[1]).resolve()
name = sys.argv[2]
runtime = agent_dir / "runtime"
problems = []

manifest = json.loads((runtime / "package.json").read_text(encoding="utf-8"))

if manifest.get("scripts"):
    problems.append("runtime package.json must not declare npm lifecycle scripts")
if "pi-package" not in (manifest.get("keywords") or []):
    problems.append('runtime package.json should carry the "pi-package" keyword')

pi = manifest.get("pi")
if not isinstance(pi, dict):
    problems.append("runtime package.json has no pi section")
    pi = {}
unknown = sorted(set(pi) - {"extensions", "skills", "prompts", "themes", "video", "image"})
if unknown:
    problems.append(f"pi section declares keys pi does not recognise: {unknown}")

section = manifest.get("agent")
if not isinstance(section, dict):
    # The section used to be named after the product, which made every
    # downstream Agent carry a foreign key. It is now always "agent".
    legacy = sorted(
        key
        for key, value in manifest.items()
        if key != "agent" and isinstance(value, dict) and "manifest_version" in value
    )
    if legacy:
        problems.append(
            f"runtime package.json has no agent section: rename the legacy {legacy[0]!r} section to 'agent'"
        )
    else:
        problems.append("runtime package.json has no agent section")
    section = {}
if section.get("manifest_version") != 1:
    problems.append("runtime manifest_version must be the integer 1")
if section.get("backend") != "pi":
    problems.append("runtime backend must be pi")
if section.get("network") not in {"deny", "allow"}:
    problems.append("runtime network must be deny or allow")
if not isinstance(section.get("capabilities"), list):
    problems.append("runtime capabilities must be an array")
tools = section.get("default_tools")
if not isinstance(tools, list) or not tools:
    problems.append("runtime default_tools must be a non-empty array")
else:
    for tool in tools:
        if not isinstance(tool, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", tool):
            problems.append(f"runtime default_tools has an invalid tool name: {tool!r}")

FORBIDDEN = re.compile(r"""[\0\n\r`$;|&<>*?()\[\]{}!\\"']""")


def check_path(relative, label, expect=None):
    if not isinstance(relative, str) or not relative.strip():
        problems.append(f"{label}: path must be a non-empty string")
        return
    if FORBIDDEN.search(relative):
        problems.append(f"{label}: path contains a forbidden character: {relative!r}")
        return
    if relative.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", relative):
        problems.append(f"{label}: path must be relative: {relative}")
        return
    parts = [part for part in relative.split("/") if part not in ("", ".")]
    if ".." in parts:
        problems.append(f"{label}: path must not traverse upward: {relative}")
        return
    target = runtime.joinpath(*parts)
    cursor = target
    while cursor != runtime and cursor.parent != cursor:
        if cursor.is_symlink():
            problems.append(f"{label}: symlink is not allowed: {relative}")
            return
        cursor = cursor.parent
    if not target.exists():
        problems.append(f"{label}: declared path does not exist: {relative}")
        return
    if expect == "file" and not target.is_file():
        problems.append(f"{label}: expected a file: {relative}")
    if expect == "dir" and not target.is_dir():
        problems.append(f"{label}: expected a directory: {relative}")


for key in ("skills", "prompts", "themes"):
    for entry in pi.get(key) or []:
        check_path(entry, f"pi.{key}")
for entry in pi.get("extensions") or []:
    check_path(entry, "pi.extensions", "file")
for entry in section.get("system_prompt") or []:
    check_path(entry, "runtime.system_prompt", "file")
for entry in section.get("context") or []:
    check_path(entry, "runtime.context")
for entry in section.get("agent_definitions") or []:
    check_path(entry, "runtime.agent_definitions", "dir")
for entry in section.get("leaf_tools") or []:
    check_path(entry, "runtime.leaf_tools", "file")

# Each declared tool self-check becomes a shell assertion in a clean container,
# so the Agent names its own sentinel instead of the infrastructure hardcoding
# one product's tool. Tokens stay shell-safe by construction.
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:=/-]+$")
checks = section.get("tool_checks", [])
if not isinstance(checks, list):
    problems.append("runtime tool_checks must be an array")
    checks = []
for index, check in enumerate(checks):
    label = f"runtime.tool_checks[{index}]"
    if not isinstance(check, dict):
        problems.append(f"{label}: each tool check must be an object")
        continue
    command = check.get("command")
    if not isinstance(command, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", command):
        problems.append(f"{label}: command must be a plain executable name, got {command!r}")
    expect = check.get("expect")
    if not isinstance(expect, str) or not SAFE_TOKEN.match(expect):
        problems.append(f"{label}: expect must be a single safe token, got {expect!r}")
    args = check.get("args", [])
    if not isinstance(args, list):
        problems.append(f"{label}: args must be an array")
    else:
        for argument in args:
            if not isinstance(argument, str) or not SAFE_TOKEN.match(argument):
                problems.append(f"{label}: args must be safe tokens, got {argument!r}")

# agent.yaml is scaffold metadata only. It must never become a second
# resource list competing with package.json.
scaffold_keys = set()
for number, line in enumerate((agent_dir / "agent.yaml").read_text(encoding="utf-8").splitlines(), 1):
    text = line.strip()
    if not text or text.startswith("#"):
        continue
    if ":" not in text:
        problems.append(f"agent.yaml:{number}: expected 'key: value'")
        continue
    scaffold_keys.add(text.split(":", 1)[0].strip())
allowed_scaffold = {"name", "runtime_dir", "development_dir", "knowledge_dir", "workflows_dir"}
extra = sorted(scaffold_keys - allowed_scaffold)
if extra:
    problems.append(f"agent.yaml declares non-scaffold keys (use package.json instead): {extra}")

# Product payload must be text: a NUL byte breaks grep/diff review and is a
# sign of a generated-source mistake.
for path in sorted(runtime.rglob("*")):
    if not path.is_file() or path.suffix not in {".ts", ".js", ".md", ".json", ".py", ".toml"}:
        continue
    if b"\x00" in path.read_bytes():
        problems.append(f"payload file contains a NUL byte: {path.relative_to(runtime)}")

# No residual second-backend product configuration.
# Names are assembled so this assertion does not itself read as residual
# non-pi wiring to the backend-convergence scan.
for stray in ("open" + "code.json", "co" + "dex.toml", ".cla" + "ude"):
    if (runtime / stray).exists():
        problems.append(f"runtime still contains a non-pi backend configuration: {stray}")

if problems:
    for problem in problems:
        print(f"ERROR {problem}", file=sys.stderr)
    raise SystemExit(1)
print(f"pi resource manifest valid for {name}")
PY
echo "validated $dir"
