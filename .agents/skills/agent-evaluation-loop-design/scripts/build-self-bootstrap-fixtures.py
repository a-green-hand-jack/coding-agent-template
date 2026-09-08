#!/usr/bin/env python3
"""Regenerate the fixed self-bootstrap fixtures with correct hashes.

Maintenance helper, not part of the evaluation protocol. The fixtures it writes
are protected inputs: run this only when deliberately changing the fixed
outcome cases, then re-run the validator and the comparator outcome matrix.

Deterministic: same inputs produce byte-identical fixtures.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _evaluation_lib as lib  # noqa: E402

RUNNER = {"id": "run-benchmark.sh", "revision": "runner-1"}
VERIFIER = {"id": "approved-verifier", "revision": "paper-verifier-1"}

EVIDENCE_FILES = {
    "evidence/artifact.txt": (
        "# Fixed fixture artifact\n"
        "\n"
        "Stands in for a generated paper draft. Secret-free, deterministic, and\n"
        "pinned by SHA-256 inside the outcome-case results.\n"
    ),
    "evidence/verifier-report.json": (
        '{\n'
        '  "checks": {\n'
        '    "abstract-claims-supported": "pass",\n'
        '    "all-required-sections-present": "pass",\n'
        '    "citations-resolve-to-supplied-sources": "pass"\n'
        '  },\n'
        '  "verifier": "approved-verifier",\n'
        '  "verifier_revision": "paper-verifier-1"\n'
        '}\n'
    ),
    "evidence/trajectory.scrubbed.txt": (
        "# Scrubbed trajectory\n"
        "\n"
        "step 1 load brief\n"
        "step 2 apply paper-writing skill\n"
        "step 3 emit paper.md and section-coverage.json\n"
        "\n"
        "No provider payloads, no credentials, no personal data.\n"
    ),
    "evidence/holdout-artifact.txt": (
        "# Fixed holdout artifact\n"
        "\n"
        "Independent holdout draft. Frozen before candidate selection and never\n"
        "used for tuning.\n"
    ),
    "evidence/holdout-verifier-report.json": (
        '{\n'
        '  "checks": {\n'
        '    "abstract-claims-supported": "pass",\n'
        '    "all-required-sections-present": "pass",\n'
        '    "citations-resolve-to-supplied-sources": "pass"\n'
        '  },\n'
        '  "task_set": "paper-holdout-fixed",\n'
        '  "verifier": "approved-verifier",\n'
        '  "verifier_revision": "paper-verifier-1"\n'
        '}\n'
    ),
    "evidence/holdout-trajectory.scrubbed.txt": (
        "# Scrubbed holdout trajectory\n"
        "\n"
        "step 1 load holdout brief\n"
        "step 2 apply paper-writing skill\n"
        "step 3 emit holdout paper.md\n"
    ),
}

BENCHMARK_EVIDENCE = (
    ("artifact", "evidence/artifact.txt", RUNNER),
    ("verifier-report", "evidence/verifier-report.json", VERIFIER),
    ("scrubbed-trajectory", "evidence/trajectory.scrubbed.txt", RUNNER),
)
HOLDOUT_EVIDENCE = (
    ("artifact", "evidence/holdout-artifact.txt", RUNNER),
    ("verifier-report", "evidence/holdout-verifier-report.json", VERIFIER),
    ("scrubbed-trajectory", "evidence/holdout-trajectory.scrubbed.txt", RUNNER),
)

BENCHMARK_TASK_INPUT_SHA = "3" * 64
HOLDOUT_TASK_INPUT_SHA = "7" * 64


def evidence_entries(root: Path, spec) -> list[dict]:
    entries = []
    for kind, relative, producer in spec:
        entries.append(
            {
                "kind": kind,
                "path": relative,
                "sha256": lib.file_sha256(root / relative),
                "producer": producer["id"],
                "producer_revision": producer["revision"],
            }
        )
    return entries


def condition_manifest(contract_revision: str, contract_sha: str, model: str, holdout_policy: str) -> dict:
    return {
        "schema_version": 1,
        "contract": {"revision": contract_revision, "sha256": contract_sha},
        "benchmark": {
            "task_set_revision": "paper-tasks-1",
            "task_input_sha256": BENCHMARK_TASK_INPUT_SHA,
            "holdout_policy_revision": holdout_policy,
        },
        "verifier": {
            "id": "approved-verifier",
            "revision": "paper-verifier-1",
            "source_sha256": "5" * 64,
        },
        "metric_policy": {
            "revision": "paper-metric-policy-1",
            "definition_sha256": "6" * 64,
        },
        "execution": {
            "backend": "fixture-backend",
            "provider": "fixture-provider",
            "model": model,
            "runtime": "fixture-runtime-1",
            "image_digest": "sha256:" + "a" * 64,
            "tool_versions": {"approved-verifier": "paper-verifier-1", "python": "3.12"},
            "request_parameters": {"max_output_tokens": 4096, "temperature": 0},
            "sampling": {"top_p": 1},
            "seed": "fixture-seed-1",
            "retry_policy": {"backoff": "none", "max_attempts": 1},
            "timeout_seconds": 600,
            "locale": "C",
            "timezone": "UTC",
        },
        "sampling": {"repetitions": 3, "aggregation": "mean"},
    }


def projection(manifest: dict, manifest_relative: str, manifest_sha: str) -> dict:
    execution = manifest["execution"]
    return {
        "condition_manifest_path": manifest_relative,
        "condition_manifest_sha256": manifest_sha,
        "contract_revision": manifest["contract"]["revision"],
        "contract_sha256": manifest["contract"]["sha256"],
        "benchmark_revision": manifest["benchmark"]["task_set_revision"],
        "verifier_revision": manifest["verifier"]["revision"],
        "metric_policy_revision": manifest["metric_policy"]["revision"],
        "backend": execution["backend"],
        "provider": execution["provider"],
        "model": execution["model"],
        "runtime": execution["runtime"],
        "repetitions": manifest["sampling"]["repetitions"],
        "aggregation": manifest["sampling"]["aggregation"],
    }


def completed_sample(sample_id: str, primary: str, secondary: str, evidence: list[dict]) -> dict:
    return {
        "sample_id": sample_id,
        "run_status": "completed",
        "failure_class": "none",
        "functional_status": "pass",
        "primary_value": Decimal(primary),
        "secondary_values": {"citation_error_rate": Decimal(secondary)},
        "evidence": evidence,
    }


def blocked_sample(sample_id: str, failure_class: str) -> dict:
    return {
        "sample_id": sample_id,
        "run_status": "blocked",
        "failure_class": failure_class,
        "functional_status": "unknown",
        "primary_value": None,
        "secondary_values": {},
        "evidence": [],
    }


def result(role: str, run_id: str, revision: str, identity: dict, samples: list[dict]) -> dict:
    completed = [item for item in samples if item["run_status"] == "completed"]
    if len(completed) == len(samples):
        aggregate = {
            "primary_value": lib.exact_mean([item["primary_value"] for item in completed]),
            "secondary_values": {
                "citation_error_rate": lib.exact_mean(
                    [item["secondary_values"]["citation_error_rate"] for item in completed]
                )
            },
        }
    else:
        aggregate = {"primary_value": None, "secondary_values": {}}
    return {
        "schema_version": 1,
        "role": role,
        "run_id": run_id,
        "subject": {"definition_revision": revision},
        "condition_identity": identity,
        "condition_manifest_path": identity["condition_manifest_path"],
        "condition_manifest_sha256": identity["condition_manifest_sha256"],
        "samples": samples,
        "aggregate": aggregate,
    }


def write(path: Path, document: dict) -> None:
    lib.atomic_write_text(path, lib.dump_canonical_json(document) + "\n")


def write_promoted(path: Path, document: dict, reference: str) -> None:
    """Write, reload, then stamp the promotion hash over the reloaded bytes."""
    write(path, document)
    reloaded = lib.load_json_exact(path)
    reloaded["promotion"] = {
        "status": "promoted",
        "promoted_result_sha256": lib.promoted_result_sha256(reloaded),
        "approved_producer": dict(RUNNER),
        "decision_reference": reference,
    }
    write(path, reloaded)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[1] / "fixtures"
    parser.add_argument("--fixtures-root", type=Path, default=default_root)
    args = parser.parse_args()
    fixtures = args.fixtures_root.resolve()
    boot = fixtures / "self-bootstrap"
    boot.mkdir(parents=True, exist_ok=True)
    (boot / "evidence").mkdir(exist_ok=True)

    for relative, text in EVIDENCE_FILES.items():
        lib.atomic_write_text(boot / relative, text)

    base_contract_path = fixtures / "paper-agent/development/evaluation-contract.json"
    base_contract = lib.load_json_exact(base_contract_path)
    base_sha = lib.canonical_sha256(base_contract)

    # A product-general variant of the same contract, with a real holdout policy.
    general = lib.load_json_exact(base_contract_path)
    general["contract_revision"] = "paper-contract-general-1"
    general["generalization"] = {
        "claim_scope": "product-general",
        "holdout": {
            "task_set_revision": "paper-holdout-1",
            "task_input_sha256": HOLDOUT_TASK_INPUT_SHA,
            "not_used_for_tuning": True,
            "frozen_before_candidate_selection": True,
            "minimum_primary_value": Decimal("0.70"),
            "human_domain_review_required": True,
        },
        "human_domain_review_required": True,
    }
    write(boot / "contract-product-general.json", general)
    general_sha = lib.canonical_sha256(lib.load_json_exact(boot / "contract-product-general.json"))

    # A deliberately invalid contract: `mode` is outside the enum.
    invalid = lib.load_json_exact(base_contract_path)
    invalid["mode"] = "perf"
    write(boot / "contract-invalid.json", invalid)

    manifests = {
        "condition-manifest.json": condition_manifest(
            "paper-contract-1", base_sha, "fixture-model", "paper-holdout-policy-none"
        ),
        "condition-manifest-changed.json": condition_manifest(
            "paper-contract-1", base_sha, "fixture-model-v2", "paper-holdout-policy-none"
        ),
        "condition-manifest-general.json": condition_manifest(
            "paper-contract-general-1", general_sha, "fixture-model", "paper-holdout-1"
        ),
    }
    shas = {}
    for name, document in manifests.items():
        write(boot / name, document)
        reloaded = lib.load_json_exact(boot / name)
        shas[name] = lib.canonical_sha256(reloaded)
        manifests[name] = reloaded

    identity = projection(manifests["condition-manifest.json"], "condition-manifest.json", shas["condition-manifest.json"])
    identity_changed = projection(
        manifests["condition-manifest-changed.json"],
        "condition-manifest-changed.json",
        shas["condition-manifest-changed.json"],
    )
    identity_general = projection(
        manifests["condition-manifest-general.json"],
        "condition-manifest-general.json",
        shas["condition-manifest-general.json"],
    )

    bench = evidence_entries(boot, BENCHMARK_EVIDENCE)
    holdout_evidence = evidence_entries(boot, HOLDOUT_EVIDENCE)

    def triple(primaries, secondaries):
        return [
            completed_sample(f"run-{index + 1}", primary, secondary, bench)
            for index, (primary, secondary) in enumerate(zip(primaries, secondaries))
        ]

    best = result(
        "current-best",
        "best-run-1",
        "best-commit-1",
        identity,
        triple(("0.70", "0.72", "0.71"), ("0.10", "0.10", "0.10")),
    )
    write_promoted(boot / "current-best-result.json", best, "template issue: paper baseline promotion")

    # Same result without a promotion record: an invalid current best.
    write(boot / "current-best-unpromoted-result.json", best)

    write(
        boot / "accepted-candidate-result.json",
        result(
            "candidate",
            "candidate-run-1",
            "candidate-commit-1",
            identity,
            triple(("0.75", "0.76", "0.74"), ("0.09", "0.09", "0.09")),
        ),
    )
    write(
        boot / "rejected-candidate-result.json",
        result(
            "candidate",
            "candidate-run-2",
            "candidate-commit-2",
            identity,
            triple(("0.71", "0.71", "0.71"), ("0.10", "0.10", "0.10")),
        ),
    )
    write(
        boot / "secondary-regression-candidate-result.json",
        result(
            "candidate",
            "candidate-run-3",
            "candidate-commit-3",
            identity,
            triple(("0.80", "0.80", "0.80"), ("0.20", "0.20", "0.20")),
        ),
    )

    functional_fail = result(
        "candidate",
        "candidate-run-4",
        "candidate-commit-4",
        identity,
        triple(("0.80", "0.80", "0.80"), ("0.09", "0.09", "0.09")),
    )
    functional_fail["samples"][1]["functional_status"] = "fail"
    write(boot / "functional-failed-candidate-result.json", functional_fail)

    environment_blocked = result(
        "candidate",
        "candidate-run-5",
        "candidate-commit-5",
        identity,
        [
            completed_sample("run-1", "0.75", "0.09", bench),
            blocked_sample("run-2", "provider"),
            completed_sample("run-3", "0.76", "0.09", bench),
        ],
    )
    write(boot / "environment-blocked-candidate-result.json", environment_blocked)

    evaluation_blocked = result(
        "candidate",
        "candidate-run-6",
        "candidate-commit-6",
        identity,
        [
            completed_sample("run-1", "0.75", "0.09", bench),
            blocked_sample("run-2", "benchmark-verifier"),
            completed_sample("run-3", "0.76", "0.09", bench),
        ],
    )
    write(boot / "evaluation-blocked-candidate-result.json", evaluation_blocked)

    write(
        boot / "invalidated-candidate-result.json",
        result(
            "candidate",
            "candidate-run-7",
            "candidate-commit-7",
            identity_changed,
            triple(("0.75", "0.76", "0.74"), ("0.09", "0.09", "0.09")),
        ),
    )

    general_best = result(
        "current-best",
        "best-run-2",
        "best-commit-2",
        identity_general,
        triple(("0.70", "0.72", "0.71"), ("0.10", "0.10", "0.10")),
    )
    write_promoted(
        boot / "current-best-general-result.json",
        general_best,
        "template issue: product-general baseline promotion",
    )

    write(
        boot / "generalization-required-candidate-result.json",
        result(
            "candidate",
            "candidate-run-8",
            "candidate-commit-8",
            identity_general,
            triple(("0.75", "0.76", "0.74"), ("0.09", "0.09", "0.09")),
        ),
    )

    satisfied = result(
        "candidate",
        "candidate-run-9",
        "candidate-commit-9",
        identity_general,
        triple(("0.75", "0.76", "0.74"), ("0.09", "0.09", "0.09")),
    )
    satisfied["generalization"] = {
        "holdout": {
            "task_set_revision": "paper-holdout-1",
            "task_input_sha256": HOLDOUT_TASK_INPUT_SHA,
            "not_used_for_tuning": True,
            "frozen_before_candidate_selection": True,
            "verifier_revision": "paper-verifier-1",
            "metric_policy_revision": "paper-metric-policy-1",
            "functional_status": "pass",
            "primary_value": Decimal("0.74"),
            "evidence": holdout_evidence,
        },
        "human_domain_review": {
            "status": "approved",
            "reference": "template issue: holdout domain review",
        },
    }
    write(boot / "generalization-satisfied-candidate-result.json", satisfied)

    problems = verify(boot, fixtures)
    if problems:
        for problem in problems:
            print(f"ERROR {problem}", file=sys.stderr)
        return 1

    written = sorted(item.relative_to(boot).as_posix() for item in boot.rglob("*") if item.is_file())
    for name in written:
        print(name)
    return 0


def verify(boot: Path, fixtures: Path) -> list[str]:
    """Re-read every generated fixture and confirm the pinned hashes hold."""
    problems: list[str] = []
    for path in sorted(boot.glob("*.json")):
        document = lib.load_json_exact(path)
        if lib.dump_canonical_json(document) + "\n" != path.read_text(encoding="utf-8"):
            problems.append(f"not round-trip stable: {path.name}")
        if not isinstance(document, dict):
            continue
        promotion = document.get("promotion")
        if isinstance(promotion, dict):
            expected = lib.promoted_result_sha256(document)
            if promotion.get("promoted_result_sha256") != expected:
                problems.append(f"promotion hash mismatch: {path.name}")
        for sample in document.get("samples", []) or []:
            for item in sample.get("evidence", []) or []:
                target = boot / item["path"]
                if not target.is_file():
                    problems.append(f"missing evidence {item['path']} in {path.name}")
                elif lib.file_sha256(target) != item["sha256"]:
                    problems.append(f"evidence hash mismatch {item['path']} in {path.name}")
        identity = document.get("condition_identity")
        if isinstance(identity, dict):
            manifest_path = boot / identity["condition_manifest_path"]
            if not manifest_path.is_file():
                problems.append(f"missing manifest for {path.name}")
            elif lib.canonical_sha256(lib.load_json_exact(manifest_path)) != identity["condition_manifest_sha256"]:
                problems.append(f"manifest hash mismatch for {path.name}")
    base = lib.load_json_exact(fixtures / "paper-agent/development/evaluation-contract.json")
    base_sha = lib.canonical_sha256(base)
    manifest = lib.load_json_exact(boot / "condition-manifest.json")
    if manifest["contract"]["sha256"] != base_sha:
        problems.append("condition-manifest.json does not pin the paper-agent contract hash")
    return problems


if __name__ == "__main__":
    raise SystemExit(main())
