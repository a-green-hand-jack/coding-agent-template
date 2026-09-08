#!/usr/bin/env python3
"""Compare a candidate evaluation result against the current best.

Thin, deterministic protocol implementing the precedence in
``../references/evaluation-contract.md``. It does not run a benchmark, does not
call a provider, does not read credentials, and never writes a current best.

Exit codes:
  0  CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE
  10 CANDIDATE_REJECTED
  20 DESIGN_INCOMPLETE | FUNCTIONAL_BASELINE_MISSING | SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE
  30 BASELINE_INVALIDATED
  40 ENVIRONMENT_BLOCKED
  41 EVALUATION_BLOCKED
  42 GENERALIZATION_REQUIRED
  2  CLI or schema malformed
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _evaluation_lib as lib  # noqa: E402

EXIT_CODES = {
    "CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE": 0,
    "CANDIDATE_REJECTED": 10,
    "DESIGN_INCOMPLETE": 20,
    "FUNCTIONAL_BASELINE_MISSING": 20,
    "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE": 20,
    "BASELINE_INVALIDATED": 30,
    "ENVIRONMENT_BLOCKED": 40,
    "EVALUATION_BLOCKED": 41,
    "GENERALIZATION_REQUIRED": 42,
}

RUN_STATUS = {"completed", "blocked"}
FAILURE_CLASS = {"none", "credential", "provider", "infrastructure", "benchmark-verifier", "evidence"}
FUNCTIONAL_STATUS = {"pass", "fail", "unknown"}
ENVIRONMENT_CLASSES = {"credential", "provider", "infrastructure"}
EVALUATION_CLASSES = {"benchmark-verifier", "evidence"}
EVIDENCE_KINDS = {"artifact", "verifier-report", "scrubbed-trajectory"}
DIRECTIONS = {"higher-is-better", "lower-is-better"}


# --------------------------------------------------------------------------
# small typed accessors
# --------------------------------------------------------------------------


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(lib.HEX64.match(value))


def is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def mapping(document: Any, key: str) -> dict:
    value = document.get(key) if isinstance(document, dict) else None
    return value if isinstance(value, dict) else {}


# --------------------------------------------------------------------------
# contract schema
# --------------------------------------------------------------------------


def validate_contract(document: Any) -> list[str]:
    problems: list[str] = []
    if not isinstance(document, dict):
        return ["contract is not a JSON object"]
    if document.get("schema_version") != 1:
        problems.append("contract.schema_version must be the integer 1")
    if not is_text(document.get("agent")):
        problems.append("contract.agent must be a non-empty string")
    mode = document.get("mode")
    if mode not in {"performance", "infrastructure-smoke-only"}:
        problems.append("contract.mode must be 'performance' or 'infrastructure-smoke-only'")
    for key in ("contract_revision", "metric_policy_revision"):
        if not is_text(document.get(key)):
            problems.append(f"contract.{key} must be a non-empty string")
    for key in ("goal", "input", "output"):
        if not is_text(mapping(document, "product").get(key)):
            problems.append(f"contract.product.{key} must be a non-empty string")
    if "baseline" in document or "current_best" in document:
        problems.append("contract must not embed a baseline or current-best pointer")

    functional = mapping(document, "functional_contract")
    checks = functional.get("checks")
    if not isinstance(checks, list) or not checks:
        problems.append("contract.functional_contract.checks must be a non-empty array")
    else:
        identifiers = []
        for index, item in enumerate(checks):
            if not isinstance(item, dict):
                problems.append(f"contract.functional_contract.checks[{index}] must be an object")
                continue
            for key in ("id", "description", "source"):
                if not is_text(item.get(key)):
                    problems.append(f"contract.functional_contract.checks[{index}].{key} must be a non-empty string")
            identifiers.append(item.get("id"))
        if len(set(identifiers)) != len(identifiers):
            problems.append("contract.functional_contract.checks ids must be unique")
    artifacts = functional.get("required_artifacts")
    if not isinstance(artifacts, list) or not artifacts or not all(is_text(item) for item in artifacts):
        problems.append("contract.functional_contract.required_artifacts must be a non-empty array of strings")

    if mode != "performance":
        return problems

    benchmark = mapping(document, "benchmark")
    for key in ("task_set", "revision", "verifier", "verifier_revision"):
        if not is_text(benchmark.get(key)):
            problems.append(f"contract.benchmark.{key} must be a non-empty string")
    environment = mapping(document, "environment")
    for key in ("backend", "provider", "model", "runtime"):
        if not is_text(environment.get(key)):
            problems.append(f"contract.environment.{key} must be a non-empty string")
    if not is_integer(environment.get("repetitions")) or environment.get("repetitions", 0) < 1:
        problems.append("contract.environment.repetitions must be an integer >= 1")
    if environment.get("aggregation") != "mean":
        problems.append("contract.environment.aggregation must be 'mean' in v1")

    metrics = mapping(document, "metrics")
    primary = mapping(metrics, "primary")
    if not is_text(primary.get("name")):
        problems.append("contract.metrics.primary.name must be a non-empty string")
    if primary.get("direction") not in DIRECTIONS:
        problems.append("contract.metrics.primary.direction must be higher-is-better or lower-is-better")
    if not is_text(primary.get("unit")):
        problems.append("contract.metrics.primary.unit must be a non-empty string")
    secondary = metrics.get("secondary")
    secondary_names: list[str] = []
    if not isinstance(secondary, list):
        problems.append("contract.metrics.secondary must be an array")
    else:
        for index, item in enumerate(secondary):
            if not isinstance(item, dict):
                problems.append(f"contract.metrics.secondary[{index}] must be an object")
                continue
            if not is_text(item.get("name")):
                problems.append(f"contract.metrics.secondary[{index}].name must be a non-empty string")
            else:
                secondary_names.append(item["name"])
            if item.get("direction") not in DIRECTIONS:
                problems.append(f"contract.metrics.secondary[{index}].direction is invalid")
            if not is_text(item.get("unit")):
                problems.append(f"contract.metrics.secondary[{index}].unit must be a non-empty string")

    acceptance = mapping(document, "acceptance")
    try:
        delta = lib.as_decimal(acceptance.get("minimum_primary_delta"), "acceptance.minimum_primary_delta")
        if delta < 0:
            problems.append("contract.acceptance.minimum_primary_delta must be >= 0")
    except lib.DocumentError as exc:
        problems.append(f"contract.{exc}")
    regressions = acceptance.get("max_secondary_regression")
    if not isinstance(regressions, dict):
        problems.append("contract.acceptance.max_secondary_regression must be an object")
    else:
        for name in secondary_names:
            if name not in regressions:
                problems.append(f"contract.acceptance.max_secondary_regression is missing '{name}'")
        for name, value in regressions.items():
            try:
                if lib.as_decimal(value, f"max_secondary_regression.{name}") < 0:
                    problems.append(f"contract.acceptance.max_secondary_regression.{name} must be >= 0")
            except lib.DocumentError as exc:
                problems.append(f"contract.{exc}")
    if not isinstance(acceptance.get("require_functional_pass"), bool):
        problems.append("contract.acceptance.require_functional_pass must be a boolean")

    stop = document.get("stop_conditions")
    if not isinstance(stop, list) or not stop or not all(is_text(item) for item in stop):
        problems.append("contract.stop_conditions must be a non-empty array of strings")

    policy = mapping(document, "evidence_policy")
    if policy.get("scrubbed_only") is not True:
        problems.append("contract.evidence_policy.scrubbed_only must be true in v1")
    kinds = policy.get("required_kinds")
    if not isinstance(kinds, list) or not kinds or not set(kinds) <= EVIDENCE_KINDS:
        problems.append("contract.evidence_policy.required_kinds must be a non-empty subset of the evidence kinds")
    producers = policy.get("approved_producers")
    if not isinstance(producers, list) or not producers:
        problems.append("contract.evidence_policy.approved_producers must be a non-empty array")
    else:
        for index, item in enumerate(producers):
            if not isinstance(item, dict) or not is_text(item.get("id")) or not is_text(item.get("revision")):
                problems.append(f"contract.evidence_policy.approved_producers[{index}] needs id and revision")

    generalization = mapping(document, "generalization")
    scope = generalization.get("claim_scope")
    if scope not in {"benchmark-local", "product-general"}:
        problems.append("contract.generalization.claim_scope must be benchmark-local or product-general")
    if not isinstance(generalization.get("human_domain_review_required"), bool):
        problems.append("contract.generalization.human_domain_review_required must be a boolean")
    holdout = generalization.get("holdout")
    if scope == "product-general":
        if not isinstance(holdout, dict):
            problems.append("contract.generalization.holdout must be an object when claim_scope is product-general")
        else:
            if not is_text(holdout.get("task_set_revision")):
                problems.append("contract.generalization.holdout.task_set_revision must be a non-empty string")
            if not is_hex64(holdout.get("task_input_sha256")):
                problems.append("contract.generalization.holdout.task_input_sha256 must be 64 hex characters")
            for key in ("not_used_for_tuning", "frozen_before_candidate_selection", "human_domain_review_required"):
                if holdout.get(key) is not True:
                    problems.append(f"contract.generalization.holdout.{key} must be true")
            try:
                lib.as_decimal(holdout.get("minimum_primary_value"), "holdout.minimum_primary_value")
            except lib.DocumentError as exc:
                problems.append(f"contract.generalization.{exc}")
            if holdout.get("task_set_revision") == benchmark.get("revision"):
                problems.append("contract.generalization.holdout.task_set_revision must differ from the benchmark revision")
    elif holdout is not None and not isinstance(holdout, dict):
        problems.append("contract.generalization.holdout must be null or an object")
    return problems


# --------------------------------------------------------------------------
# condition manifest
# --------------------------------------------------------------------------

EXECUTION_KEYS = (
    ("backend", is_text),
    ("provider", is_text),
    ("model", is_text),
    ("runtime", is_text),
    ("image_digest", is_text),
    ("tool_versions", lambda value: isinstance(value, dict)),
    ("request_parameters", lambda value: isinstance(value, dict)),
    ("sampling", lambda value: isinstance(value, dict)),
    ("seed", is_text),
    ("retry_policy", lambda value: isinstance(value, dict)),
    ("timeout_seconds", is_integer),
    ("locale", is_text),
    ("timezone", is_text),
)


def validate_manifest(document: Any) -> list[str]:
    problems: list[str] = []
    if not isinstance(document, dict):
        return ["condition manifest is not a JSON object"]
    if document.get("schema_version") != 1:
        problems.append("manifest.schema_version must be the integer 1")
    contract = mapping(document, "contract")
    if not is_text(contract.get("revision")):
        problems.append("manifest.contract.revision must be a non-empty string")
    if not is_hex64(contract.get("sha256")):
        problems.append("manifest.contract.sha256 must be 64 hex characters")
    benchmark = mapping(document, "benchmark")
    if not is_text(benchmark.get("task_set_revision")):
        problems.append("manifest.benchmark.task_set_revision must be a non-empty string")
    if not is_hex64(benchmark.get("task_input_sha256")):
        problems.append("manifest.benchmark.task_input_sha256 must be 64 hex characters")
    if not is_text(benchmark.get("holdout_policy_revision")):
        problems.append("manifest.benchmark.holdout_policy_revision must be a non-empty string")
    verifier = mapping(document, "verifier")
    for key in ("id", "revision"):
        if not is_text(verifier.get(key)):
            problems.append(f"manifest.verifier.{key} must be a non-empty string")
    if not is_hex64(verifier.get("source_sha256")):
        problems.append("manifest.verifier.source_sha256 must be 64 hex characters")
    policy = mapping(document, "metric_policy")
    if not is_text(policy.get("revision")):
        problems.append("manifest.metric_policy.revision must be a non-empty string")
    if not is_hex64(policy.get("definition_sha256")):
        problems.append("manifest.metric_policy.definition_sha256 must be 64 hex characters")
    execution = mapping(document, "execution")
    for key, predicate in EXECUTION_KEYS:
        if key not in execution:
            problems.append(f"manifest.execution.{key} is required even when it is a default")
        elif not predicate(execution[key]):
            problems.append(f"manifest.execution.{key} has the wrong type")
    sampling = mapping(document, "sampling")
    if not is_integer(sampling.get("repetitions")) or sampling.get("repetitions", 0) < 1:
        problems.append("manifest.sampling.repetitions must be an integer >= 1")
    if sampling.get("aggregation") != "mean":
        problems.append("manifest.sampling.aggregation must be 'mean' in v1")
    return problems


def manifest_projection(manifest: dict, relative: str, digest: str) -> dict:
    execution = mapping(manifest, "execution")
    return {
        "condition_manifest_path": relative,
        "condition_manifest_sha256": digest,
        "contract_revision": mapping(manifest, "contract").get("revision"),
        "contract_sha256": mapping(manifest, "contract").get("sha256"),
        "benchmark_revision": mapping(manifest, "benchmark").get("task_set_revision"),
        "verifier_revision": mapping(manifest, "verifier").get("revision"),
        "metric_policy_revision": mapping(manifest, "metric_policy").get("revision"),
        "backend": execution.get("backend"),
        "provider": execution.get("provider"),
        "model": execution.get("model"),
        "runtime": execution.get("runtime"),
        "repetitions": mapping(manifest, "sampling").get("repetitions"),
        "aggregation": mapping(manifest, "sampling").get("aggregation"),
    }


# --------------------------------------------------------------------------
# results
# --------------------------------------------------------------------------


class LoadedResult:
    """A result document plus its resolved manifest and integrity findings."""

    def __init__(self, role: str, path: Path) -> None:
        self.role = role
        self.path = path
        self.directory = path.parent
        self.document: dict = {}
        self.manifest: dict = {}
        self.manifest_relative = ""
        self.manifest_sha256 = ""
        self.manifest_bytes = b""
        self.structural: list[str] = []
        self.evidence: list[str] = []

    @property
    def samples(self) -> list[dict]:
        value = self.document.get("samples")
        return value if isinstance(value, list) else []

    def blocked_classes(self) -> set[str]:
        classes = set()
        for sample in self.samples:
            if isinstance(sample, dict) and sample.get("run_status") == "blocked":
                classes.add(sample.get("failure_class"))
        return classes


def load_result(role: str, path: Path, contract: dict, contract_sha: str) -> LoadedResult:
    loaded = LoadedResult(role, path)
    try:
        resolved = lib.safe_input_file(path)
    except lib.PathSafetyError as exc:
        loaded.structural.append(f"{role}: {exc}")
        return loaded
    loaded.path = resolved
    loaded.directory = resolved.parent
    try:
        document = lib.load_json_exact(resolved)
    except lib.DocumentError as exc:
        loaded.structural.append(f"{role}: {exc}")
        return loaded
    if not isinstance(document, dict):
        loaded.structural.append(f"{role}: result is not a JSON object")
        return loaded
    loaded.document = document

    if document.get("schema_version") != 1:
        loaded.structural.append(f"{role}: result.schema_version must be the integer 1")
    if document.get("role") != role:
        loaded.structural.append(f"{role}: result.role must be '{role}', got {document.get('role')!r}")
    if not is_text(document.get("run_id")):
        loaded.structural.append(f"{role}: result.run_id must be a non-empty string")
    if not is_text(mapping(document, "subject").get("definition_revision")):
        loaded.structural.append(f"{role}: result.subject.definition_revision must be a non-empty string")

    identity = mapping(document, "condition_identity")
    if not identity:
        loaded.structural.append(f"{role}: result.condition_identity is missing")
        return loaded
    relative = identity.get("condition_manifest_path")
    digest = identity.get("condition_manifest_sha256")
    if document.get("condition_manifest_path") != relative:
        loaded.structural.append(f"{role}: top-level condition_manifest_path disagrees with condition_identity")
    if document.get("condition_manifest_sha256") != digest:
        loaded.structural.append(f"{role}: top-level condition_manifest_sha256 disagrees with condition_identity")
    if not is_hex64(digest):
        loaded.structural.append(f"{role}: condition_manifest_sha256 must be 64 hex characters")
    try:
        manifest_path = lib.safe_child_path(loaded.directory, relative if isinstance(relative, str) else "")
    except lib.PathSafetyError as exc:
        loaded.structural.append(f"{role}: condition manifest path is unsafe: {exc}")
        return loaded
    try:
        manifest = lib.load_json_exact(manifest_path)
    except lib.DocumentError as exc:
        loaded.structural.append(f"{role}: condition manifest {exc}")
        return loaded
    problems = validate_manifest(manifest)
    loaded.structural.extend(f"{role}: {item}" for item in problems)
    if problems:
        return loaded
    loaded.manifest = manifest
    loaded.manifest_relative = relative
    loaded.manifest_bytes = lib.canonical_bytes(manifest)
    loaded.manifest_sha256 = lib.sha256_hex(loaded.manifest_bytes)
    if loaded.manifest_sha256 != digest:
        loaded.structural.append(
            f"{role}: condition_manifest_sha256 does not match the manifest's canonical bytes"
        )
    if mapping(manifest, "contract").get("sha256") != contract_sha:
        loaded.structural.append(f"{role}: manifest does not pin the supplied contract's hash")

    expected = manifest_projection(manifest, relative, loaded.manifest_sha256)
    for key, value in expected.items():
        if identity.get(key) != value:
            loaded.structural.append(
                f"{role}: condition_identity.{key} disagrees with the manifest ({identity.get(key)!r} != {value!r})"
            )
    if set(identity) != set(expected):
        extra = sorted(set(identity) - set(expected))
        missing = sorted(set(expected) - set(identity))
        if extra:
            loaded.structural.append(f"{role}: condition_identity has unexpected fields: {extra}")
        if missing:
            loaded.structural.append(f"{role}: condition_identity is missing fields: {missing}")

    # Contract environment must agree with the manifest's execution/sampling.
    environment = mapping(contract, "environment")
    execution = mapping(manifest, "execution")
    for key in ("backend", "provider", "model", "runtime"):
        if environment.get(key) != execution.get(key):
            loaded.structural.append(
                f"{role}: contract.environment.{key} disagrees with the manifest execution"
            )
    sampling = mapping(manifest, "sampling")
    if environment.get("repetitions") != sampling.get("repetitions"):
        loaded.structural.append(f"{role}: contract.environment.repetitions disagrees with the manifest")
    if environment.get("aggregation") != sampling.get("aggregation"):
        loaded.structural.append(f"{role}: contract.environment.aggregation disagrees with the manifest")

    check_samples(loaded, contract)
    return loaded


def check_samples(loaded: LoadedResult, contract: dict) -> None:
    role = loaded.role
    samples = loaded.document.get("samples")
    repetitions = mapping(contract, "environment").get("repetitions")
    if not isinstance(samples, list) or not samples:
        loaded.structural.append(f"{role}: result.samples must be a non-empty array")
        return
    if is_integer(repetitions) and len(samples) != repetitions:
        loaded.structural.append(
            f"{role}: result has {len(samples)} samples but the contract requires {repetitions}"
        )
    identifiers: list[Any] = []
    policy = mapping(contract, "evidence_policy")
    required_kinds = set(policy.get("required_kinds") or [])
    approved = {
        (item.get("id"), item.get("revision"))
        for item in policy.get("approved_producers") or []
        if isinstance(item, dict)
    }
    secondary_names = [
        item.get("name")
        for item in mapping(contract, "metrics").get("secondary") or []
        if isinstance(item, dict)
    ]

    for index, sample in enumerate(samples):
        label = f"{role}: samples[{index}]"
        if not isinstance(sample, dict):
            loaded.structural.append(f"{label} must be an object")
            continue
        identifiers.append(sample.get("sample_id"))
        if not is_text(sample.get("sample_id")):
            loaded.structural.append(f"{label}.sample_id must be a non-empty string")
        status = sample.get("run_status")
        failure = sample.get("failure_class")
        functional = sample.get("functional_status")
        if status not in RUN_STATUS:
            loaded.structural.append(f"{label}.run_status must be completed or blocked")
            continue
        if failure not in FAILURE_CLASS:
            loaded.structural.append(f"{label}.failure_class is not in the taxonomy")
            continue
        if functional not in FUNCTIONAL_STATUS:
            loaded.structural.append(f"{label}.functional_status is not in the taxonomy")
            continue
        if status == "completed" and failure != "none":
            loaded.structural.append(f"{label} is completed but declares failure_class {failure!r}")
        if status == "blocked" and failure == "none":
            loaded.structural.append(f"{label} is blocked but declares failure_class 'none'")

        if status == "blocked":
            if sample.get("primary_value") is not None:
                loaded.structural.append(f"{label}.primary_value must be null on a blocked sample")
            if sample.get("secondary_values") not in ({}, None):
                loaded.structural.append(f"{label}.secondary_values must be empty on a blocked sample")
            continue

        try:
            lib.as_decimal(sample.get("primary_value"), f"{label}.primary_value")
        except lib.DocumentError as exc:
            loaded.structural.append(str(exc))
        values = sample.get("secondary_values")
        if not isinstance(values, dict):
            loaded.structural.append(f"{label}.secondary_values must be an object")
        else:
            for name in secondary_names:
                if name not in values:
                    loaded.evidence.append(f"{label}.secondary_values is missing '{name}'")
                else:
                    try:
                        lib.as_decimal(values[name], f"{label}.secondary_values.{name}")
                    except lib.DocumentError as exc:
                        loaded.evidence.append(str(exc))

        entries = sample.get("evidence")
        if not isinstance(entries, list) or not entries:
            loaded.evidence.append(f"{label}.evidence must be a non-empty array on a completed sample")
            continue
        seen_kinds = set()
        for position, item in enumerate(entries):
            entry_label = f"{label}.evidence[{position}]"
            if not isinstance(item, dict):
                loaded.evidence.append(f"{entry_label} must be an object")
                continue
            kind = item.get("kind")
            if kind not in EVIDENCE_KINDS:
                loaded.evidence.append(f"{entry_label}.kind is not a known evidence kind")
            else:
                seen_kinds.add(kind)
            if not is_hex64(item.get("sha256")):
                loaded.evidence.append(f"{entry_label}.sha256 must be 64 hex characters")
            producer = (item.get("producer"), item.get("producer_revision"))
            if producer not in approved:
                loaded.evidence.append(
                    f"{entry_label} producer {producer!r} is not in the contract's approved_producers"
                )
            try:
                target = lib.safe_child_path(loaded.directory, item.get("path") or "")
            except lib.PathSafetyError as exc:
                loaded.evidence.append(f"{entry_label}.path is unsafe: {exc}")
                continue
            actual = lib.file_sha256(target)
            if actual != item.get("sha256"):
                loaded.evidence.append(f"{entry_label} sha256 does not match the file bytes")
        missing_kinds = sorted(required_kinds - seen_kinds)
        if missing_kinds:
            loaded.evidence.append(f"{label} is missing required evidence kinds {missing_kinds}")

    if len(set(identifiers)) != len(identifiers):
        loaded.structural.append(f"{role}: sample_id values must be unique")

    check_aggregate(loaded, contract)


def check_aggregate(loaded: LoadedResult, contract: dict) -> None:
    samples = [item for item in loaded.samples if isinstance(item, dict)]
    aggregate = loaded.document.get("aggregate")
    if not isinstance(aggregate, dict):
        loaded.structural.append(f"{loaded.role}: result.aggregate must be an object")
        return
    completed = [item for item in samples if item.get("run_status") == "completed"]
    if len(completed) != len(samples):
        if aggregate.get("primary_value") is not None or aggregate.get("secondary_values") not in ({}, None):
            loaded.structural.append(
                f"{loaded.role}: result.aggregate must be null/empty while a sample is blocked"
            )
        return
    try:
        recomputed = lib.exact_mean(
            [lib.as_decimal(item.get("primary_value"), "primary_value") for item in completed]
        )
    except lib.DocumentError:
        return
    try:
        declared = lib.as_decimal(aggregate.get("primary_value"), "aggregate.primary_value")
    except lib.DocumentError as exc:
        loaded.evidence.append(f"{loaded.role}: {exc}")
        return
    if declared != recomputed:
        loaded.evidence.append(
            f"{loaded.role}: self-reported aggregate.primary_value {declared} != recomputed mean {recomputed}"
        )
    declared_secondary = aggregate.get("secondary_values")
    if not isinstance(declared_secondary, dict):
        loaded.evidence.append(f"{loaded.role}: aggregate.secondary_values must be an object")
        return
    for name in [
        item.get("name")
        for item in mapping(contract, "metrics").get("secondary") or []
        if isinstance(item, dict)
    ]:
        try:
            expected = lib.exact_mean(
                [
                    lib.as_decimal((item.get("secondary_values") or {}).get(name), name)
                    for item in completed
                ]
            )
        except lib.DocumentError:
            continue
        if name not in declared_secondary:
            loaded.evidence.append(f"{loaded.role}: aggregate.secondary_values is missing '{name}'")
        else:
            try:
                if lib.as_decimal(declared_secondary[name], name) != expected:
                    loaded.evidence.append(
                        f"{loaded.role}: self-reported aggregate.secondary_values.{name} != recomputed mean {expected}"
                    )
            except lib.DocumentError as exc:
                loaded.evidence.append(f"{loaded.role}: {exc}")


def validate_promotion(loaded: LoadedResult) -> list[str]:
    promotion = loaded.document.get("promotion")
    if not isinstance(promotion, dict):
        return ["current best has no promotion record"]
    problems = []
    if promotion.get("status") != "promoted":
        problems.append("promotion.status must be 'promoted'")
    expected = lib.promoted_result_sha256(loaded.document)
    if promotion.get("promoted_result_sha256") != expected:
        problems.append("promotion.promoted_result_sha256 does not match the result document")
    producer = mapping(promotion, "approved_producer")
    if not is_text(producer.get("id")) or not is_text(producer.get("revision")):
        problems.append("promotion.approved_producer needs id and revision")
    if not is_text(promotion.get("decision_reference")):
        problems.append("promotion.decision_reference must be a non-empty string")
    return problems


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------


def primary_mean(loaded: LoadedResult) -> Decimal:
    completed = [item for item in loaded.samples if isinstance(item, dict) and item.get("run_status") == "completed"]
    return lib.exact_mean([lib.as_decimal(item.get("primary_value"), "primary_value") for item in completed])


def secondary_mean(loaded: LoadedResult, name: str) -> Decimal:
    completed = [item for item in loaded.samples if isinstance(item, dict) and item.get("run_status") == "completed"]
    return lib.exact_mean(
        [lib.as_decimal((item.get("secondary_values") or {}).get(name), name) for item in completed]
    )


def compare_metrics(contract: dict, best: LoadedResult, candidate: LoadedResult) -> tuple[list[str], dict]:
    metrics = mapping(contract, "metrics")
    acceptance = mapping(contract, "acceptance")
    primary = mapping(metrics, "primary")
    direction = primary.get("direction")
    minimum = lib.as_decimal(acceptance.get("minimum_primary_delta"), "minimum_primary_delta")
    best_mean = primary_mean(best)
    candidate_mean = primary_mean(candidate)
    improvement = candidate_mean - best_mean if direction == "higher-is-better" else best_mean - candidate_mean
    detail = {
        "primary_metric": primary.get("name"),
        "direction": direction,
        "current_best_mean": lib.decimal_text(best_mean),
        "candidate_mean": lib.decimal_text(candidate_mean),
        "improvement": lib.decimal_text(improvement),
        "minimum_primary_delta": lib.decimal_text(minimum),
        "secondary": {},
    }
    problems: list[str] = []
    if improvement < minimum:
        problems.append(
            f"primary metric improvement {lib.decimal_text(improvement)} is below the required "
            f"{lib.decimal_text(minimum)}"
        )
    allowed = acceptance.get("max_secondary_regression") or {}
    for item in metrics.get("secondary") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        best_value = secondary_mean(best, name)
        candidate_value = secondary_mean(candidate, name)
        regression = (
            candidate_value - best_value
            if item.get("direction") == "lower-is-better"
            else best_value - candidate_value
        )
        budget = lib.as_decimal(allowed.get(name), f"max_secondary_regression.{name}")
        detail["secondary"][name] = {
            "direction": item.get("direction"),
            "current_best_mean": lib.decimal_text(best_value),
            "candidate_mean": lib.decimal_text(candidate_value),
            "regression": lib.decimal_text(regression),
            "allowed_regression": lib.decimal_text(budget),
        }
        if regression > budget:
            problems.append(
                f"secondary metric '{name}' regressed by {lib.decimal_text(regression)}, "
                f"above the allowed {lib.decimal_text(budget)}"
            )
    return problems, detail


def check_generalization(contract: dict, candidate: LoadedResult) -> list[str]:
    generalization = mapping(contract, "generalization")
    if generalization.get("claim_scope") != "product-general":
        return []
    policy = mapping(generalization, "holdout")
    declared = mapping(candidate.document, "generalization")
    holdout = declared.get("holdout")
    if not isinstance(holdout, dict):
        return ["contract claims product-general scope but the candidate declares no holdout result"]
    problems: list[str] = []
    if holdout.get("task_set_revision") != policy.get("task_set_revision"):
        problems.append("holdout task_set_revision does not match the contract holdout policy")
    if holdout.get("task_input_sha256") != policy.get("task_input_sha256"):
        problems.append("holdout task_input_sha256 does not match the contract holdout policy")
    benchmark = mapping(contract, "benchmark")
    if holdout.get("task_set_revision") == benchmark.get("revision"):
        problems.append("holdout shares the benchmark task-set revision and is not independent")
    if holdout.get("verifier_revision") != benchmark.get("verifier_revision"):
        problems.append("holdout verifier_revision does not match the contract verifier")
    if holdout.get("metric_policy_revision") != contract.get("metric_policy_revision"):
        problems.append("holdout metric_policy_revision does not match the contract")
    for key in ("not_used_for_tuning", "frozen_before_candidate_selection"):
        if holdout.get(key) is not True:
            problems.append(f"holdout.{key} must be true")
    if holdout.get("functional_status") != "pass":
        problems.append("holdout functional_status must be pass")
    try:
        value = lib.as_decimal(holdout.get("primary_value"), "holdout.primary_value")
        threshold = lib.as_decimal(policy.get("minimum_primary_value"), "holdout.minimum_primary_value")
        if value < threshold:
            problems.append(
                f"holdout primary value {lib.decimal_text(value)} is below the independent threshold "
                f"{lib.decimal_text(threshold)}"
            )
    except lib.DocumentError as exc:
        problems.append(str(exc))
    entries = holdout.get("evidence")
    if not isinstance(entries, list) or not entries:
        problems.append("holdout result carries no evidence")
    else:
        approved = {
            (item.get("id"), item.get("revision"))
            for item in mapping(contract, "evidence_policy").get("approved_producers") or []
            if isinstance(item, dict)
        }
        required = set(mapping(contract, "evidence_policy").get("required_kinds") or [])
        seen = set()
        for item in entries:
            if not isinstance(item, dict):
                problems.append("holdout evidence entry is not an object")
                continue
            seen.add(item.get("kind"))
            if (item.get("producer"), item.get("producer_revision")) not in approved:
                problems.append("holdout evidence producer is not approved by the contract")
            try:
                target = lib.safe_child_path(candidate.directory, item.get("path") or "")
            except lib.PathSafetyError as exc:
                problems.append(f"holdout evidence path is unsafe: {exc}")
                continue
            if lib.file_sha256(target) != item.get("sha256"):
                problems.append("holdout evidence sha256 does not match the file bytes")
        missing = sorted(required - seen)
        if missing:
            problems.append(f"holdout evidence is missing required kinds {missing}")
    if generalization.get("human_domain_review_required") or policy.get("human_domain_review_required"):
        review = mapping(declared, "human_domain_review")
        if review.get("status") != "approved" or not is_text(review.get("reference")):
            problems.append("an approved human/domain review with a reference is required")
    return problems


# --------------------------------------------------------------------------
# decision
# --------------------------------------------------------------------------


def decide(args: argparse.Namespace, report: dict) -> tuple[str, str]:
    try:
        contract_path = lib.safe_input_file(args.contract)
    except lib.PathSafetyError as exc:
        return "DESIGN_INCOMPLETE", f"contract path is unusable: {exc}"
    try:
        contract = lib.load_json_exact(contract_path)
    except lib.DocumentError as exc:
        return "DESIGN_INCOMPLETE", f"contract is not readable JSON: {exc}"
    problems = validate_contract(contract)
    if problems:
        report["contract_problems"] = problems
        return "DESIGN_INCOMPLETE", f"contract failed schema validation ({len(problems)} problem(s))"

    contract_sha = lib.canonical_sha256(contract)
    report["contract"] = {
        "path": str(contract_path),
        "revision": contract.get("contract_revision"),
        "sha256": contract_sha,
        "mode": contract.get("mode"),
        "claim_scope": mapping(contract, "generalization").get("claim_scope"),
    }
    if contract.get("mode") == "infrastructure-smoke-only":
        return (
            "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE",
            "contract mode is infrastructure-smoke-only; it declares no performance metric",
        )

    best = load_result("current-best", args.current_best, contract, contract_sha)
    candidate = load_result("candidate", args.candidate, contract, contract_sha)
    for loaded, key in ((best, "current_best"), (candidate, "candidate")):
        report[key] = {
            "path": str(loaded.path),
            "definition_revision": mapping(loaded.document, "subject").get("definition_revision"),
            "condition_manifest_path": loaded.manifest_relative,
            "condition_manifest_sha256": loaded.manifest_sha256,
            "structural_problems": loaded.structural,
            "integrity_problems": loaded.evidence,
        }

    promotion_problems = validate_promotion(best) if best.document else ["current best is unreadable"]
    report["current_best"]["promotion_problems"] = promotion_problems
    report["current_best"]["promotion_status"] = mapping(best.document, "promotion").get("status")

    best_blocked = [
        item for item in best.samples if isinstance(item, dict) and item.get("run_status") != "completed"
    ]
    best_failed = [
        item
        for item in best.samples
        if isinstance(item, dict) and item.get("run_status") == "completed" and item.get("functional_status") != "pass"
    ]
    if best.structural or best.evidence or promotion_problems or best_blocked or best_failed:
        return (
            "FUNCTIONAL_BASELINE_MISSING",
            "CURRENT_BEST_INVALID: the current best is not a valid, promoted, functionally passing baseline",
        )

    if candidate.structural:
        return "EVALUATION_BLOCKED", f"candidate structure is invalid ({len(candidate.structural)} problem(s))"

    if best.manifest_bytes != candidate.manifest_bytes or best.manifest_sha256 != candidate.manifest_sha256:
        return (
            "BASELINE_INVALIDATED",
            "the candidate ran under a different condition identity; re-measure the current best first",
        )

    blocked = candidate.blocked_classes()
    if blocked & ENVIRONMENT_CLASSES:
        return (
            "ENVIRONMENT_BLOCKED",
            f"candidate has blocked samples with failure classes {sorted(blocked & ENVIRONMENT_CLASSES)}",
        )
    if blocked & EVALUATION_CLASSES:
        return (
            "EVALUATION_BLOCKED",
            f"candidate has blocked samples with failure classes {sorted(blocked & EVALUATION_CLASSES)}",
        )
    if candidate.evidence:
        return "EVALUATION_BLOCKED", f"candidate evidence is invalid ({len(candidate.evidence)} problem(s))"

    if mapping(contract, "acceptance").get("require_functional_pass"):
        failing = [
            item.get("sample_id")
            for item in candidate.samples
            if isinstance(item, dict) and item.get("functional_status") != "pass"
        ]
        if failing:
            return "CANDIDATE_REJECTED", f"functional contract failed on samples {failing}"

    metric_problems, detail = compare_metrics(contract, best, candidate)
    report["metrics"] = detail
    if metric_problems:
        return "CANDIDATE_REJECTED", "; ".join(metric_problems)

    generalization_problems = check_generalization(contract, candidate)
    report["generalization_problems"] = generalization_problems
    if generalization_problems:
        return "GENERALIZATION_REQUIRED", "; ".join(generalization_problems)

    return (
        "CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE",
        "benchmark-local acceptance recommendation only; promotion requires a separate gate",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--current-best", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="explicit machine-readable report destination")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "schema_version": 1,
        "tool": "compare-evaluations.py",
        "promotion_performed": False,
        "attestation": "integrity and auditable provenance only; not remote attestation",
    }
    try:
        state, reason = decide(args, report)
    except lib.DocumentError as exc:
        print(f"ERROR malformed document: {exc}", file=sys.stderr)
        return 2
    except lib.PathSafetyError as exc:
        print(f"ERROR unsafe path: {exc}", file=sys.stderr)
        return 2

    report["state"] = state
    report["reason"] = reason
    report["exit_code"] = EXIT_CODES[state]
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        try:
            lib.atomic_write_text(args.output, text + "\n")
        except lib.PathSafetyError as exc:
            print(f"ERROR unsafe report destination: {exc}", file=sys.stderr)
            return 2
    print(text)
    return EXIT_CODES[state]


if __name__ == "__main__":
    raise SystemExit(main())
