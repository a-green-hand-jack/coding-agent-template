#!/usr/bin/env python3
"""Generate the product-structure and optimization-loop Mermaid diagrams.

Implements ``../references/agent-architecture-schema.md``. The product diagram
is built from a real filesystem scan of the Agent's runtime directory plus the
explicit evaluation contract; nothing about product semantics is guessed from
prose. The optimization diagram is built from the fixed state schema.

Deterministic: identical inputs produce byte-identical output. Writes the two
``.mmd`` files and, unless ``--no-readme`` is given, synchronises them into
README's managed blocks. The ``.mmd`` files stay the single source of truth;
README never holds a second copy that can drift. Never writes into a product
runtime directory. No provider access, no credentials, no network.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _evaluation_lib as lib  # noqa: E402

ARCHITECTURE_BASENAME = "agent-architecture.mmd"
OPTIMIZATION_BASENAME = "agent-optimization-loop.mmd"

# Files under tools/ that are packaging metadata rather than leaf tools.
TOOL_DENYLIST = {
    "AGENTS.md",
    "README.md",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
}

STATES = (
    "INTENT_DEFINED",
    "CONTRACT_DESIGNED",
    "FUNCTIONAL_BASELINE_BUILT",
    "BASELINE_MEASURED",
    "HYPOTHESIS_READY",
    "CANDIDATE_IMPLEMENTED",
    "CANDIDATE_EVALUATING",
    "EVIDENCE_VALIDATED",
    "COMPARE_WITH_CURRENT_BEST",
    "DESIGN_INCOMPLETE",
    "FUNCTIONAL_BASELINE_MISSING",
    "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE",
    "ENVIRONMENT_BLOCKED",
    "EVALUATION_BLOCKED",
    "BASELINE_INVALIDATED",
    "CANDIDATE_REJECTED",
    "CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE",
    "GENERALIZATION_REQUIRED",
    "ACCEPTED_AS_CURRENT_BEST",
    "STOPPED",
)

TRANSITIONS = (
    ("INTENT_DEFINED", "CONTRACT_DESIGNED", "human intent recorded"),
    ("CONTRACT_DESIGNED", "FUNCTIONAL_BASELINE_BUILT", "contract valid and performance mode"),
    ("CONTRACT_DESIGNED", "DESIGN_INCOMPLETE", "contract missing or schema invalid"),
    ("CONTRACT_DESIGNED", "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE", "contract mode is infrastructure smoke only"),
    ("FUNCTIONAL_BASELINE_BUILT", "BASELINE_MEASURED", "functional checks decide pass or fail stably"),
    ("FUNCTIONAL_BASELINE_BUILT", "FUNCTIONAL_BASELINE_MISSING", "contract or verifier cannot decide yet"),
    ("BASELINE_MEASURED", "HYPOTHESIS_READY", "current best measured and promoted"),
    ("HYPOTHESIS_READY", "CANDIDATE_IMPLEMENTED", "one improvement hypothesis at a time"),
    ("CANDIDATE_IMPLEMENTED", "CANDIDATE_EVALUATING", "approved runner under the fixed condition manifest"),
    ("CANDIDATE_EVALUATING", "EVIDENCE_VALIDATED", "samples and evidence collected"),
    ("EVIDENCE_VALIDATED", "COMPARE_WITH_CURRENT_BEST", "schema, hashes and provenance check out"),
    ("COMPARE_WITH_CURRENT_BEST", "BASELINE_INVALIDATED", "condition manifests differ"),
    ("COMPARE_WITH_CURRENT_BEST", "ENVIRONMENT_BLOCKED", "credential, provider or infrastructure failure"),
    ("COMPARE_WITH_CURRENT_BEST", "EVALUATION_BLOCKED", "benchmark, verifier or evidence failure"),
    ("COMPARE_WITH_CURRENT_BEST", "DESIGN_INCOMPLETE", "required design fields missing or invalid"),
    ("COMPARE_WITH_CURRENT_BEST", "FUNCTIONAL_BASELINE_MISSING", "current best invalid or not promoted"),
    ("COMPARE_WITH_CURRENT_BEST", "CANDIDATE_REJECTED", "functional failure, threshold not met or regression"),
    ("COMPARE_WITH_CURRENT_BEST", "CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE", "fixed benchmark threshold met"),
    ("CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE", "ACCEPTED_AS_CURRENT_BEST", "benchmark-local scope plus promotion gate"),
    ("CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE", "GENERALIZATION_REQUIRED", "product-general claim requested"),
    ("ACCEPTED_AS_CURRENT_BEST", "HYPOTHESIS_READY", "keep iterating"),
    ("ACCEPTED_AS_CURRENT_BEST", "STOPPED", "stop condition reached"),
    ("CANDIDATE_REJECTED", "HYPOTHESIS_READY", "new hypothesis or rollback to previous best"),
    ("ENVIRONMENT_BLOCKED", "CANDIDATE_EVALUATING", "fix the environment and rerun the same candidate"),
    ("EVALUATION_BLOCKED", "CANDIDATE_EVALUATING", "fix benchmark, verifier or evidence and rerun"),
    ("BASELINE_INVALIDATED", "BASELINE_MEASURED", "re-measure current best under the new condition identity"),
    ("GENERALIZATION_REQUIRED", "HYPOTHESIS_READY", "independent holdout and human review still pending"),
)


MARKER_BEGIN = re.compile(r"^<!--\s*BEGIN GENERATED:\s*(\S+)\s*-->\s*$")
MARKER_END = re.compile(r"^<!--\s*END GENERATED:\s*(\S+)\s*-->\s*$")


class ReadmeError(Exception):
    """README managed blocks are missing, duplicated, crossed or mis-paired."""


def marker_spans(text: str) -> list[tuple[str, int, int]]:
    """Locate managed blocks, refusing duplicated, crossed or mis-paired markers."""
    lines = text.splitlines()
    spans: list[tuple[str, int, int]] = []
    open_marker: tuple[str, int] | None = None
    for index, line in enumerate(lines):
        begin = MARKER_BEGIN.match(line)
        end = MARKER_END.match(line)
        if begin:
            if open_marker is not None:
                raise ReadmeError(
                    f"line {index + 1}: managed block for {begin.group(1)!r} opens inside "
                    f"the still-open block for {open_marker[0]!r}"
                )
            open_marker = (begin.group(1), index)
        elif end:
            if open_marker is None:
                raise ReadmeError(f"line {index + 1}: END GENERATED without a matching BEGIN")
            if end.group(1) != open_marker[0]:
                raise ReadmeError(
                    f"line {index + 1}: markers do not pair, {open_marker[0]!r} then {end.group(1)!r}"
                )
            spans.append((open_marker[0], open_marker[1], index))
            open_marker = None
    if open_marker is not None:
        raise ReadmeError(f"unclosed managed block for {open_marker[0]!r}")
    names = [item[0] for item in spans]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ReadmeError(f"duplicate managed blocks: {duplicates}")
    return spans


def block_body(basename: str, content: str) -> list[str]:
    return ["```mermaid", *content.rstrip("\n").split("\n"), "```"]


def apply_blocks(text: str, rendered: dict[str, str]) -> str:
    """Rewrite only the managed block bodies; everything else is untouched."""
    spans = marker_spans(text)
    present = {name for name, _, _ in spans}
    missing = sorted(set(rendered) - present)
    if missing:
        raise ReadmeError(
            f"README has no managed block for {missing}; run --init-readme once to insert them"
        )
    unknown = sorted(present - set(rendered))
    if unknown:
        raise ReadmeError(f"README has managed blocks with unknown basenames: {unknown}")
    lines = text.splitlines()
    for name, start, stop in sorted(spans, key=lambda item: item[1], reverse=True):
        lines[start + 1 : stop] = block_body(name, rendered[name])
    return "\n".join(lines) + "\n"


def initial_section(rendered: dict[str, str], basenames: tuple[str, ...]) -> list[str]:
    lines = [
        "",
        "## Agent diagrams",
        "",
        "Generated by the development-only `agent-evaluation-loop-design` skill. The",
        "`.mmd` files are the single source of truth; the blocks below are generated and",
        "are rewritten in place, so never hand-edit them.",
        "",
    ]
    for basename in basenames:
        lines += [
            f"Source: [`{basename}`]({basename})",
            "",
            f"<!-- BEGIN GENERATED: {basename} -->",
            *block_body(basename, rendered[basename]),
            f"<!-- END GENERATED: {basename} -->",
            "",
        ]
    return lines


def insert_initial_blocks(text: str, rendered: dict[str, str], basenames: tuple[str, ...]) -> str:
    """Insert both blocks once, only when neither marker exists anywhere."""
    lines = text.splitlines()
    for line in lines:
        if MARKER_BEGIN.match(line) or MARKER_END.match(line):
            raise ReadmeError(
                "--init-readme refuses to run: a GENERATED marker already exists. "
                "Repair the existing markers by hand instead."
            )
    while lines and not lines[-1].strip():
        lines.pop()
    combined = lines + initial_section(rendered, basenames)
    while combined and not combined[-1].strip():
        combined.pop()
    return "\n".join(combined) + "\n"


class Component:
    def __init__(self, node_id: str, label: str, relative: str) -> None:
        self.node_id = node_id
        self.label = label
        self.relative = relative


class Scan:
    def __init__(self) -> None:
        self.runtime_dir: Path | None = None
        self.runtime_relative = ""
        self.identity = False
        self.memory_policy = False
        self.knowledge: list[Component] = []
        self.skills: list[Component] = []
        self.workflows: list[Component] = []
        self.tools: list[Component] = []
        self.problems: list[str] = []


def sanitize(text: str) -> str:
    """Make arbitrary text safe inside a quoted Mermaid label."""
    cleaned = " ".join(str(text).split())
    return cleaned.replace('"', "'").replace("[", "(").replace("]", ")")


def shorten(text: str, limit: int = 110) -> str:
    cleaned = sanitize(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def allocate(prefix: str, name: str, used: set[str]) -> str:
    base = f"{prefix}_{lib.slug(name)}"
    candidate = base
    counter = 2
    while candidate in used:
        candidate = f"{base}_{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def scan_runtime(agent_root: Path, manifest: dict[str, str]) -> Scan:
    scan = Scan()
    runtime_name = manifest.get("runtime_dir")
    if not runtime_name:
        scan.problems.append("agent.yaml does not declare runtime_dir")
        return scan
    try:
        runtime_dir = lib.safe_child_path(agent_root, runtime_name)
    except lib.PathSafetyError as exc:
        scan.problems.append(f"runtime_dir is unusable: {exc}")
        return scan
    if not runtime_dir.is_dir():
        scan.problems.append(f"runtime_dir does not exist: {runtime_name}")
        return scan
    scan.runtime_dir = runtime_dir
    scan.runtime_relative = runtime_name
    scan.identity = (runtime_dir / "identity.md").is_file()
    scan.memory_policy = (runtime_dir / "memory-policy.md").is_file()
    if not scan.identity:
        scan.problems.append("runtime is missing identity.md")
    if not scan.memory_policy:
        scan.problems.append("runtime is missing memory-policy.md")

    used: set[str] = set()

    knowledge_dir = runtime_dir / "knowledge"
    if knowledge_dir.is_dir():
        for path in sorted(knowledge_dir.rglob("*.md"), key=lambda item: item.as_posix()):
            if path.name == "AGENTS.md" or not path.is_file():
                continue
            relative = path.relative_to(knowledge_dir).as_posix()
            scan.knowledge.append(
                Component(allocate("kn", relative.rsplit(".", 1)[0], used), relative, relative)
            )

    skills_dir = runtime_dir / "skills"
    if skills_dir.is_dir():
        for path in sorted(skills_dir.iterdir(), key=lambda item: item.as_posix()):
            if not path.is_dir() or not (path / "SKILL.md").is_file():
                continue
            scan.skills.append(Component(allocate("sk", path.name, used), path.name, f"skills/{path.name}"))

    workflows_dir = runtime_dir / "workflows"
    if workflows_dir.is_dir():
        for path in sorted(workflows_dir.rglob("*.md"), key=lambda item: item.as_posix()):
            if path.name == "AGENTS.md" or not path.is_file():
                continue
            relative = path.relative_to(workflows_dir).as_posix()
            scan.workflows.append(
                Component(allocate("wf", relative.rsplit(".", 1)[0], used), relative, relative)
            )

    tools_dir = runtime_dir / "tools"
    if tools_dir.is_dir():
        for path in sorted(tools_dir.iterdir(), key=lambda item: item.as_posix()):
            if not path.is_file() or path.name in TOOL_DENYLIST:
                continue
            stem = path.name.rsplit(".", 1)[0] if "." in path.name else path.name
            scan.tools.append(Component(allocate("tl", stem, used), path.name, f"tools/{path.name}"))

    return scan


def contract_view(contract: Any, problems: list[str]) -> dict[str, str]:
    """Derive only the labels the contract actually authorizes."""
    if problems or not isinstance(contract, dict):
        return {
            "state": "DESIGN_INCOMPLETE",
            "mode": "unknown",
            "goal": "no valid evaluation contract; product semantics are unknown",
            "input": "unknown until a contract exists",
            "output": "unknown until a contract exists",
            "artifacts": "unknown",
            "metric": "no primary metric declared",
            "checks": "no functional checks declared",
            "claim_scope": "unknown",
        }
    mode = contract.get("mode")
    product = contract.get("product") if isinstance(contract.get("product"), dict) else {}
    functional = contract.get("functional_contract") if isinstance(contract.get("functional_contract"), dict) else {}
    artifacts = functional.get("required_artifacts") or []
    checks = [
        item.get("id")
        for item in functional.get("checks") or []
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if mode == "performance":
        metrics = contract.get("metrics") if isinstance(contract.get("metrics"), dict) else {}
        primary = metrics.get("primary") if isinstance(metrics.get("primary"), dict) else {}
        metric = f"{primary.get('name')} ({primary.get('direction')})"
        generalization = contract.get("generalization") if isinstance(contract.get("generalization"), dict) else {}
        scope = str(generalization.get("claim_scope"))
        state = "PERFORMANCE_READY"
    else:
        metric = "none declared (smoke-only contract)"
        scope = "not applicable"
        state = "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE"
    return {
        "state": state,
        "mode": str(mode),
        "goal": str(product.get("goal", "unknown")),
        "input": str(product.get("input", "unknown")),
        "output": str(product.get("output", "unknown")),
        "artifacts": ", ".join(str(item) for item in artifacts) or "none declared",
        "metric": metric,
        "checks": ", ".join(checks) or "none declared",
        "claim_scope": scope,
    }


def group_block(lines: list[str], group_id: str, title: str, components: list[Component], prefix: str) -> None:
    lines.append(f'    subgraph {group_id}["{title}"]')
    if components:
        for component in components:
            lines.append(f'      {component.node_id}["{sanitize(component.label)}"]')
    else:
        lines.append(f'      {prefix}_none["(none)"]')
    lines.append("    end")


def render_architecture(agent: str, agent_relative: str, scan: Scan, view: dict[str, str]) -> str:
    runtime_title = (
        f"Product runtime: {agent_relative}/{scan.runtime_relative}"
        if scan.runtime_relative
        else "Product runtime: MISSING_RUNTIME_DIR"
    )
    lines: list[str] = [
        "%% GENERATED FILE - do not edit by hand.",
        "%% Regenerate with the agent-evaluation-loop-design skill's generate-agent-diagrams.py.",
        f"%% Agent: {agent}",
        f"%% Contract mode: {view['mode']}",
        f"%% Contract state: {view['state']}",
        f"%% Product goal: {sanitize(view['goal'])}",
        f"%% Product input: {sanitize(view['input'])}",
        f"%% Product output: {sanitize(view['output'])}",
        f"%% Functional checks: {sanitize(view['checks'])}",
        "flowchart TB",
        '  subgraph user["Human / User"]',
        f'    user_input["Input<br/>{shorten(view["input"])}"]',
        f'    user_output["Output<br/>{shorten(view["output"])}"]',
        "  end",
        f'  subgraph runtime["{sanitize(runtime_title)}"]',
    ]
    lines.append(
        '    rt_identity["identity.md<br/>product identity and instructions"]'
        if scan.identity
        else '    rt_identity["identity.md<br/>MISSING"]'
    )
    lines.append(
        '    rt_memory_policy["memory-policy.md<br/>durable memory boundary"]'
        if scan.memory_policy
        else '    rt_memory_policy["memory-policy.md<br/>MISSING"]'
    )
    group_block(lines, "grp_knowledge", "knowledge", scan.knowledge, "kn")
    group_block(lines, "grp_skills", "skills", scan.skills, "sk")
    group_block(lines, "grp_workflows", "workflows", scan.workflows, "wf")
    group_block(lines, "grp_tools", "tools (deterministic leaf adapters)", scan.tools, "tl")
    lines.append("  end")
    lines.extend(
        [
            '  subgraph execution["Execution layer (external — not product identity)"]',
            '    ex_backend["coding-agent backend<br/>supplied at run time"]',
            '    ex_provider["LLM provider<br/>credentials injected at run time"]',
            '    ex_model["model<br/>selected at run time"]',
            "  end",
            '  subgraph evidence["Evidence outputs"]',
            f'    ev_artifact["required artifacts<br/>{shorten(view["artifacts"], 90)}"]',
            '    ev_trajectory["scrubbed trajectory<br/>no credentials, no raw sessions"]',
            '    ev_verifier["verifier report<br/>functional pass or fail"]',
            "  end",
            '  subgraph development["Development-only (not product behavior)"]',
            f'    dv_contract["evaluation contract<br/>mode={sanitize(view["mode"])}, scope={sanitize(view["claim_scope"])}"]',
            '    dv_validation["validate-agent-evaluation.py<br/>structure and determinism"]',
            f'    dv_benchmark["benchmark and comparator<br/>primary metric {shorten(view["metric"], 70)}"]',
            '    dv_loop["run-agent-loop.sh<br/>stage runner, not an auto-optimizer"]',
            "  end",
            "  user_input --> rt_identity",
            "  rt_identity --> rt_memory_policy",
            "  rt_identity --> ex_backend",
            "  ex_backend --> ex_provider",
            "  ex_provider --> ex_model",
            "  ex_model --> user_output",
            "  rt_identity --> ev_artifact",
            "  ev_artifact --> ev_trajectory",
            "  ev_artifact --> ev_verifier",
            "  ev_verifier --> dv_benchmark",
            "  dv_contract --> dv_validation",
            "  dv_validation --> dv_benchmark",
            "  dv_benchmark --> dv_loop",
        ]
    )
    for component in scan.skills:
        lines.append(f"  rt_identity --> {component.node_id}")
    for component in scan.workflows:
        lines.append(f"  rt_identity --> {component.node_id}")
    for component in scan.knowledge:
        lines.append(f"  {component.node_id} --> rt_identity")
    for component in scan.tools:
        lines.append(f"  {component.node_id} --> ev_artifact")
    if scan.problems:
        for index, problem in enumerate(scan.problems, start=1):
            lines.append(f"%% Scan problem {index}: {sanitize(problem)}")
    return "\n".join(lines) + "\n"


def render_optimization(agent: str, view: dict[str, str]) -> str:
    lines: list[str] = [
        "%% GENERATED FILE - do not edit by hand.",
        "%% Regenerate with the agent-evaluation-loop-design skill's generate-agent-diagrams.py.",
        f"%% Agent: {agent}",
        f"%% Contract state: {view['state']}",
        "stateDiagram-v2",
        "  direction TB",
    ]
    for state in STATES:
        lines.append(f"  state \"{state}\" as {state}")
    for source, target, guard in TRANSITIONS:
        lines.append(f"  {source} --> {target} : {guard}")
    lines.extend(
        [
            "  state SELF_BOOTSTRAP_ADVANCED {",
            "    SB_BASE_COMMITTED --> SB_DISTINCT_CLEAN_CANDIDATE : distinct clean descendant revision",
            "    SB_DISTINCT_CLEAN_CANDIDATE --> SB_RUN_BASE_EVALUATOR : evaluator comes from the immutable base archive",
            "    SB_RUN_BASE_EVALUATOR --> SB_CHECK_OBSERVABLE_DELTA : structure and determinism preserved",
            "    SB_CHECK_OBSERVABLE_DELTA --> SB_HUMAN_REVIEW : pre-declared delta observed",
            "    SB_CHECK_OBSERVABLE_DELTA --> SB_BLOCKED : evaluator, fixture or protected path changed",
            "    SB_CHECK_OBSERVABLE_DELTA --> SB_REJECTED : invariant lost or no observable delta",
            "  }",
            "  note right of COMPARE_WITH_CURRENT_BEST",
            "    subject.definition_revision differs between current best and candidate by design.",
            "    That difference is the premise of the comparison, never a baseline invalidation.",
            "    Only the canonical condition manifest defines comparability; a run-affecting input",
            "    that cannot be recorded in the manifest blocks the comparison instead of passing.",
            "  end note",
            "  note right of CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE",
            "    A benchmark-local acceptance recommendation only. The comparator never promotes",
            "    and never writes the current best; ACCEPTED_AS_CURRENT_BEST needs a separate",
            "    promotion gate binding the result hash, the manifest hash and a human decision.",
            "  end note",
            "  note right of GENERALIZATION_REQUIRED",
            "    A product-general claim needs an independent holdout or canary that was frozen",
            "    before candidate selection and never used for tuning, plus human domain review.",
            "  end note",
            "  note right of ENVIRONMENT_BLOCKED",
            "    Environment and evaluation blocks update nothing. A provider or infrastructure",
            "    failure is not a regression and not an improvement; fix that layer and rerun",
            "    the same candidate.",
            "  end note",
            "  note right of BASELINE_INVALIDATED",
            "    The evaluation conditions changed. Re-measure the current best under the new",
            "    condition identity before comparing anything else.",
            "  end note",
            "  note right of STOPPED",
            "    STOPPED needs a recorded reason: goal reached, N consecutive candidates without",
            "    material improvement, budget or wall-clock exhausted, or a human stop.",
            "  end note",
            "  note right of SELF_BOOTSTRAP_ADVANCED",
            "    Advanced path for optimizing the design skill itself. The self-bootstrap",
            "    candidate runs against the fixed fixture and the base evaluator and cannot",
            "    relax the evaluator, the fixtures or the expected results.",
            "  end note",
            "  note right of SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE",
            "    A smoke or infrastructure pass is never performance evidence. A smoke-only",
            "    contract can render these diagrams but can never accept an improvement.",
            "  end note",
            "  note right of CONTRACT_DESIGNED",
            f"    Current contract state for {agent}: mode {sanitize(view['mode'])} gives {view['state']}.",
            "  end note",
            "  [*] --> INTENT_DEFINED",
            "  STOPPED --> [*]",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", default="hewo", help="Agent name (default: hewo)")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="repository root (default: cwd)")
    parser.add_argument("--agent-root", type=Path, help="default: <repo-root>/src/<agent>")
    parser.add_argument("--contract", type=Path, help="default: <agent-root>/<development_dir>/evaluation-contract.json")
    parser.add_argument("--output-dir", type=Path, help="default: <repo-root>")
    parser.add_argument("--readme", type=Path, help="default: <repo-root>/README.md")
    parser.add_argument("--no-readme", action="store_true", help="write only the .mmd files")
    parser.add_argument(
        "--init-readme",
        action="store_true",
        help="insert both managed blocks once, only when neither marker exists yet",
    )
    parser.add_argument("--check", action="store_true", help="compare only; write nothing and fail on drift")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    agent_root = (args.agent_root or repo_root / "src" / args.agent).resolve()
    output_dir = (args.output_dir or repo_root).resolve()
    if not agent_root.is_dir():
        print(f"ERROR agent root does not exist: {agent_root}", file=sys.stderr)
        return 2
    if not output_dir.is_dir():
        print(f"ERROR output directory does not exist: {output_dir}", file=sys.stderr)
        return 2

    manifest_path = agent_root / "agent.yaml"
    manifest: dict[str, str] = {}
    scan_problems: list[str] = []
    if manifest_path.is_file():
        try:
            manifest = lib.parse_agent_yaml(manifest_path)
        except lib.DocumentError as exc:
            scan_problems.append(str(exc))
    else:
        scan_problems.append(f"agent.yaml is missing: {manifest_path}")

    scan = scan_runtime(agent_root, manifest)
    scan.problems = scan_problems + scan.problems

    contract_path = args.contract
    contract_problems: list[str] = []
    contract: Any = None
    if contract_path is None:
        development = manifest.get("development_dir")
        if not development:
            contract_problems.append("agent.yaml does not declare development_dir")
        else:
            contract_path = agent_root / development / "evaluation-contract.json"
    if contract_path is not None:
        if not contract_path.is_file():
            contract_problems.append(f"evaluation contract is missing: {contract_path}")
        else:
            try:
                contract = lib.load_json_exact(contract_path)
            except lib.DocumentError as exc:
                contract_problems.append(str(exc))
    view = contract_view(contract, contract_problems)

    try:
        agent_relative = agent_root.relative_to(repo_root).as_posix()
    except ValueError:
        agent_relative = agent_root.name

    rendered = {
        ARCHITECTURE_BASENAME: render_architecture(args.agent, agent_relative, scan, view),
        OPTIMIZATION_BASENAME: render_optimization(args.agent, view),
    }

    drift: list[str] = []
    for basename, text in rendered.items():
        target = output_dir / basename
        if args.check:
            if not target.is_file():
                drift.append(f"{basename} does not exist")
            elif target.read_text(encoding="utf-8") != text:
                drift.append(f"{basename} differs from the generated content")
        else:
            lib.atomic_write_text(target, text)
            # Generated sources are committed and read by humans; the atomic
            # temp-file write would otherwise leave them 0600.
            os.chmod(target, 0o644)

    readme_path = None if args.no_readme else (args.readme or repo_root / "README.md")
    readme_status = "skipped"
    if readme_path is not None:
        if not readme_path.is_file():
            print(f"ERROR README does not exist: {readme_path}", file=sys.stderr)
            return 2
        current = readme_path.read_text(encoding="utf-8")
        try:
            if args.init_readme:
                updated = insert_initial_blocks(current, rendered, (ARCHITECTURE_BASENAME, OPTIMIZATION_BASENAME))
            else:
                updated = apply_blocks(current, rendered)
        except ReadmeError as exc:
            print(f"ERROR README managed blocks: {exc}", file=sys.stderr)
            return 1
        if args.check:
            if updated != current:
                drift.append("README managed blocks differ from the generated content")
            readme_status = "checked"
        elif updated != current:
            lib.atomic_write_text(readme_path, updated)
            readme_status = "updated"
        else:
            readme_status = "unchanged"

    for problem in scan.problems:
        print(f"WARN scan: {problem}", file=sys.stderr)
    for problem in contract_problems:
        print(f"WARN contract: {problem}", file=sys.stderr)

    if args.check:
        if drift:
            for item in drift:
                print(f"ERROR drift: {item}", file=sys.stderr)
            return 1
        print(f"No drift for {args.agent}: {ARCHITECTURE_BASENAME}, {OPTIMIZATION_BASENAME}, README={readme_status}")
        return 0

    print(f"Wrote {output_dir / ARCHITECTURE_BASENAME}")
    print(f"Wrote {output_dir / OPTIMIZATION_BASENAME}")
    print(f"README: {readme_status}")
    print(f"Contract state: {view['state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
