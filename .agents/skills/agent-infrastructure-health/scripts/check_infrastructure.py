#!/usr/bin/env python3
"""Check the installable coding-agent infrastructure without provider secrets."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path


NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_FILES = (
    "distribution/install.sh",
    "distribution/launcher",
    "distribution/container-entrypoint.sh",
    "docker/Dockerfile",
    "scripts/validate-definition.sh",
)
SHELL_DIRS = ("distribution", "docker", "scripts")
TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass
class Result:
    level: str
    check: str
    message: str


class Health:
    def __init__(self, root: Path, agent: str, image: str, release_archive: Path | None, skip_build: bool) -> None:
        self.root = root
        self.agent = agent
        self.image = image
        self.release_archive = release_archive
        self.skip_build = skip_build
        self.results: list[Result] = []

    def add(self, level: str, check: str, message: str) -> None:
        self.results.append(Result(level, check, message))

    def run_command(self, check: str, command: list[str], cwd: Path | None = None) -> bool:
        result = subprocess.run(command, cwd=cwd or self.root, capture_output=True, text=True)
        if result.returncode:
            detail = (result.stderr or result.stdout).strip().splitlines()
            self.add("ERROR", check, detail[-1] if detail else f"command failed: {' '.join(command)}")
            return False
        self.add("PASS", check, "ok")
        return True

    def required_files(self) -> None:
        for relative in REQUIRED_FILES:
            path = self.root / relative
            if path.is_file():
                self.add("PASS", "required-file", relative)
            else:
                self.add("ERROR", "required-file", f"missing {relative}")
        e2e_helpers = sorted((self.root / "docker").glob("run-*-e2e.sh"))
        if e2e_helpers:
            self.add("PASS", "e2e-helper", ", ".join(path.name for path in e2e_helpers))
        else:
            self.add("ERROR", "e2e-helper", "no docker/run-*-e2e.sh helper found")
        agent_dir = self.root / "src" / self.agent
        if not NAME_RE.fullmatch(self.agent):
            self.add("ERROR", "agent-name", f"invalid Agent name: {self.agent}")
        elif not (agent_dir / "agent.yaml").is_file():
            self.add("ERROR", "agent-definition", f"missing {agent_dir / 'agent.yaml'}")

    def syntax(self) -> None:
        for directory in SHELL_DIRS:
            base = self.root / directory
            for path in sorted(base.rglob("*.sh")) if base.is_dir() else []:
                self.run_command("shell-syntax", ["bash", "-n", str(path)])
        for path in sorted((self.root / "scripts").rglob("*.py")) if (self.root / "scripts").is_dir() else []:
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, SyntaxError) as exc:
                self.add("ERROR", "python-syntax", f"{path}: {exc}")
            else:
                self.add("PASS", "python-syntax", str(path.relative_to(self.root)))

    def definition(self) -> None:
        self.run_command("definition-validation", ["./scripts/validate-definition.sh", self.agent])
        tools_project = self.root / "src" / self.agent / "runtime" / "tools" / "pyproject.toml"
        if tools_project.is_file():
            if shutil.which("uv"):
                self.add("PASS", "uv-prerequisite", "uv is available for declared runtime tools")
            else:
                self.add("ERROR", "uv-prerequisite", "runtime/tools/pyproject.toml exists but uv is not installed")

    def docker(self) -> None:
        if self.skip_build:
            self.add("INFO", "docker-build", f"reusing {self.image}")
        else:
            self.run_command(
                "docker-build",
                ["docker", "build", "--build-arg", f"AGENT_NAME={self.agent}", "-t", self.image, "-f", "docker/Dockerfile", "."],
            )
        commands = [
            "set -eu",
            # The product supports pi and only pi; the image must contain it
            # and must not contain a retired backend.
            "command -v pi",
            f"test -f /opt/install/lib/{self.agent}/agent-definition/package.json",
        ]
        tools = self.runtime_tool_commands()
        for tool in tools:
            if not TOOL_NAME_RE.fullmatch(tool):
                self.add("ERROR", "tool-command-name", f"invalid runtime tool command name: {tool}")
                continue
            commands.append(f"command -v {tool}")
            if tool == "hewo-tool":
                commands.append('test "$(hewo-tool --check)" = HEWO_TOOL_OK')
        commands.extend(
            [
                f"{self.agent} --help >/dev/null",
                f"{self.agent} --version >/dev/null",
                f"test -x /opt/install/bin/{self.agent}",
                f"test -z \"$(find /opt/install -name AGENTS.md -print -quit)\"",
                f"test ! -d /opt/install/lib/{self.agent}/agent-definition/.agents",
            ]
        )
        smoke = "; ".join(commands)
        self.run_command("docker-runtime", ["docker", "run", "--rm", "--entrypoint", "bash", self.image, "-c", smoke])

    def runtime_tool_commands(self) -> list[str]:
        project = self.root / "src" / self.agent / "runtime" / "tools" / "pyproject.toml"
        if not project.is_file():
            return []
        try:
            data = tomllib.loads(project.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return []
        scripts = data.get("project", {}).get("scripts", {})
        return sorted(scripts) if isinstance(scripts, dict) else []

    def release_check(self) -> None:
        if not self.release_archive:
            return
        archive = self.release_archive if self.release_archive.is_absolute() else self.root / self.release_archive
        if not archive.is_file():
            self.add("ERROR", "release-payload", f"missing release archive {archive}")
            return
        self.run_command(
            "release-payload",
            [
                sys.executable,
                str(self.root / ".agents/skills/agent-consistency-audit/scripts/audit_agent.py"),
                "--agent",
                self.agent,
                "--strict",
                "--release",
                str(archive),
            ],
        )

    def run(self) -> int:
        self.required_files()
        if not NAME_RE.fullmatch(self.agent):
            return 1
        self.syntax()
        self.definition()
        if shutil.which("docker"):
            self.docker()
        else:
            self.add("ERROR", "docker-prerequisite", "docker is not installed or not on PATH")
        self.release_check()
        return 1 if any(result.level == "ERROR" for result in self.results) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--agent", required=True)
    parser.add_argument("--image", help="Docker image tag (default: <agent>:infra)")
    parser.add_argument("--release", type=Path)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    root = args.root.resolve()
    image = args.image or f"{args.agent}:infra"
    health = Health(root, args.agent, image, args.release, args.skip_build)
    code = health.run()
    if args.as_json:
        print(json.dumps({"agent": args.agent, "image": image, "results": [asdict(result) for result in health.results], "exit_code": code}, ensure_ascii=False, indent=2))
    else:
        for result in health.results:
            print(f"{result.level:<5} {result.check:<22} {result.message}")
        print(f"Summary: {sum(item.level == 'ERROR' for item in health.results)} error(s), {sum(item.level == 'PASS' for item in health.results)} pass(es)")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
