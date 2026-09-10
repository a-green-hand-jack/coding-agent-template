#!/usr/bin/env python3
"""Evaluate a candidate revision of this skill using the immutable base commit.

The grader never comes from the candidate. The base evaluator, base comparator,
fixtures, expected invariants, fixed outcome cases and the candidate manifest
are all unpacked read-only from ``git archive <base-ref>``.

This prevents a normal candidate from relaxing the evaluator, the fixtures or
the expected results in the same change. It is NOT an OS sandbox and does not
stop arbitrary malicious code from touching other host resources; do not run an
un-reviewed candidate on the host.

Exit codes: 0 HUMAN_REVIEW, 10 REJECTED, 20 BLOCKED, 2 CLI error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _evaluation_lib as lib  # noqa: E402

SKILL_RELATIVE = ".agents/skills/agent-evaluation-loop-design"
ARCHITECTURE_BASENAME = "agent-architecture.mmd"
OPTIMIZATION_BASENAME = "agent-optimization-loop.mmd"
KNOWN_DELTA_KINDS = {"readme-managed-block-sync"}

# Fixed comparator outcomes, asserted with the BASE comparator only.
OUTCOME_CASES = (
    ("paper", "current-best-result.json", "accepted-candidate-result.json", "CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE", 0),
    ("paper", "current-best-result.json", "rejected-candidate-result.json", "CANDIDATE_REJECTED", 10),
    ("paper", "current-best-result.json", "secondary-regression-candidate-result.json", "CANDIDATE_REJECTED", 10),
    ("paper", "current-best-result.json", "functional-failed-candidate-result.json", "CANDIDATE_REJECTED", 10),
    ("paper", "current-best-result.json", "environment-blocked-candidate-result.json", "ENVIRONMENT_BLOCKED", 40),
    ("paper", "current-best-result.json", "evaluation-blocked-candidate-result.json", "EVALUATION_BLOCKED", 41),
    ("paper", "current-best-result.json", "invalidated-candidate-result.json", "BASELINE_INVALIDATED", 30),
    ("paper", "current-best-unpromoted-result.json", "accepted-candidate-result.json", "FUNCTIONAL_BASELINE_MISSING", 20),
    ("invalid", "current-best-result.json", "accepted-candidate-result.json", "DESIGN_INCOMPLETE", 20),
    ("smoke", "current-best-result.json", "accepted-candidate-result.json", "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE", 20),
    ("general", "current-best-general-result.json", "generalization-required-candidate-result.json", "GENERALIZATION_REQUIRED", 42),
    ("general", "current-best-general-result.json", "generalization-satisfied-candidate-result.json", "CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE", 0),
)


class Blocked(Exception):
    def __init__(self, gate: str, reason: str) -> None:
        super().__init__(reason)
        self.gate = gate
        self.reason = reason


class Rejected(Exception):
    def __init__(self, gate: str, reason: str) -> None:
        super().__init__(reason)
        self.gate = gate
        self.reason = reason


class Report:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {
            "schema_version": 1,
            "tool": "self-bootstrap-check.py",
            "gates": [],
            "start_phase": "preconditions",
            "end_phase": "preconditions",
            "cleanup": "not-attempted",
            "sandbox_guarantee": "repository and output boundary only; not an OS sandbox",
        }

    def gate(self, name: str, state: str, reason: str = "") -> None:
        self.data["gates"].append({"gate": name, "state": state, "reason": reason})
        self.data["end_phase"] = name

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value


def git(root: Path, *arguments: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments], check=False, capture_output=True, text=True
    )
    if check and result.returncode:
        raise Blocked("git", f"git {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def resolve_commit(root: Path, ref: str) -> str:
    sha = git(root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise Blocked("refs", f"{ref!r} did not resolve to a full commit SHA")
    return sha


def check_no_symlink_root(path: Path, label: str) -> Path:
    if path.is_symlink():
        raise Blocked("paths", f"{label} is a symlink: {path}")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise Blocked("paths", f"{label} does not resolve: {path}: {exc}") from exc
    if not resolved.is_dir():
        raise Blocked("paths", f"{label} is not a directory: {path}")
    return resolved


def candidate_status(root: Path) -> dict[str, str]:
    return {
        "head": git(root, "rev-parse", "HEAD"),
        "porcelain": git(root, "status", "--porcelain=v1", "--untracked-files=all", check=False),
        "unstaged": git(root, "diff", "--name-only", check=False),
        "staged": git(root, "diff", "--cached", "--name-only", check=False),
    }


def unpack_base(repo_root: Path, base_sha: str, workspace: Path, report: Report) -> tuple[Path, dict[str, str], str]:
    """Extract the base snapshot read-only and pin it with a SHA-256 manifest."""
    archive = workspace / "base.tar"
    with archive.open("wb") as handle:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "archive", "--format=tar", base_sha],
            check=False,
            stdout=handle,
            stderr=subprocess.PIPE,
        )
    if result.returncode:
        raise Blocked("base-archive", f"git archive failed: {result.stderr.decode().strip()}")

    snapshot = workspace / "base-snapshot"
    snapshot.mkdir(mode=0o700)
    with tarfile.open(archive, "r:") as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                raise Blocked("base-archive", f"archive contains a link entry: {member.name}")
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise Blocked("base-archive", f"archive contains an unsafe path: {member.name}")
        tar.extractall(snapshot, filter="data")

    manifest: dict[str, str] = {}
    for path in sorted(snapshot.rglob("*")):
        if path.is_symlink():
            raise Blocked("base-archive", f"symlink in the base snapshot: {path}")
        if path.is_file():
            manifest[path.relative_to(snapshot).as_posix()] = lib.file_sha256(path)
    digest = lib.canonical_sha256(manifest)

    for path in sorted(snapshot.rglob("*"), reverse=True):
        mode = stat.S_IMODE(path.lstat().st_mode)
        os.chmod(path, mode & ~0o222)
    report.set("base_archive_manifest_sha256", digest)
    report.set("base_archive_file_count", len(manifest))
    return snapshot, manifest, digest


def validate_candidate_manifest(document: Any) -> dict:
    if not isinstance(document, dict):
        raise Blocked("candidate-manifest", "candidate manifest is not a JSON object")
    if document.get("schema_version") != 1:
        raise Blocked("candidate-manifest", "candidate manifest schema_version must be 1")
    delta = document.get("observable_delta")
    if not isinstance(delta, dict):
        raise Blocked("candidate-manifest", "candidate manifest has no observable_delta object")
    kind = delta.get("kind")
    if kind not in KNOWN_DELTA_KINDS:
        raise Blocked(
            "candidate-manifest",
            f"observable_delta.kind {kind!r} is not implemented by the base evaluator; "
            "a manifest cannot declare new scoring logic",
        )
    allowed = document.get("allowed_candidate_paths")
    if not isinstance(allowed, list) or not allowed or not all(isinstance(item, str) for item in allowed):
        raise Blocked("candidate-manifest", "allowed_candidate_paths must be a non-empty array of strings")
    protected = document.get("base_protected_paths")
    if not isinstance(protected, list) or not protected:
        raise Blocked("candidate-manifest", "base_protected_paths must be a non-empty array")
    for entry in allowed:
        try:
            lib.lexical_relative_check(entry)
        except lib.PathSafetyError as exc:
            raise Blocked("candidate-manifest", f"allowed path is unsafe: {exc}") from exc
        for guard in protected:
            if entry == guard or entry.startswith(guard.rstrip("/") + "/") or guard.startswith(entry + "/"):
                raise Blocked(
                    "candidate-manifest",
                    f"allowed_candidate_paths entry {entry!r} overlaps protected path {guard!r}; "
                    "a candidate cannot widen its own permissions",
                )
    return document


def path_matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return path == pattern or path.startswith(pattern + "/")


def run_base_comparator(snapshot: Path, report: Report) -> None:
    comparator = snapshot / SKILL_RELATIVE / "scripts/compare-evaluations.py"
    if not comparator.is_file():
        raise Blocked("base-comparator", f"base comparator is missing from the snapshot: {comparator}")
    fixtures = snapshot / SKILL_RELATIVE / "fixtures"
    # Resolve from the base snapshot's manifest, including pre-migration bases.
    smoke_agent = snapshot / "src" / "hewo"
    smoke_manifest = lib.parse_agent_yaml(smoke_agent / "agent.yaml")
    contracts = {
        "paper": fixtures / "paper-agent/development/evaluation-contract.json",
        "invalid": fixtures / "self-bootstrap/contract-invalid.json",
        "general": fixtures / "self-bootstrap/contract-product-general.json",
        "smoke": smoke_agent / smoke_manifest["development_dir"] / "evaluation-contract.json",
    }
    boot = fixtures / "self-bootstrap"
    before = lib.file_sha256(comparator)
    failures = []
    for contract_key, best, candidate, expected_state, expected_code in OUTCOME_CASES:
        result = subprocess.run(
            [
                sys.executable,
                str(comparator),
                "--contract",
                str(contracts[contract_key]),
                "--current-best",
                str(boot / best),
                "--candidate",
                str(boot / candidate),
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(snapshot),
        )
        try:
            state = json.loads(result.stdout).get("state")
        except json.JSONDecodeError:
            state = None
        if state != expected_state or result.returncode != expected_code:
            failures.append(
                f"{candidate} with {contract_key}: expected {expected_state}/{expected_code}, "
                f"got {state}/{result.returncode}"
            )
    if lib.file_sha256(comparator) != before:
        raise Blocked("base-comparator", "the base comparator changed while it was running")
    report.set("base_comparator_cases", len(OUTCOME_CASES))
    if failures:
        raise Blocked("base-comparator", "base comparator outcomes drifted: " + "; ".join(failures))


MARKER_BEGIN = re.compile(r"^<!--\s*BEGIN GENERATED:\s*(\S+)\s*-->\s*$")
MARKER_END = re.compile(r"^<!--\s*END GENERATED:\s*(\S+)\s*-->\s*$")


def managed_blocks(readme_text: str) -> dict[str, str]:
    """Parse README managed blocks with the BASE evaluator's own rules."""
    lines = readme_text.splitlines()
    spans: list[tuple[str, int, int]] = []
    open_marker: tuple[str, int] | None = None
    for index, line in enumerate(lines):
        begin = MARKER_BEGIN.match(line)
        end = MARKER_END.match(line)
        if begin:
            if open_marker is not None:
                raise Rejected("readme-markers", f"nested or crossed begin marker at line {index + 1}")
            open_marker = (begin.group(1), index)
        elif end:
            if open_marker is None:
                raise Rejected("readme-markers", f"end marker without a begin at line {index + 1}")
            if end.group(1) != open_marker[0]:
                raise Rejected(
                    "readme-markers",
                    f"marker names do not pair: {open_marker[0]!r} then {end.group(1)!r}",
                )
            spans.append((open_marker[0], open_marker[1], index))
            open_marker = None
    if open_marker is not None:
        raise Rejected("readme-markers", f"unclosed begin marker for {open_marker[0]!r}")
    names = [item[0] for item in spans]
    if len(set(names)) != len(names):
        raise Rejected("readme-markers", f"duplicate managed blocks: {sorted(names)}")
    blocks: dict[str, str] = {}
    for name, start, stop in spans:
        body = lines[start + 1 : stop]
        if not body or body[0].strip() != "```mermaid" or body[-1].strip() != "```":
            raise Rejected("readme-markers", f"managed block {name!r} is not a single mermaid fence")
        blocks[name] = "\n".join(body[1:-1]) + "\n"
    return blocks


def check_readme_delta(candidate_root: Path, manifest: dict, workspace: Path, report: Report) -> None:
    delta = manifest["observable_delta"]
    for relative in delta.get("expected_artifacts") or []:
        if not (candidate_root / relative).is_file():
            raise Rejected("observable-delta", f"expected artifact is missing from the candidate: {relative}")

    readme = candidate_root / "README.md"
    blocks = managed_blocks(readme.read_text(encoding="utf-8"))
    expected = {ARCHITECTURE_BASENAME, OPTIMIZATION_BASENAME}
    if set(blocks) != expected:
        raise Rejected(
            "observable-delta",
            f"README managed blocks are {sorted(blocks)}, expected {sorted(expected)}",
        )
    for basename, body in blocks.items():
        source = (candidate_root / basename).read_text(encoding="utf-8")
        if body != source:
            raise Rejected("observable-delta", f"README block for {basename} does not match the .mmd bytes")
    report.gate("observable-delta:markers-unique", "PASS")
    report.gate("observable-delta:blocks-match-mmd", "PASS")

    # check-mode-detects-drift, exercised on a disposable copy so the candidate
    # worktree is never written to.
    scratch = workspace / "drift-probe"
    scratch.mkdir()
    shutil.copy2(readme, scratch / "README.md")
    for basename in expected:
        shutil.copy2(candidate_root / basename, scratch / basename)
    tampered = (scratch / "README.md").read_text(encoding="utf-8").replace(
        "```mermaid", "```mermaid\n%% tampered", 1
    )
    (scratch / "README.md").write_text(tampered, encoding="utf-8")
    generator = candidate_root / SKILL_RELATIVE / "scripts/generate-agent-diagrams.py"
    if not generator.is_file():
        raise Rejected("observable-delta", "candidate generator is missing")
    result = subprocess.run(
        [
            sys.executable,
            str(generator),
            "--agent",
            "hewo",
            "--repo-root",
            str(candidate_root),
            "--output-dir",
            str(scratch),
            "--readme",
            str(scratch / "README.md"),
            "--check",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(scratch),
        env=probe_env(scratch),
    )
    if result.returncode == 0:
        raise Rejected(
            "observable-delta",
            "candidate generator --check did not detect a tampered README managed block",
        )
    report.gate("observable-delta:check-mode-detects-drift", "PASS")


def probe_env(root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["HOME"] = str(root)
    environment["TMPDIR"] = str(root)
    environment.pop("PYTHONPATH", None)
    return environment


def run_candidate_static_checks(candidate_root: Path, snapshot: Path, workspace: Path, report: Report) -> None:
    """Run the candidate generator/validator against a disposable fixture copy."""
    fixture_copy = workspace / "fixture-copy"
    shutil.copytree(snapshot / SKILL_RELATIVE / "fixtures/paper-agent", fixture_copy / "paper-agent")
    for path in fixture_copy.rglob("*"):
        os.chmod(path, stat.S_IMODE(path.lstat().st_mode) | 0o200)
    output = workspace / "candidate-output"
    output.mkdir()

    generator = candidate_root / SKILL_RELATIVE / "scripts/generate-agent-diagrams.py"
    validator = candidate_root / SKILL_RELATIVE / "scripts/validate-agent-evaluation.py"
    for label, script in (("generator", generator), ("validator", validator)):
        if not script.is_file():
            raise Rejected("candidate-static", f"candidate {label} is missing: {script}")

    first = subprocess.run(
        [
            sys.executable, str(generator),
            "--agent", "paper-agent",
            "--agent-root", str(fixture_copy / "paper-agent"),
            "--output-dir", str(output),
            "--no-readme",
        ],
        check=False, capture_output=True, text=True, cwd=str(output), env=probe_env(output),
    )
    if first.returncode:
        raise Rejected("candidate-static", f"candidate generator failed on the fixture: {first.stderr.strip()}")
    hashes = {name: lib.file_sha256(output / name) for name in (ARCHITECTURE_BASENAME, OPTIMIZATION_BASENAME)}
    second = subprocess.run(
        [
            sys.executable, str(generator),
            "--agent", "paper-agent",
            "--agent-root", str(fixture_copy / "paper-agent"),
            "--output-dir", str(output),
            "--no-readme",
        ],
        check=False, capture_output=True, text=True, cwd=str(output), env=probe_env(output),
    )
    if second.returncode:
        raise Rejected("candidate-static", "candidate generator failed on the second run")
    for name, digest in hashes.items():
        if lib.file_sha256(output / name) != digest:
            raise Rejected("candidate-static", f"candidate generator is not deterministic for {name}")
    report.gate("candidate-static:determinism", "PASS")

    # The base evaluator judges the output itself, using the BASE expected
    # invariants, rather than trusting the candidate validator's verdict.
    expected = lib.load_json_exact(snapshot / SKILL_RELATIVE / "fixtures/paper-agent/expected-invariants.json")
    architecture = (output / ARCHITECTURE_BASENAME).read_text(encoding="utf-8")
    optimization = (output / OPTIMIZATION_BASENAME).read_text(encoding="utf-8")
    missing: list[str] = []
    for node in list(expected["architecture"]["required_node_ids"]) + list(
        expected["architecture"]["required_subgraph_ids"]
    ):
        if not re.search(rf"(^|\s){re.escape(node)}\[", architecture, flags=re.MULTILINE):
            missing.append(f"architecture node {node}")
    for source, target in expected["architecture"]["required_edges"]:
        if not re.search(rf"^\s*{re.escape(source)}\s*-->\s*{re.escape(target)}\s*$", architecture, flags=re.MULTILINE):
            missing.append(f"architecture edge {source}->{target}")
    declared = {
        match.group(1)
        for match in re.finditer(
            r'^\s*state\s+"[^"]+"\s+as\s+([A-Za-z0-9_]+)', optimization, flags=re.MULTILINE
        )
    } | {
        match.group(1)
        for match in re.finditer(r"^\s*state\s+([A-Za-z0-9_]+)\s*\{", optimization, flags=re.MULTILINE)
    }
    # A substring test would be satisfied by a transition or a note still
    # mentioning the name, so require an actual state declaration.
    for state in expected["optimization"]["required_state_ids"]:
        if state not in declared:
            missing.append(f"optimization state declaration {state}")
    for source, target in expected["optimization"]["required_transitions"]:
        if not re.search(
            rf"^\s*{re.escape(source)}\s*-->\s*{re.escape(target)}\s*(:.*)?$", optimization, flags=re.MULTILINE
        ):
            missing.append(f"optimization transition {source}->{target}")
    for node in expected["architecture"]["forbidden_node_ids"]:
        if re.search(rf"(^|\s){re.escape(node)}\[", architecture, flags=re.MULTILINE):
            missing.append(f"forbidden node present: {node}")
    if "AGENTS.md" in architecture or "AGENTS.md" in optimization:
        missing.append("a diagram references AGENTS.md")
    if missing:
        raise Rejected("candidate-static", "required invariants lost: " + "; ".join(sorted(missing)[:12]))
    report.gate("candidate-static:base-invariants", "PASS")

    validation = subprocess.run(
        [
            sys.executable, str(validator),
            "--agent", "paper-agent",
            "--agent-root", str(fixture_copy / "paper-agent"),
            "--output-dir", str(output),
            "--expected", str(snapshot / SKILL_RELATIVE / "fixtures/paper-agent/expected-invariants.json"),
            "--strict",
        ],
        check=False, capture_output=True, text=True, cwd=str(output), env=probe_env(output),
    )
    report.gate(
        "candidate-static:candidate-validator",
        "PASS" if validation.returncode == 0 else "ADVISORY-FAIL",
        "" if validation.returncode == 0 else validation.stderr.strip()[:400],
    )

    runtime_writes = [
        path.as_posix()
        for path in (candidate_root / "src").rglob("agent-*.mmd")
        if "runtime" in path.parts
    ]
    if runtime_writes:
        raise Rejected("candidate-static", f"diagrams were written into a product runtime: {runtime_writes}")
    report.gate("candidate-static:runtime-boundary", "PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--candidate-ref", required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--candidate-manifest", required=True)
    parser.add_argument("--output", type=Path, help="explicit external execution-report destination")
    args = parser.parse_args()

    report = Report()
    workspace: Path | None = None
    state = "BLOCKED"
    reason = ""
    exit_code = 20
    try:
        repo_root = check_no_symlink_root(args.repo_root, "repo root")
        base_sha = resolve_commit(repo_root, args.base_ref)
        candidate_sha = resolve_commit(repo_root, args.candidate_ref)
        report.set("base_ref", args.base_ref)
        report.set("base_sha", base_sha)
        report.set("candidate_ref", args.candidate_ref)
        report.set("candidate_sha", candidate_sha)
        report.set("base_tree_sha", git(repo_root, "rev-parse", f"{base_sha}^{{tree}}"))
        report.set("candidate_tree_sha", git(repo_root, "rev-parse", f"{candidate_sha}^{{tree}}"))
        if base_sha == candidate_sha:
            raise Blocked("refs", "base and candidate refs resolve to the same commit")
        ancestry = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", base_sha, candidate_sha],
            check=False, capture_output=True, text=True,
        )
        if ancestry.returncode:
            raise Blocked("refs", "base ref is not an ancestor of the candidate ref")
        report.gate("refs", "PASS")

        candidate_root = check_no_symlink_root(args.candidate_root, "candidate root")
        report.set("requested_head", candidate_sha)
        toplevel = Path(git(candidate_root, "rev-parse", "--show-toplevel")).resolve()
        if toplevel != candidate_root:
            raise Blocked("candidate-worktree", f"candidate root is not a worktree root: {toplevel}")
        before = candidate_status(candidate_root)
        report.set("observed_head", before["head"])
        report.set("candidate_root_digest", lib.sha256_hex(str(candidate_root).encode("utf-8")))
        if before["head"] != candidate_sha:
            raise Blocked("candidate-worktree", "candidate worktree HEAD is not the requested candidate SHA")
        symbolic = subprocess.run(
            ["git", "-C", str(candidate_root), "symbolic-ref", "-q", "HEAD"],
            check=False, capture_output=True, text=True,
        )
        if symbolic.returncode == 0:
            raise Blocked("candidate-worktree", "candidate worktree is not detached")
        if before["porcelain"] or before["unstaged"] or before["staged"]:
            raise Blocked("candidate-worktree", "candidate worktree is not clean")
        report.gate("candidate-worktree", "PASS")

        workspace = Path(tempfile.mkdtemp(prefix="self-bootstrap-"))
        os.chmod(workspace, 0o700)
        snapshot, base_manifest, base_digest = unpack_base(repo_root, base_sha, workspace, report)
        report.gate("base-archive", "PASS")

        try:
            lib.lexical_relative_check(args.candidate_manifest)
            manifest_path = lib.safe_child_path(snapshot, args.candidate_manifest)
        except lib.PathSafetyError as exc:
            raise Blocked("candidate-manifest", f"manifest path is unusable in the base snapshot: {exc}") from exc
        manifest = validate_candidate_manifest(lib.load_json_exact(manifest_path))
        report.set("candidate_manifest_sha256", lib.canonical_sha256(manifest))
        report.set("observable_delta_kind", manifest["observable_delta"]["kind"])
        report.gate("candidate-manifest", "PASS")

        changed = [
            item for item in git(repo_root, "diff", "--name-only", base_sha, candidate_sha).splitlines() if item
        ]
        allowed = manifest["allowed_candidate_paths"]
        protected = manifest["base_protected_paths"]
        outside = [item for item in changed if not any(path_matches(item, entry) for entry in allowed)]
        touched_protected = [item for item in changed if any(path_matches(item, entry) for entry in protected)]
        report.set("protected_path_diff", touched_protected)
        report.set("candidate_changed_paths", changed)
        if touched_protected:
            raise Blocked(
                "protected-paths",
                f"candidate changed protected evaluator/fixture paths: {touched_protected}",
            )
        if outside:
            raise Blocked("allowlist", f"candidate changed paths outside its allowlist: {outside}")
        if not changed:
            raise Rejected("allowlist", "candidate has no tracked change relative to the base")
        report.gate("protected-paths", "PASS")
        report.gate("allowlist", "PASS")

        run_base_comparator(snapshot, report)
        report.gate("base-comparator", "PASS")

        run_candidate_static_checks(candidate_root, snapshot, workspace, report)
        check_readme_delta(candidate_root, manifest, workspace, report)

        after = candidate_status(candidate_root)
        if after != before:
            raise Blocked("post-run-clean", "the candidate worktree changed during the run")
        post_manifest = {
            path.relative_to(snapshot).as_posix(): lib.file_sha256(path)
            for path in sorted(snapshot.rglob("*"))
            if path.is_file()
        }
        if lib.canonical_sha256(post_manifest) != base_digest:
            raise Blocked("post-run-clean", "the base snapshot changed during the run")
        report.gate("post-run-clean", "PASS")

        state = "HUMAN_REVIEW"
        exit_code = 0
        reason = (
            "machine gates passed and the pre-declared observable delta was confirmed; "
            "a human still decides readability, simplicity and whether this helps a developer"
        )
    except Rejected as exc:
        report.gate(exc.gate, "REJECTED", exc.reason)
        state, reason, exit_code = "REJECTED", exc.reason, 10
    except Blocked as exc:
        report.gate(exc.gate, "BLOCKED", exc.reason)
        state, reason, exit_code = "BLOCKED", exc.reason, 20
    except (lib.DocumentError, lib.PathSafetyError) as exc:
        report.gate("input", "BLOCKED", str(exc))
        state, reason, exit_code = "BLOCKED", str(exc), 20
    finally:
        if workspace is not None:
            try:
                shutil.rmtree(workspace, onexc=lambda func, path, exc: _force_remove(path))
                report.data["cleanup"] = "removed"
            except Exception as exc:  # cleanup failure must not be silent
                report.data["cleanup"] = f"failed: {exc}"
                if state == "HUMAN_REVIEW":
                    state, reason, exit_code = "BLOCKED", f"cleanup failed: {exc}", 20
        else:
            report.data["cleanup"] = "nothing-to-clean"

    report.set("state", state)
    report.set("reason", reason)
    report.set("exit_code", exit_code)
    text = json.dumps(report.data, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        try:
            lib.atomic_write_text(args.output, text + "\n")
        except lib.PathSafetyError as exc:
            print(f"ERROR unsafe report destination: {exc}", file=sys.stderr)
            print(text)
            return 2
    print(text)
    return exit_code


def _force_remove(path: str) -> None:
    target = Path(path)
    try:
        os.chmod(target.parent, stat.S_IMODE(target.parent.lstat().st_mode) | 0o700)
        os.chmod(target, stat.S_IMODE(target.lstat().st_mode) | 0o600)
    except OSError:
        pass
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target, ignore_errors=True)
    else:
        target.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
