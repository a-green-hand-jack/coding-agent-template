#!/usr/bin/env python3
"""Validate an Agent's evaluation design and its generated diagrams.

Checks the evaluation contract's schema, the agent manifest and paths, the
required diagram nodes/edges/states/transitions, byte-level determinism, the
product/development boundary and secret safety. It never calls a provider.

The contract schema is imported from the protected ``compare-evaluations.py``
so that editing this validator cannot weaken the normative rules.

Exit codes:
  0  OK (including SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE unless --require-performance).
     Warnings are advisory and never change the exit code; only problems fail.
  1  validation problems
  2  CLI error
  20 DESIGN_INCOMPLETE (contract missing or schema invalid)
  21 SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE under --require-performance
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _evaluation_lib as lib  # noqa: E402

GENERATOR = HERE / "generate-agent-diagrams.py"
COMPARATOR = HERE / "compare-evaluations.py"
ARCHITECTURE_BASENAME = "agent-architecture.mmd"
OPTIMIZATION_BASENAME = "agent-optimization-loop.mmd"

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]+ PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[A-Z0-9_]*API_KEY\s*=\s*\S+"),
)

DEFAULT_REQUIRED_ARCHITECTURE_NODES = (
    "user_input",
    "user_output",
    "rt_identity",
    "rt_memory_policy",
    "ex_backend",
    "ex_provider",
    "ex_model",
    "ev_artifact",
    "ev_trajectory",
    "ev_verifier",
    "dv_contract",
    "dv_validation",
    "dv_benchmark",
    "dv_loop",
)
DEFAULT_REQUIRED_SUBGRAPHS = (
    "user",
    "runtime",
    "grp_knowledge",
    "grp_skills",
    "grp_workflows",
    "grp_tools",
    "execution",
    "evidence",
    "development",
)


def load_generator():
    """Import the generator's README marker rules by path."""
    spec = importlib.util.spec_from_file_location("_diagram_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the generator: {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_protected_schema():
    """Import validate_contract from the protected comparator by path."""
    spec = importlib.util.spec_from_file_location("_protected_comparator", COMPARATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the protected comparator: {COMPARATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_generator(agent: str, agent_root: Path, contract: Path | None, output_dir: Path) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        str(GENERATOR),
        "--agent",
        agent,
        "--agent-root",
        str(agent_root),
        "--output-dir",
        str(output_dir),
        "--no-readme",
    ]
    if contract is not None:
        command += ["--contract", str(contract)]
    return subprocess.run(command, check=False, capture_output=True, text=True)


def edges_from_flowchart(text: str) -> set[tuple[str, str]]:
    edges = set()
    pattern = re.compile(r"^\s*([A-Za-z0-9_]+)\s*-->(?:\|[^|]*\|)?\s*([A-Za-z0-9_]+)\s*$")
    for line in text.splitlines():
        if line.lstrip().startswith("%%"):
            continue
        match = pattern.match(line)
        if match:
            edges.add((match.group(1), match.group(2)))
    return edges


def transitions_from_state_diagram(text: str) -> set[tuple[str, str]]:
    transitions = set()
    pattern = re.compile(r"^\s*([A-Za-z0-9_\[\]*]+)\s*-->\s*([A-Za-z0-9_\[\]*]+)\s*(?::.*)?$")
    for line in text.splitlines():
        if line.lstrip().startswith("%%"):
            continue
        match = pattern.match(line)
        if match:
            transitions.add((match.group(1), match.group(2)))
    return transitions


def declared_nodes(text: str) -> set[str]:
    nodes = set()
    for match in re.finditer(r"^\s*([A-Za-z0-9_]+)\[", text, flags=re.MULTILINE):
        nodes.add(match.group(1))
    for match in re.finditer(r"^\s*subgraph\s+([A-Za-z0-9_]+)\[", text, flags=re.MULTILINE):
        nodes.add(match.group(1))
    return nodes


def declared_states(text: str) -> set[str]:
    states = set()
    for match in re.finditer(r'^\s*state\s+"([^"]+)"\s+as\s+([A-Za-z0-9_]+)', text, flags=re.MULTILINE):
        states.add(match.group(2))
    for match in re.finditer(r"^\s*state\s+([A-Za-z0-9_]+)\s*\{", text, flags=re.MULTILINE):
        states.add(match.group(1))
    return states


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", default="hewo")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--agent-root", type=Path, help="default: <repo-root>/src/<agent>")
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--output-dir", type=Path, help="default: <repo-root>")
    parser.add_argument("--readme", type=Path, help="default: <output-dir>/README.md")
    parser.add_argument("--no-readme", action="store_true", help="skip the README managed-block checks")
    parser.add_argument("--expected", type=Path, help="expected-invariants.json for a fixture")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="run the full structural check set; a valid smoke-only contract still exits 0",
    )
    parser.add_argument("--require-performance", action="store_true", help="fail on a smoke-only contract")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    agent_root = (args.agent_root or repo_root / "src" / args.agent).resolve()
    output_dir = (args.output_dir or repo_root).resolve()
    problems: list[str] = []
    warnings: list[str] = []

    if not agent_root.is_dir():
        print(f"ERROR agent root does not exist: {agent_root}", file=sys.stderr)
        return 2

    # --- agent manifest -------------------------------------------------
    manifest: dict[str, str] = {}
    manifest_path = agent_root / "agent.yaml"
    if not manifest_path.is_file():
        problems.append(f"agent.yaml is missing: {manifest_path}")
    else:
        try:
            manifest = lib.parse_agent_yaml(manifest_path)
        except lib.DocumentError as exc:
            problems.append(str(exc))
    runtime_name = manifest.get("runtime_dir")
    if not runtime_name:
        problems.append("agent.yaml does not declare runtime_dir")
    elif not (agent_root / runtime_name).is_dir():
        problems.append(f"runtime_dir does not exist: {runtime_name}")
    development_name = manifest.get("development_dir")
    if not development_name:
        problems.append("agent.yaml does not declare development_dir")

    # --- contract -------------------------------------------------------
    contract_path = args.contract
    if contract_path is None and development_name:
        contract_path = agent_root / development_name / "evaluation-contract.json"
    state = "PERFORMANCE_READY"
    contract: Any = None
    if contract_path is None or not contract_path.is_file():
        state = "DESIGN_INCOMPLETE"
        problems.append(f"evaluation contract is missing: {contract_path}")
    else:
        try:
            contract = lib.load_json_exact(contract_path)
        except lib.DocumentError as exc:
            state = "DESIGN_INCOMPLETE"
            problems.append(str(exc))
    if contract is not None:
        schema_problems = load_protected_schema().validate_contract(contract)
        if schema_problems:
            state = "DESIGN_INCOMPLETE"
            problems.extend(schema_problems)
        elif contract.get("mode") == "infrastructure-smoke-only":
            state = "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE"

    if state == "DESIGN_INCOMPLETE":
        report(args, state, problems, warnings)
        return 20

    # --- diagrams exist and match a fresh generation --------------------
    with tempfile.TemporaryDirectory(prefix="agent-eval-validate-") as scratch:
        first = Path(scratch) / "first"
        second = Path(scratch) / "second"
        first.mkdir()
        second.mkdir()
        run_a = run_generator(args.agent, agent_root, args.contract, first)
        run_b = run_generator(args.agent, agent_root, args.contract, second)
        if run_a.returncode or run_b.returncode:
            problems.append(f"generator failed: {(run_a.stderr or run_b.stderr).strip()}")
            report(args, state, problems, warnings)
            return 1
        rendered: dict[str, str] = {}
        for basename in (ARCHITECTURE_BASENAME, OPTIMIZATION_BASENAME):
            text_a = (first / basename).read_text(encoding="utf-8")
            text_b = (second / basename).read_text(encoding="utf-8")
            if text_a != text_b:
                problems.append(f"generator is not deterministic for {basename}")
            rendered[basename] = text_a
            committed = output_dir / basename
            if not committed.is_file():
                problems.append(f"generated diagram is missing from the output directory: {basename}")
            elif committed.read_text(encoding="utf-8") != text_a:
                problems.append(f"{basename} in the output directory differs from a fresh generation")

    architecture = rendered[ARCHITECTURE_BASENAME]
    optimization = rendered[OPTIMIZATION_BASENAME]

    # --- required structure ---------------------------------------------
    expected: dict[str, Any] = {}
    if args.expected is not None:
        if not args.expected.is_file():
            problems.append(f"expected invariants file is missing: {args.expected}")
        else:
            try:
                expected = lib.load_json_exact(args.expected)
            except lib.DocumentError as exc:
                problems.append(str(exc))

    architecture_expected = expected.get("architecture") if isinstance(expected.get("architecture"), dict) else {}
    optimization_expected = expected.get("optimization") if isinstance(expected.get("optimization"), dict) else {}

    nodes = declared_nodes(architecture)
    required_nodes = list(architecture_expected.get("required_node_ids") or DEFAULT_REQUIRED_ARCHITECTURE_NODES)
    required_nodes += list(architecture_expected.get("required_subgraph_ids") or DEFAULT_REQUIRED_SUBGRAPHS)
    for node in required_nodes:
        if node not in nodes:
            problems.append(f"{ARCHITECTURE_BASENAME} is missing required node/subgraph {node}")
    for node in architecture_expected.get("forbidden_node_ids") or []:
        if node in nodes:
            problems.append(f"{ARCHITECTURE_BASENAME} declares forbidden node {node}")

    edges = edges_from_flowchart(architecture)
    for pair in architecture_expected.get("required_edges") or []:
        if tuple(pair) not in edges:
            problems.append(f"{ARCHITECTURE_BASENAME} is missing required edge {pair[0]} --> {pair[1]}")

    states = declared_states(optimization)
    for name in optimization_expected.get("required_state_ids") or []:
        if name not in states:
            problems.append(f"{OPTIMIZATION_BASENAME} is missing required state {name}")
    transitions = transitions_from_state_diagram(optimization)
    for pair in optimization_expected.get("required_transitions") or []:
        if tuple(pair) not in transitions:
            problems.append(f"{OPTIMIZATION_BASENAME} is missing required transition {pair[0]} --> {pair[1]}")

    for text, key, basename in (
        (architecture, "required_text", ARCHITECTURE_BASENAME),
        (optimization, "required_text", OPTIMIZATION_BASENAME),
    ):
        source = architecture_expected if basename == ARCHITECTURE_BASENAME else optimization_expected
        for needle in source.get(key) or []:
            if needle not in text:
                problems.append(f"{basename} does not contain required text {needle!r}")
    for needle in architecture_expected.get("forbidden_text") or []:
        if needle in architecture:
            problems.append(f"{ARCHITECTURE_BASENAME} contains forbidden text {needle!r}")

    # --- boundary and secret safety --------------------------------------
    if runtime_name:
        runtime_dir = (agent_root / runtime_name).resolve()
        if lib.is_within(output_dir, runtime_dir):
            problems.append("output directory is inside the product runtime; diagrams are development artifacts")
        for basename in (ARCHITECTURE_BASENAME, OPTIMIZATION_BASENAME):
            if (runtime_dir / basename).exists():
                problems.append(f"{basename} must not exist inside the product runtime")
    for basename, text in rendered.items():
        if "AGENTS.md" in text:
            problems.append(f"{basename} references AGENTS.md; development instructions are not product components")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"{basename} contains possible credential material")
                break

    # --- README managed blocks -------------------------------------------
    if not args.no_readme:
        explicit = args.readme is not None
        readme_path = args.readme or (output_dir / "README.md")
        if not readme_path.is_file():
            # An explicitly named README must exist. A fixture output directory
            # has no README of its own, so the default path only warns.
            message = f"README does not exist: {readme_path}"
            (problems if explicit else warnings).append(message)
        else:
            generator_module = load_generator()
            readme_text = readme_path.read_text(encoding="utf-8")
            try:
                spans = generator_module.marker_spans(readme_text)
            except generator_module.ReadmeError as exc:
                problems.append(f"README managed blocks: {exc}")
                spans = []
            names = {name for name, _, _ in spans}
            for basename in (ARCHITECTURE_BASENAME, OPTIMIZATION_BASENAME):
                if basename not in names:
                    problems.append(f"README has no managed block for {basename}")
            for name in sorted(names - {ARCHITECTURE_BASENAME, OPTIMIZATION_BASENAME}):
                problems.append(f"README has a managed block with an unknown basename: {name}")
            if spans and not problems:
                try:
                    if generator_module.apply_blocks(readme_text, rendered) != readme_text:
                        problems.append("README managed blocks are stale relative to the generated .mmd bytes")
                except generator_module.ReadmeError as exc:
                    problems.append(f"README managed blocks: {exc}")
            for basename in (ARCHITECTURE_BASENAME, OPTIMIZATION_BASENAME):
                if f"({basename})" not in readme_text:
                    warnings.append(f"README does not link the {basename} source file")

    declared_state = expected.get("contract_state")
    if declared_state is not None and declared_state != state:
        problems.append(f"expected contract_state {declared_state!r} but computed {state!r}")

    if state == "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE":
        message = (
            "contract is infrastructure-smoke-only: it can render diagrams but can never "
            "demonstrate a performance improvement"
        )
        if args.require_performance:
            problems.append(message)
        else:
            warnings.append(message)

    report(args, state, problems, warnings)
    if problems:
        if state == "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE" and args.require_performance and len(problems) == 1:
            return 21
        return 1
    return 0


def report(args: argparse.Namespace, state: str, problems: list[str], warnings: list[str]) -> None:
    for item in warnings:
        print(f"WARN  {item}", file=sys.stderr)
    for item in problems:
        print(f"ERROR {item}", file=sys.stderr)
    print(
        json.dumps(
            {
                "schema_version": 1,
                "tool": "validate-agent-evaluation.py",
                "agent": args.agent,
                "state": state,
                "problems": problems,
                "warnings": warnings,
                "ok": not problems,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
