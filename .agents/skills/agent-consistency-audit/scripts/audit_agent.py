#!/usr/bin/env python3
"""Deterministic preflight audit for a coding-agent repository.

The audit deliberately reports likely problems instead of trying to infer
whether prose is semantically correct. A coding agent must review WARNings and
run the provider-backed Docker E2E separately.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tarfile
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "release",
    "artifacts",
    "traces",
    "work",
    "__pycache__",
}
TEXT_SUFFIXES = {
    ".json",
    ".jsonc",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".js",
    ".yaml",
    ".yml",
}
SECRET_FILE_RE = re.compile(
    r"(?:^\.env(?:\..*)?$|auth\.json$|(?:credential|secret|token|private[-_]?key))",
    re.IGNORECASE,
)
SECRET_CONTENT_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"\b(?:OPENAI|ANTHROPIC|GOOGLE|AWS|AZURE|OPENCODE)[A-Z0-9_]*_(?:API_)?KEY\s*=\s*['\"]?[A-Za-z0-9+/=_-]{16,}"
    ),
    re.compile(
        r"\b[A-Z][A-Z0-9_]*(?:API_KEY|AUTH_TOKEN)\s*=\s*['\"]?[A-Za-z0-9+/=_-]{16,}"
    ),
)
STALE_MARKERS = {
    "example-agent": "obsolete example scaffold name",
    "hello-world": "removed example scaffold name",
    "tests/install/test-install.sh": "removed install-test workflow",
    "opencode-agent-template": "renamed repository identifier",
}
# Files that record what was observed rather than instructing anyone. A retired
# name inside them is evidence, not drift, so rewriting it to satisfy a later
# gate would falsify the record. Treated like `.agents/memory/`.
RECORDED_EVIDENCE_FILES = {
    "DevelopmentMachine.md": "generated profile of what this machine actually had",
    ".agents/knowledge/development-machine-facts.md": "operator-confirmed smoke evidence",
}
PLACEHOLDER_RE = re.compile(r"(?:<[^>]+>|\$\{[^}]+\}|\$[A-Z_][A-Z0-9_]*)")
SRC_REF_RE = re.compile(r"(?<![A-Za-z0-9_])src/([A-Za-z0-9._-]+)(?:/|\b)")
MD_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")


@dataclass
class Finding:
    level: str
    code: str
    path: str
    line: int | None
    message: str


class Audit:
    def __init__(self, root: Path, selected_agent: str | None, strict: bool, release: Path | None) -> None:
        self.root = root
        self.selected_agent = selected_agent
        self.strict = strict
        self.release = release
        self.findings: list[Finding] = []
        self.agents: list[str] = []

    def add(
        self,
        level: str,
        code: str,
        path: Path | str,
        message: str,
        line: int | None = None,
    ) -> None:
        display = str(path)
        if isinstance(path, Path):
            try:
                display = str(path.relative_to(self.root))
            except ValueError:
                display = str(path)
        self.findings.append(Finding(level, code, display, line, message))

    def discover_agents(self) -> None:
        src = self.root / "src"
        if not src.is_dir():
            self.add("ERROR", "missing-src", src, "missing src/ directory")
            return
        for child in sorted(src.iterdir()):
            if child.is_dir() and (child / "agent.yaml").is_file():
                self.agents.append(child.name)
        if self.selected_agent:
            if self.selected_agent not in self.agents:
                self.add(
                    "ERROR",
                    "unknown-agent",
                    src / self.selected_agent,
                    "selected Agent has no src/<agent>/agent.yaml",
                )
            self.agents = [self.selected_agent]
        elif not self.agents:
            self.add("ERROR", "no-agent", src, "no Agent definitions discovered")

    @staticmethod
    def parse_simple_yaml(path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", raw)
            if match and match.group(2) and not match.group(2).startswith("#"):
                values[match.group(1)] = match.group(2).strip("'\"")
        return values

    def check_definition(self, name: str) -> None:
        agent_dir = self.root / "src" / name
        manifest = agent_dir / "agent.yaml"
        if not manifest.is_file():
            self.add("ERROR", "missing-manifest", manifest, "missing agent.yaml")
            return
        values = self.parse_simple_yaml(manifest)
        if values.get("name") != name:
            self.add(
                "ERROR",
                "manifest-name",
                manifest,
                f"name is {values.get('name')!r}, expected {name!r}",
            )
        runtime_rel = values.get("runtime_dir", "runtime")
        runtime = agent_dir / runtime_rel
        if not runtime.is_dir():
            self.add("ERROR", "missing-runtime", runtime, "runtime_dir does not exist")
            return
        development_rel = values.get("development_dir", "development")
        development = agent_dir / development_rel
        if not development.exists():
            self.add(
                "INFO",
                "optional-development-dir",
                development,
                "development_dir is declared but not present; this is allowed for a minimal Agent",
            )

        required_files = {
            "identity.md": runtime / "identity.md",
            "memory-policy.md": runtime / "memory-policy.md",
            "package.json": runtime / "package.json",
        }
        for label, path in required_files.items():
            if not path.is_file():
                self.add("ERROR", "missing-runtime-file", path, f"missing runtime {label}")
        for label, path in {
            "knowledge_dir": agent_dir / values.get("knowledge_dir", f"{runtime_rel}/knowledge"),
            "skills_dir": agent_dir / values.get("skills_dir", f"{runtime_rel}/skills"),
            "workflows_dir": agent_dir / values.get("workflows_dir", f"{runtime_rel}/workflows"),
        }.items():
            if not path.is_dir():
                self.add("ERROR", "missing-runtime-dir", path, f"missing {label}")

        config_path = runtime / "package.json"
        if config_path.is_file():
            self.check_runtime_manifest(name, runtime, config_path)
        skills_dir = runtime / "skills"
        if skills_dir.is_dir() and not list(skills_dir.rglob("SKILL.md")):
            self.add("ERROR", "no-runtime-skill", skills_dir, "runtime has no SKILL.md")
        self.check_runtime_boundary(name, runtime)

    def check_runtime_manifest(self, name: str, runtime: Path, path: Path) -> None:
        """Audit the pi resource manifest.

        `scripts/validate-definition.sh` owns the exhaustive structural
        contract. This audit covers the drift a repository accumulates over
        time: a manifest that stopped being pi-only, resource paths that no
        longer resolve, and a declared tool surface that went empty.
        """
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.add("ERROR", "invalid-runtime-manifest", path, f"cannot parse JSON: {exc}")
            return
        if manifest.get("scripts"):
            self.add(
                "ERROR",
                "runtime-manifest-scripts",
                path,
                "runtime package.json must not declare npm lifecycle scripts",
            )
        if "pi-package" not in (manifest.get("keywords") or []):
            self.add("WARN", "pi-package-keyword", path, 'manifest lacks the "pi-package" keyword')

        pi = manifest.get("pi")
        if not isinstance(pi, dict):
            self.add("ERROR", "missing-pi-section", path, "manifest has no pi section")
            pi = {}
        elif "./skills" not in (pi.get("skills") or []):
            self.add("ERROR", "skills-path", path, "pi.skills does not include ./skills")

        section = manifest.get("agent")
        if not isinstance(section, dict):
            legacy = sorted(
                key
                for key, value in manifest.items()
                if key != "agent" and isinstance(value, dict) and "manifest_version" in value
            )
            hint = f": rename the legacy {legacy[0]!r} section to 'agent'" if legacy else ""
            self.add("ERROR", "missing-agent-section", path, f"manifest has no agent section{hint}")
            return
        if section.get("manifest_version") != 1:
            self.add(
                "ERROR",
                "manifest-version",
                path,
                f"agent.manifest_version is {section.get('manifest_version')!r}, expected 1",
            )
        if section.get("backend") != "pi":
            self.add(
                "ERROR",
                "backend-drift",
                path,
                f"agent.backend is {section.get('backend')!r}, expected 'pi'",
            )
        if section.get("network") not in {"deny", "allow"}:
            self.add(
                "ERROR",
                "network-policy",
                path,
                f"agent.network is {section.get('network')!r}, expected 'deny' or 'allow'",
            )
        tools = section.get("default_tools")
        if not isinstance(tools, list) or not tools:
            self.add("ERROR", "empty-tool-surface", path, "agent.default_tools is missing or empty")

        # Every declared resource must still resolve inside the runtime, so a
        # renamed or deleted file fails the audit instead of the user's first run.
        declared = [
            (f"pi.{key}", entry)
            for key in ("skills", "prompts", "themes", "extensions")
            for entry in (pi.get(key) or [])
        ] + [
            (f"agent.{key}", entry)
            for key in ("system_prompt", "context", "agent_definitions", "leaf_tools")
            for entry in (section.get(key) or [])
        ]
        for label, entry in declared:
            if not isinstance(entry, str) or not entry.strip():
                self.add("ERROR", "invalid-resource-path", path, f"{label} has a non-string path")
                continue
            if entry.startswith("/") or ".." in entry.split("/"):
                self.add(
                    "ERROR",
                    "unsafe-resource-path",
                    path,
                    f"{label} must be a relative path inside the runtime: {entry}",
                )
                continue
            if not (runtime / entry).exists():
                self.add(
                    "ERROR",
                    "broken-resource-path",
                    path,
                    f"{label} declares a path that does not exist: {entry}",
                )

    def check_runtime_boundary(self, name: str, runtime: Path) -> None:
        for path in runtime.rglob("*"):
            if path.is_dir():
                continue
            if path.name in {"AGENTS.md", "CLAUDE.md"}:
                self.add(
                    "INFO",
                    "development-in-runtime-source",
                    path,
                    "development AGENTS.md is present in source; verify packaging excludes it",
                )
            if SECRET_FILE_RE.search(path.name):
                self.add("ERROR", "credential-file-in-runtime", path, "credential-like file is inside runtime")
            if path.suffix == ".json":
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    self.add("ERROR", "invalid-runtime-json", path, f"cannot parse JSON: {exc}")
            if path.name == "pyproject.toml":
                try:
                    data = tomllib.loads(path.read_text(encoding="utf-8"))
                except (OSError, tomllib.TOMLDecodeError) as exc:
                    self.add("ERROR", "invalid-tool-project", path, f"cannot parse TOML: {exc}")
                else:
                    if not isinstance(data.get("project"), dict) or not data["project"].get("name"):
                        self.add("ERROR", "tool-project-name", path, "tool pyproject lacks [project].name")

    def check_development_skills(self) -> None:
        skills_root = self.root / ".agents" / "skills"
        if not skills_root.is_dir():
            self.add("INFO", "no-development-skills", skills_root, "no .agents/skills directory")
            return
        for path in skills_root.rglob("SKILL.md"):
            if path == SKILL_DIR / "SKILL.md":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if not text.startswith("---\n"):
                self.add("WARN", "skill-frontmatter", path, "development SKILL.md lacks YAML frontmatter")
                continue
            header = text.split("---\n", 2)
            frontmatter = header[1] if len(header) > 1 else ""
            if not re.search(r"^name:\s*\S+", frontmatter, re.MULTILINE):
                self.add("ERROR", "skill-name", path, "frontmatter lacks name")
            if not re.search(r"^description:\s*\S+", frontmatter, re.MULTILINE):
                self.add("ERROR", "skill-description", path, "frontmatter lacks description")

    def iter_text_files(self) -> Iterable[Path]:
        for current, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDED_DIRS]
            current_path = Path(current)
            for filename in files:
                path = current_path / filename
                if path == SKILL_DIR or SKILL_DIR in path.parents:
                    continue
                if SECRET_FILE_RE.search(filename):
                    if filename == ".env.example":
                        yield path
                        continue
                    self.add("INFO", "skipped-credential-file", path, "credential-like file was not read")
                    continue
                if path.is_symlink():
                    # A symlink carries no content of its own; the target is
                    # walked under its own path.
                    continue
                if path.suffix.lower() in TEXT_SUFFIXES:
                    yield path

    def check_text_integrity(self) -> None:
        active_agents = set(self.agents)
        for path in self.iter_text_files():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                self.add("WARN", "unreadable-file", path, str(exc))
                continue
            for index, line in enumerate(text.splitlines(), 1):
                for pattern in SECRET_CONTENT_PATTERNS:
                    if pattern.search(line) and not line.lstrip().startswith(("#", "-")):
                        self.add("ERROR", "possible-secret", path, "possible credential material; inspect without printing it", index)
                        break
                for marker, explanation in STALE_MARKERS.items():
                    if marker not in line:
                        continue
                    relative = path.relative_to(self.root)
                    if "memory" in relative.parts or relative.as_posix() in RECORDED_EVIDENCE_FILES:
                        self.add("INFO", "historical-marker", path, f"historical/template-only reference: {explanation}", index)
                    elif marker == "tests/install/test-install.sh" and re.search(r"obsolete|removed|deprecated|do not restore", line, re.IGNORECASE):
                        self.add("INFO", "documented-obsolete-marker", path, explanation, index)
                    elif "template-agent-development" in relative.parts and marker in {"example-agent", "hello-world"}:
                        self.add("INFO", "template-example-marker", path, explanation, index)
                    else:
                        self.add("WARN", "stale-marker", path, explanation, index)
                for match in SRC_REF_RE.finditer(line):
                    referenced = match.group(1)
                    if referenced in active_agents or referenced in {"<agent>", "<agent_name>", "agent_name", "my-agent"}:
                        continue
                    if PLACEHOLDER_RE.search(referenced):
                        continue
                    if referenced in {"hewo", "src"} and "template-agent-development" in path.parts:
                        continue
                    self.add("WARN", "stale-src-reference", path, f"src/{referenced} is not a discovered Agent", index)
            if path.suffix.lower() == ".md":
                self.check_markdown_links(path, text)

    def check_markdown_links(self, path: Path, text: str) -> None:
        for match in MD_LINK_RE.finditer(text):
            target = match.group(1).strip().split()[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#", "$", "<")):
                continue
            if PLACEHOLDER_RE.search(target):
                continue
            target_path = (path.parent / target.split("#", 1)[0]).resolve()
            if not target_path.exists():
                self.add("WARN", "broken-markdown-link", path, f"linked path does not exist: {target}")

    def check_scripts(self) -> None:
        for path in self.iter_text_files():
            if path.suffix == ".sh":
                result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                if result.returncode:
                    self.add("ERROR", "shell-syntax", path, result.stderr.strip() or "bash -n failed")
            elif path.suffix == ".py" and path != Path(__file__):
                try:
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                except (OSError, SyntaxError) as exc:
                    self.add("ERROR", "python-syntax", path, str(exc))

    def check_cross_file_defaults(self) -> None:
        install = self.root / "distribution" / "install.sh"
        if install.is_file():
            text = install.read_text(encoding="utf-8", errors="replace")
            match = re.search(r'AGENT_NAME="\$\{AGENT_NAME:-([^}]+)\}"', text)
            if match and match.group(1) not in self.agents:
                self.add("ERROR", "installer-default-agent", install, f"default Agent {match.group(1)!r} is not defined")
            backend_match = re.search(r'AGENT_BACKENDS="\$\{AGENT_BACKENDS:-([^}]+)\}"', text)
            if backend_match:
                for backend in backend_match.group(1).split(","):
                    if backend not in {"pi", "pi-coding-agent"}:
                        self.add("ERROR", "installer-backend", install, f"unsupported default backend {backend!r}")
        dockerfile = self.root / "docker" / "Dockerfile"
        if dockerfile.is_file():
            match = re.search(r"^ARG AGENT_NAME=([^\s]+)", dockerfile.read_text(encoding="utf-8"), re.MULTILINE)
            if match and match.group(1) not in self.agents:
                self.add("ERROR", "docker-default-agent", dockerfile, f"default Agent {match.group(1)!r} is not defined")
        package = self.root / "package.json"
        if package.is_file():
            try:
                data = json.loads(package.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self.add("ERROR", "invalid-package-json", package, f"cannot parse JSON: {exc}")
            else:
                validate = data.get("scripts", {}).get("validate", "")
                match = re.search(r"validate-definition\.sh\s+(\S+)", validate)
                if match and match.group(1) not in self.agents:
                    self.add("ERROR", "package-default-agent", package, f"validate script targets unknown Agent {match.group(1)!r}")

    def check_release(self) -> None:
        if not self.release:
            return
        archive = self.release if self.release.is_absolute() else self.root / self.release
        if not archive.is_file():
            self.add("ERROR", "missing-release", archive, "release archive does not exist")
            return
        try:
            with tarfile.open(archive, "r:gz") as handle:
                names = handle.getnames()
        except (OSError, tarfile.TarError) as exc:
            self.add("ERROR", "invalid-release", archive, f"cannot read release archive: {exc}")
            return
        if not any(path.rstrip("/").endswith("/agent-definition") for path in names):
            self.add("ERROR", "release-definition", archive, "release has no agent-definition directory")
        for required in ("launcher", "install.sh"):
            if not any(path.endswith(f"/{required}") or path == required for path in names):
                self.add("ERROR", "release-file", archive, f"release is missing {required}")
        for name in names:
            parts = Path(name).parts
            if {"AGENTS.md", "CLAUDE.md"} & set(parts) or ".agents" in parts or "development" in parts:
                self.add("ERROR", "development-in-release", archive, f"development-only path is present: {name}")
            if parts and SECRET_FILE_RE.search(parts[-1]):
                self.add("ERROR", "credential-in-release", archive, f"credential-like path is present: {name}")

    def run(self) -> int:
        self.discover_agents()
        for name in self.agents:
            self.check_definition(name)
        self.check_development_skills()
        self.check_text_integrity()
        self.check_scripts()
        self.check_cross_file_defaults()
        self.check_release()
        return self.exit_code()

    def exit_code(self) -> int:
        if any(item.level == "ERROR" for item in self.findings):
            return 1
        if self.strict and any(item.level == "WARN" for item in self.findings):
            return 1
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    parser.add_argument("--agent", help="audit one Agent instead of all discovered definitions")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON findings")
    parser.add_argument("--release", type=Path, help="inspect a release tar.gz payload as well")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    audit = Audit(root, args.agent, args.strict, args.release)
    code = audit.run()
    if args.as_json:
        print(json.dumps({"root": str(root), "agents": audit.agents, "findings": [asdict(item) for item in audit.findings], "exit_code": code}, ensure_ascii=False, indent=2))
    else:
        for item in audit.findings:
            location = item.path
            if item.line is not None:
                location += f":{item.line}"
            print(f"{item.level:<5} {item.code:<28} {location} - {item.message}")
        counts = {level: sum(item.level == level for item in audit.findings) for level in ("ERROR", "WARN", "INFO")}
        print(f"Summary: {counts['ERROR']} error(s), {counts['WARN']} warning(s), {counts['INFO']} info")
        if code:
            print("Audit failed; review findings before claiming the Agent is current.", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
