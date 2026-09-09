#!/usr/bin/env bash
# Freeze everything one evaluation run executes into an immutable snapshot.
#
# A long provider-backed run used to read the live worktree at three separate
# moments after the developer was told the run had started: the Docker build,
# the pass/fail verifier, and the loop scripts the child process re-executed.
# Editing the product definition during a run therefore changed what was tested
# and what the evidence claimed. This script moves every one of those reads to a
# single instant: submit time.
#
# The whole worktree is frozen, not just the Docker build context, because the
# preflight stages resolve their own paths (validate-definition.sh is CWD
# relative, audit_agent.py defaults --root to the current directory). Freezing
# only the build context would leave those stages reading live source while the
# benchmark ran frozen source, producing a summary that looks internally
# consistent and is not.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
agent="${AGENT_NAME:-hewo}"
into=""

usage() {
  cat <<'EOF'
Usage: ./scripts/freeze-agent-run.sh --into DIR [--agent NAME]

Copy the worktree into DIR and record the two digests that identify the run.
DIR must not already exist.

Options:
  --into DIR     Destination snapshot directory (required)
  --agent NAME   Agent name (default: hewo, or $AGENT_NAME)
  -h, --help     Show this help

Prints KEY=VALUE lines on stdout:
  AGENT_DEFINITION_REVISION  digest of what the product Agent does
  AGENT_CONTEXT_DIGEST       digest of the image inputs (the build cache key)
  AGENT_IMAGE                <agent>:def-<context digest prefix>
  AGENT_RUN_SNAPSHOT         the frozen directory
EOF
}

while (($#)); do
  case "$1" in
    --into) into="${2:?missing value for --into}"; shift 2 ;;
    --agent) agent="${2:?missing value for --agent}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$into" ]] || { usage >&2; exit 2; }
[[ "$agent" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]] || { printf 'invalid agent name: %s\n' "$agent" >&2; exit 2; }

python3 - "$root" "$agent" "$into" <<'PY'
"""Copy the worktree and digest it in one walk.

The copy and the digest MUST come from the same traversal. If they were two
passes with two exclude lists, two different trees could produce one digest and
the image cache would hand back a stale image for changed source.
"""

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

repo_root, agent, destination = sys.argv[1:]
root = Path(repo_root).resolve()
into = Path(destination)

# Generated, vendored, or secret-bearing. .env* is excluded for the same reason
# credentials are never baked into an image: a snapshot lives outside the
# repository and must never carry a key.
EXCLUDED_NAMES = {
    ".git",
    ".opencode",
    ".pi",
    "release",
    "artifacts",
    "traces",
    "node_modules",
    "__pycache__",
    "build",
}
EXCLUDED_SUFFIXES = (".egg-info", ".log")


def excluded(name: str) -> bool:
    if name in EXCLUDED_NAMES or name.endswith(EXCLUDED_SUFFIXES):
        return True
    return name == ".env" or name.startswith(".env.")


if into.exists():
    print(f"ERROR snapshot destination already exists: {into}", file=sys.stderr)
    raise SystemExit(2)
resolved_into = into.resolve().parent / into.name
if resolved_into == root or root in resolved_into.parents:
    print("ERROR snapshot destination must live outside the repository", file=sys.stderr)
    raise SystemExit(2)

# path -> descriptor. The descriptor carries the executable bit because a
# chmod -x changes no file content: without the mode a broken worktree would
# hit the image cache and a stale image would be reported as passing.
manifest: dict[str, str] = {}


def digest_file(path: Path) -> str:
    output = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            output.update(chunk)
    return output.hexdigest()


def walk(relative: Path) -> None:
    source = root / relative if relative != Path(".") else root
    target = into / relative if relative != Path(".") else into
    target.mkdir(parents=True, exist_ok=True)
    if relative != Path("."):
        manifest[relative.as_posix() + "/"] = "d"
    for entry in sorted(os.listdir(source)):
        if excluded(entry):
            continue
        child = source / entry
        child_relative = relative / entry if relative != Path(".") else Path(entry)
        key = child_relative.as_posix()
        if child.is_symlink():
            # Symlinks are content: CLAUDE.md -> AGENTS.md is how this
            # repository keeps one file under two names. Retargeting one must
            # change the digest, and a followed link would copy a duplicate.
            link = os.readlink(child)
            manifest[key] = "l:" + link
            os.symlink(link, into / child_relative)
        elif child.is_dir():
            walk(child_relative)
        elif child.is_file():
            manifest[key] = "f:%d:%s" % (1 if os.access(child, os.X_OK) else 0, digest_file(child))
            shutil.copy2(child, into / child_relative)
        # Sockets, fifos and devices are not source; skipping them keeps the
        # snapshot copyable and the digest total over real content.


walk(Path("."))


def subset_digest(prefixes: tuple[str, ...], extra: dict | None = None) -> str:
    selected = {
        key: value
        for key, value in manifest.items()
        if any(key == prefix or key.startswith(prefix) for prefix in prefixes)
    }
    if extra:
        selected["\0build-args"] = json.dumps(extra, sort_keys=True, ensure_ascii=True)
    canonical = json.dumps(selected, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# The subject axis: what the product Agent does. The launcher belongs here
# because it injects the identity through --append-system-prompt and closes the
# discovery boundary with --no-context-files/--no-skills/--no-prompt-templates.
# Editing it changes product behavior, so it must not read as a mere
# environment change.
definition_revision = subset_digest(
    (f"src/{agent}/", "distribution/launcher", "distribution/container-entrypoint.sh")
)

# The image cache key. scripts/ and benchmarks/ are frozen but deliberately
# absent here: editing a script must not force an image rebuild.
context_digest = subset_digest(
    ("src/", "distribution/", "docker/"),
    {
        "AGENT_NAME": agent,
        "PI_VERSION": os.environ.get("PI_VERSION", "latest"),
        "PI_PACKAGE": os.environ.get("PI_PACKAGE", "@earendil-works/pi-coding-agent"),
    },
)

image = f"{agent}:def-{context_digest[:12]}"
record = {
    "schema_version": 1,
    "agent": agent,
    "definition_revision": definition_revision,
    "context_digest": context_digest,
    "image": image,
    "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "entries": len(manifest),
}
# Written last: a consumer that finds this file knows the copy completed.
(into / ".frozen.json").write_text(
    json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
)

print(f"AGENT_DEFINITION_REVISION={definition_revision}")
print(f"AGENT_CONTEXT_DIGEST={context_digest}")
print(f"AGENT_IMAGE={image}")
print(f"AGENT_RUN_SNAPSHOT={into}")
PY
