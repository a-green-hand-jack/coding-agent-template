#!/usr/bin/env python3
"""Fail if a non-pi backend still appears in the product or acceptance contract.

The product Agent supports pi and only pi. This gate enumerates the touchpoints
that form the product, release and acceptance contract and refuses any residual
OpenCode / Codex / Claude Code wiring in them, so a multi-backend contract
cannot survive by accident.

Development-side files may still name other CLIs, because the development
machine really does have them and rewriting that history would be dishonest.
Those files are listed explicitly with a reason; the allowlist is the point of
review, not a wildcard.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

# Paths that form the product, release and acceptance contract.
PRODUCT_CONTRACT = (
    "distribution/**",
    "docker/**",
    "scripts/**",
    "src/**",
    ".env.example",
    ".dockerignore",
    ".github/workflows/**",
    "README.md",
    "USER.md",
    "package.json",
)

# Non-pi backend wiring. Matching any of these inside the product contract is a
# failure; matching them anywhere outside the development allowlist is also a
# failure, so new files cannot quietly reintroduce a second backend.
FORBIDDEN = (
    (r"opencode-ai@", "OpenCode npm package"),
    (r"@openai/codex", "Codex npm package"),
    (r"@anthropic-ai/claude-code", "Claude Code npm package"),
    (r"@mariozechner/pi-coding-agent", "stale pi package name"),
    (r"OPENCODE_CONFIG|OPENCODE_CONFIG_DIR|OPENCODE_AUTH_FILE|AGENT_AUTH_STORE", "OpenCode env wiring"),
    (r"CODEX_HOME|CODEX_AUTH_STORE|CODEX_SANDBOX_MODE|CODEX_MODEL", "Codex env wiring"),
    (r"CLAUDE_CONFIG_DIR|CLAUDE_AUTH_STORE|CLAUDE_MODEL|ANTHROPIC_AUTH_TOKEN", "Claude Code env wiring"),
    (r"--codex-auth-file|--claude-api-key-file|--claude-credentials-file", "non-pi credential flags"),
    (r"\bopencode\.json\b", "OpenCode product configuration"),
    (r"\bopencode\s+run\b|\bopencode\s+models\b|\bclaude\s+-p\b|\bcodex\s+exec\b", "non-pi CLI invocation"),
    (r"--backend\s+(opencode|codex|claude)", "non-pi backend selection"),
    # Hyphen-guarded so a legitimate pi PROVIDER id such as "openai-codex" is
    # not mistaken for a retired backend.
    (r"(?<![\w-])(opencode|codex|claude|claude-code)(?![\w-])", "non-pi backend name"),
)

# Development-side files that may still name other CLIs, each with its reason.
DEVELOPMENT_ALLOWLIST = {
    "AGENTS.md": "names the coding agents this repository may be developed WITH, not product backends",
    "DEV.md": "developer guide; records the development harness and the pi-only product contract",
    "DevelopmentMachine.md": "generated profile of what is actually installed on this machine",
    ".agents/knowledge/development-machine-facts.md": "operator-confirmed facts about installed CLIs",
    ".agents/knowledge/provider-e2e.md": "secret-free credential cheat-sheet for this machine's CLIs",
    ".agents/knowledge/pi-runtime-component-contract.md": "states which capabilities pi lacks and names alternatives",
    ".agents/memory/2026-09-06-issue1-hewo-evidence.md": "historical evidence; must not be rewritten",
    ".agents/skills/development-machine-profile/SKILL.md": "machine-agnostic prober",
    ".agents/skills/development-machine-profile/references/profile-schema.md": "machine-agnostic prober schema",
    ".agents/skills/development-machine-profile/scripts/probe-host.sh": "probes whichever CLIs exist",
    ".agents/skills/agent-consistency-audit/scripts/audit_agent.py": "audit rules name retired markers deliberately",
    ".agents/skills/template-release-readiness/scripts/audit_template_release.py": "audit rules name retired markers deliberately",
    ".agents/skills/agent-definition-validation/SKILL.md": "records the pi-only validation contract",
    ".agents/skills/agent-infrastructure-health/SKILL.md": "records the pi-only infrastructure contract",
    ".agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py": "checks the pi runtime only",
    ".agents/skills/template-agent-development/SKILL.md": "downstream guidance; records the pi-only contract",
    ".agents/skills/template-agent-development/references/use-template.md": "downstream guidance",
    ".agents/skills/template-agent-development/references/sync-template.md": "downstream guidance",
    ".agents/skills/template-agent-development/references/migrate-existing-agent.md": "migration guidance from older layouts",
    ".agents/template-content-registry.json": "registry notes describe historical classes",
    ".opencode/opencode.jsonc": "configuration for the development harness, not the product",
    "scripts/check-pi-only-backend.py": "this gate names the patterns it forbids",
}

# Positive facts the pi-only contract must keep.
REQUIRED_FACTS = (
    ("distribution/launcher", r"--append-system-prompt", "launcher must inject identity through pi"),
    ("distribution/launcher", r"--skill", "launcher must load skills through pi's own loader"),
    ("distribution/launcher", r"--extension", "launcher must load the extension through pi's own loader"),
    ("distribution/launcher", r"--no-context-files", "launcher must stop pi discovering AGENTS.md into the product"),
    ("distribution/launcher", r"--no-skills", "launcher must disable ambient skill discovery"),
    ("distribution/launcher", r"supports pi only", "launcher must refuse other backends explicitly"),
    ("scripts/validate-definition.sh", r"runtime/package\.json", "validation must require the pi resource manifest"),
    ("docker/Dockerfile", r"pi-coding-agent", "the image must install pi"),
)

FORBIDDEN_RUNTIME_FILES = (
    "src/*/runtime/opencode.json",
    "src/*/runtime/codex.toml",
)


def tracked(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], check=True, stdout=subprocess.PIPE
    )
    return [item for item in result.stdout.decode().split("\0") if item]


def in_product_contract(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) or path.startswith(pattern.rstrip("*"))
               for pattern in PRODUCT_CONTRACT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--list-allowlist", action="store_true", help="print the development allowlist and exit")
    args = parser.parse_args()
    root = args.repo_root.resolve()

    if args.list_allowlist:
        for path, reason in sorted(DEVELOPMENT_ALLOWLIST.items()):
            print(f"{path}\n    {reason}")
        return 0

    errors: list[str] = []
    checked = 0
    patterns = [(re.compile(pattern, re.IGNORECASE), label) for pattern, label in FORBIDDEN]

    for relative in tracked(root):
        # Plan files are historical development records; rewriting them to
        # satisfy a later gate would falsify the record.
        if relative == "PLAN.md" or relative.startswith("PLAN-") or relative in DEVELOPMENT_ALLOWLIST:
            continue
        path = root / relative
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        checked += 1
        for compiled, label in patterns:
            match = compiled.search(content)
            if match:
                line = content[: match.start()].count("\n") + 1
                scope = "product contract" if in_product_contract(relative) else "repository"
                errors.append(f"{relative}:{line}: {label} in the {scope}: {match.group(0)!r}")
                break

    for pattern in FORBIDDEN_RUNTIME_FILES:
        for found in root.glob(pattern):
            errors.append(f"{found.relative_to(root)}: non-pi backend configuration must not exist")

    for relative, pattern, reason in REQUIRED_FACTS:
        path = root / relative
        if not path.is_file():
            errors.append(f"{relative}: required file is missing")
            continue
        if not re.search(pattern, path.read_text(encoding="utf-8")):
            errors.append(f"{relative}: {reason} (missing {pattern!r})")

    if errors:
        print(f"ERROR pi-only backend scan found {len(errors)} problem(s):", file=sys.stderr)
        for item in errors:
            print(f"  {item}", file=sys.stderr)
        return 1
    print(
        f"pi-only backend scan clean: {checked} tracked file(s) scanned, "
        f"{len(DEVELOPMENT_ALLOWLIST)} development-side exemption(s), "
        f"{len(REQUIRED_FACTS)} positive fact(s) confirmed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
