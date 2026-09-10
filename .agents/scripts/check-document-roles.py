#!/usr/bin/env python3
"""Fail when a governed document does not declare who it is for.

A repository serving end users, human developers and coding agents at once
accumulates documents whose tone and scope drift, because nobody wrote down
who each one is for. Every governed document therefore declares its role
separately from its content, and this gate enforces that the declaration
exists and is well formed. It never judges the content itself.

`.agents/knowledge/document-roles.md` is the normative definition; this script
is its executable form. Keep the two in step.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

# Documents that must carry the full six-field block.
GOVERNED_FULL = (
    "README.md",
    "DEV.md",
    "USER.md",
    "AGENTS.md",
    ".agents/development/hewo/cases/README.md",
    ".agents/README.md",
    ".agents/*/README.md",
    ".agents/knowledge/*.md",
    ".agents/workflows/*.md",
    ".agents/skills/*/SKILL.md",
    ".agents/skills/*/references/*.md",
)

# Exempt by design. The runtime payload is exempt because its files are loaded
# into the product Agent's prompt and documentation metadata must never enter a
# shipped prompt; records are exempt because a role block would edit history.
EXEMPT = (
    "src/*/runtime/**",
    ".agents/memory/*.md",
    "PLAN.md",
    "PLAN-*.md",
    ".agents/local/DevelopmentMachine.md",
    ".agents/downstream-skeleton/**",
    ".agents/skills/*/fixtures/**",
)
# Note: a scoped AGENTS.md inside the runtime is NOT exempt. It is stripped
# from every payload, so it takes the short form; classify() handles that by
# basename before the exemptions are consulted.

FIELDS = ("Audience", "Authority", "Tone", "Language", "Contains", "Excludes")
AUDIENCE_TERMS = ("end user", "human developer", "development coding agent", "product agent")
AUTHORITY_TERMS = ("normative", "informative", "record")

HEADER_RE = re.compile(r"^>\s*\*\*Role of this document\*\*\s*$")
FIELD_RE = re.compile(r"^>\s*-\s*\*\*(?P<field>[A-Za-z]+):\*\*\s*(?P<value>.+?)\s*$")
SHORT_RE = re.compile(r"^>\s*\*\*Role:\*\*\s*(?P<value>.+?)\s*$")


def tracked(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], check=True, stdout=subprocess.PIPE
    )
    return [item for item in result.stdout.decode().split("\0") if item]


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatchcase(path, pattern):
            return True
        if pattern.endswith("/**") and path.startswith(pattern[:-2]):
            return True
    return False


def classify(path: str) -> str:
    """Return 'full', 'short' or 'exempt' for one repository-relative path."""
    if not path.endswith(".md"):
        return "exempt"
    # A scoped AGENTS.md always takes the short form, wherever it sits. Only the
    # root one carries the full block, because it is the primary document the
    # development coding agent reads.
    if path.endswith("AGENTS.md") and path != "AGENTS.md":
        return "short"
    if matches(path, EXEMPT):
        return "exempt"
    if matches(path, GOVERNED_FULL):
        return "full"
    return "exempt"


def check_full(path: str, lines: list[str]) -> list[str]:
    problems: list[str] = []
    header_index = next((i for i, line in enumerate(lines[:20]) if HEADER_RE.match(line)), None)
    if header_index is None:
        return [
            f"{path}: missing the role block. Add '> **Role of this document**' after the H1 "
            "(see .agents/knowledge/document-roles.md)"
        ]
    # A SKILL.md opens with YAML frontmatter, which sits above the H1 and is
    # metadata rather than content. Skip it before deciding what precedes the
    # block; the block still has to follow the H1 directly.
    start = 0
    if lines and lines[0].strip() == "---":
        closing = next(
            (i for i, line in enumerate(lines[1:header_index], 1) if line.strip() == "---"), None
        )
        if closing is not None:
            start = closing + 1
    # The block must open the document, not sit below content.
    before = [line for line in lines[start:header_index] if line.strip()]
    if len(before) != 1 or not before[0].startswith("# "):
        problems.append(f"{path}:{header_index + 1}: the role block must directly follow the H1 title")

    found: dict[str, str] = {}
    order: list[str] = []
    for line in lines[header_index + 1 :]:
        if not line.startswith(">"):
            break
        match = FIELD_RE.match(line)
        if match:
            found[match.group("field")] = match.group("value")
            order.append(match.group("field"))

    for field in FIELDS:
        if field not in found:
            problems.append(f"{path}: role block is missing the **{field}:** field")
    if not problems and order[: len(FIELDS)] != list(FIELDS):
        problems.append(f"{path}: role block fields must be in the order {', '.join(FIELDS)}")

    audience = found.get("Audience", "")
    if audience and not any(term in audience.lower() for term in AUDIENCE_TERMS):
        problems.append(
            f"{path}: Audience must lead with one of {AUDIENCE_TERMS}, got {audience!r}"
        )
    authority = found.get("Authority", "")
    if authority and not any(term in authority.lower() for term in AUTHORITY_TERMS):
        problems.append(
            f"{path}: Authority must be one of {AUTHORITY_TERMS}, got {authority!r}"
        )
    excludes = found.get("Excludes", "")
    if excludes and "`" not in excludes:
        problems.append(
            f"{path}: Excludes must route at least one excluded category to a destination "
            "written as a `path`"
        )
    return problems


def check_short(path: str, lines: list[str]) -> list[str]:
    if any(SHORT_RE.match(line) for line in lines[:12]):
        return []
    return [
        f"{path}: missing the one-line role declaration. Add '> **Role:** ...' after the H1 "
        "(see .agents/knowledge/document-roles.md)"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--list", action="store_true", help="print the classification and exit")
    args = parser.parse_args()
    root = args.repo_root.resolve()

    problems: list[str] = []
    counts = {"full": 0, "short": 0, "exempt": 0}
    for relative in tracked(root):
        kind = classify(relative)
        counts[kind] += 1
        if args.list and kind != "exempt":
            print(f"{kind:6} {relative}")
        if kind == "exempt":
            continue
        path = root / relative
        # A symlink carries no content of its own; its target is checked under
        # its own path.
        if path.is_symlink() or not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        problems.extend(check_full(relative, lines) if kind == "full" else check_short(relative, lines))

    if args.list:
        return 0
    if problems:
        print(f"ERROR document role scan found {len(problems)} problem(s):", file=sys.stderr)
        for item in problems:
            print(f"  {item}", file=sys.stderr)
        return 1
    print(
        f"document roles declared: {counts['full']} full block(s), "
        f"{counts['short']} scoped role line(s), {counts['exempt']} exempt path(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
