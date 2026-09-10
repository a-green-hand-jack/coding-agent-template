#!/usr/bin/env python3
"""Run deterministic pre-release checks for the coding-agent template."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path


SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]+ PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])-[A-Za-z0-9_-]{16,}\b"),
)
RETIRED_MARKERS = (
    "DEEPSEEKP_API_KEY",
    "src/" + "hello-" + "world",
    "opencode-" + "agent-template",
)
RELEASE_FORBIDDEN = (
    ".agents/",
    "AGENTS.md",
    "template-content-registry",
    "benchmarks/",  # Legacy/external benchmark payloads remain forbidden; cases are in .agents/.
    "DEV.md",
    "USER.md",
)


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return fnmatch.fnmatchcase(path, pattern)


class Audit:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)
        print(f"ERROR {message}", file=sys.stderr)

    def warning(self, message: str) -> None:
        self.warnings.append(message)
        print(f"WARN  {message}", file=sys.stderr)


def git_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode().strip() or "git ls-files failed")
    return [item for item in result.stdout.decode().split("\0") if item]


def read_registry(root: Path, audit: Audit) -> dict:
    path = root / ".agents/template-content-registry.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        audit.error(f"registry unreadable: {path}: {exc}")
        return {}


def check_registry(root: Path, tracked: list[str], registry: dict, audit: Audit) -> None:
    classes = registry.get("classes", {})
    inventory = registry.get("repository_inventory", {})
    patterns = inventory.get("patterns", [])
    if inventory.get("tracked_paths_must_be_registered") is not True:
        audit.error("registry does not require complete tracked-path coverage")
    if not patterns:
        audit.error("registry has no repository inventory patterns")
    for item in patterns:
        if item.get("class") not in classes or not item.get("path"):
            audit.error(f"invalid registry inventory pattern: {item!r}")
    for path in tracked:
        if not any(matches(path, item.get("path", "")) for item in patterns):
            audit.error(f"unregistered tracked path: {path}")

    entries = registry.get("entries", [])
    for entry in entries:
        entry_path = entry.get("path", "")
        if not entry_path or any(char in entry_path for char in "*?["):
            continue
        if not any(matches(path, entry_path) for path in tracked):
            audit.error(f"stale registry entry: {entry_path}")
        if entry.get("class") not in classes:
            audit.error(f"registry entry has unknown class: {entry_path}")

    for item in entries:
        if item.get("class") == "placeholder-only":
            source = root / item.get("path", "")
            destination = item.get("destination", "")
            if not source.is_file():
                audit.error(f"placeholder source missing: {item.get('path')}")
            if destination not in {
                ".agents/knowledge/PLACEHOLDER.md",
                ".agents/memory/PLACEHOLDER.md",
                ".agents/workflows/PLACEHOLDER.md",
            }:
                audit.error(f"placeholder has unsafe destination: {destination}")


def check_required_paths(root: Path, audit: Audit) -> None:
    required = (
        ".agents/template-content-registry.json",
        ".agents/downstream-skeleton/knowledge/PLACEHOLDER.md",
        ".agents/downstream-skeleton/memory/PLACEHOLDER.md",
        ".agents/downstream-skeleton/workflows/PLACEHOLDER.md",
        ".agents/skills/template-agent-development/SKILL.md",
        ".agents/skills/agent-consistency-audit/SKILL.md",
        ".agents/skills/agent-definition-validation/SKILL.md",
        ".agents/skills/agent-infrastructure-health/SKILL.md",
        "distribution/install.sh",
        "distribution/container-entrypoint.sh",
        "docker/run-hewo-e2e.sh",
        "scripts/setup-dev.sh",
        "docker/Dockerfile",
        "scripts/build-release.sh",
        ".agents/scripts/validate-definition.sh",
        "src/hewo/agent.yaml",
    )
    for relative in required:
        if not (root / relative).is_file():
            audit.error(f"required template path missing: {relative}")


def check_tracked_content(root: Path, tracked: list[str], audit: Audit) -> None:
    audit_code = {
        ".agents/skills/agent-consistency-audit/scripts/audit_agent.py",
        ".agents/skills/template-release-readiness/scripts/audit_template_release.py",
    }
    for relative in tracked:
        # These deterministic auditors contain marker strings as test rules;
        # scanning their source would report the rules themselves as leakage.
        if relative in audit_code:
            continue
        path = root / relative
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                audit.error(f"possible credential material in tracked file: {relative}")
                break
        for marker in RETIRED_MARKERS:
            if marker in content:
                audit.error(f"retired/template residue marker {marker!r} in: {relative}")
                break


def check_release(path: Path, audit: Audit) -> None:
    if not path.is_file():
        audit.error(f"release archive missing: {path}")
        return
    try:
        with tarfile.open(path, "r:gz") as archive:
            names = archive.getnames()
    except (OSError, tarfile.TarError) as exc:
        audit.error(f"release archive unreadable: {path}: {exc}")
        return
    for required in ("runtime-package/package.json", "install.sh", "release-manifest.json"):
        if not any(name.endswith("/" + required) for name in names):
            audit.error(f"required release payload missing: {required}")
    for name in names:
        parts = Path(name).parts
        if any(forbidden.rstrip("/") in parts for forbidden in RELEASE_FORBIDDEN):
            audit.error(f"template-only content in release archive: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", default="hewo", help="sample Agent to require (default: hewo)")
    parser.add_argument("--release", type=Path, help="optional release archive to inspect")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable summary")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    audit = Audit()
    try:
        tracked = git_files(root)
    except RuntimeError as exc:
        audit.error(str(exc))
        tracked = []
    registry = read_registry(root, audit)
    check_registry(root, tracked, registry, audit)
    check_required_paths(root, audit)
    check_tracked_content(root, tracked, audit)
    if args.release:
        check_release(args.release if args.release.is_absolute() else root / args.release, audit)

    summary = {"errors": audit.errors, "warnings": audit.warnings, "ok": not audit.errors}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Summary: {len(audit.errors)} error(s), {len(audit.warnings)} warning(s)")
    return 1 if audit.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
