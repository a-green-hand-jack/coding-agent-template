#!/usr/bin/env python3
"""Ensure every tracked template path is covered by the content registry."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return fnmatch.fnmatchcase(path, pattern)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.repo_root.resolve()
    registry_path = root / ".agents/template-content-registry.json"

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR registry unreadable: {registry_path}: {exc}", file=sys.stderr)
        return 2

    inventory = registry.get("repository_inventory", {})
    patterns = inventory.get("patterns", [])
    classes = set(registry.get("classes", {}))
    if inventory.get("tracked_paths_must_be_registered") is not True or not patterns:
        print("ERROR registry must declare tracked_paths_must_be_registered and patterns", file=sys.stderr)
        return 2
    invalid = [p for p in patterns if p.get("class") not in classes or not p.get("path")]
    if invalid:
        print(f"ERROR inventory has {len(invalid)} invalid pattern entries", file=sys.stderr)
        return 2

    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        print(f"ERROR git ls-files failed: {result.stderr.decode().strip()}", file=sys.stderr)
        return 2
    tracked = [item for item in result.stdout.decode().split("\0") if item]

    stale_entries = []
    for entry in registry.get("entries", []):
        entry_path = entry.get("path", "")
        if not entry_path or any(char in entry_path for char in "*?["):
            continue
        if not any(matches(path, entry_path) for path in tracked):
            stale_entries.append(entry_path)
    if stale_entries:
        print("ERROR registry entries do not match tracked paths:", file=sys.stderr)
        for path in stale_entries:
            print(f"  {path}", file=sys.stderr)
        return 1

    unmatched = [path for path in tracked if not any(matches(path, p["path"]) for p in patterns)]
    if unmatched:
        print("ERROR unregistered tracked paths:", file=sys.stderr)
        for path in unmatched:
            print(f"  {path}", file=sys.stderr)
        return 1

    print(f"Template registry covers {len(tracked)} tracked paths with {len(patterns)} inventory patterns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
