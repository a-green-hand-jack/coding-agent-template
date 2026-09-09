# Evaluation Contract, Condition Manifest and Result Schema (v1)

> **Role of this document**
> - **Audience:** the development coding agent writing or reviewing an evaluation contract, condition manifest, or result document.
> - **Authority:** normative. Where this document and a script disagree, one of the two is a defect and must be fixed.
> - **Tone:** specification-style; field tables, canonical byte rules, precedence order, and exit codes as a contract.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** canonical JSON and hashing, contract v1 fields, the canonical condition manifest, the result and evidence schema, promotion and generalization blocks, comparator precedence, CLI and exit codes.
> - **Excludes:** when to run the loop at all (see `.agents/skills/agent-evaluation-loop-design/SKILL.md`), and the diagram and README sync rules (see `.agents/skills/agent-evaluation-loop-design/references/agent-architecture-schema.md`).

Normative for `validate-agent-evaluation.py` and `compare-evaluations.py`. When
this document and a script disagree, that is a defect in one of them — fix it,
do not work around it.

## 0. Canonical JSON and hashing

Every hash in this protocol is SHA-256 over *canonical JSON bytes*, defined as:

- UTF-8, no byte-order mark.
- Object keys sorted by Unicode code point.
- No insignificant whitespace: `,` between items, `:` between key and value.
- `true`, `false`, `null` lowercase.
- Integers emitted as-is. Non-integer numbers are parsed as exact decimals and
  re-emitted in plain (non-exponential) decimal form, preserving the digits
  written in the source document.
- Strings emitted with JSON escaping, non-ASCII characters kept literal.

Both scripts parse every document with exact decimal arithmetic, so `0.1 + 0.2`
problems cannot change a comparison outcome. Metric arithmetic is exact
decimal, never binary floating point.

Defined hashes:

| Name | Bytes hashed |
| --- | --- |
| `contract_sha256` | canonical JSON of the whole contract document |
| `condition_manifest_sha256` | canonical JSON of the whole condition-manifest document |
| `promoted_result_sha256` | canonical JSON of the current-best result document **with the top-level `promotion` key removed** |
| evidence `sha256` | raw bytes of the evidence file |

The contract deliberately contains no baseline pointer, so its hash is stable
for as long as the evaluation policy is unchanged.

## 1. Evaluation contract v1

Canonical location: `src/<agent_name>/development/evaluation-contract.json`,
resolved from `agent.yaml`'s `development_dir`. `--contract PATH` overrides it.
There is no other lookup path.

### 1.1 Required fields

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | integer | must be `1` |
| `agent` | string | non-empty |
| `mode` | string | `performance` \| `infrastructure-smoke-only` |
| `contract_revision` | string | non-empty; bump on any semantic change |
| `metric_policy_revision` | string | non-empty |
| `product` | object | `goal`, `input`, `output` — all non-empty strings |
| `functional_contract` | object | `checks`, `required_artifacts` |
| `functional_contract.checks` | array | ≥1 object with non-empty `id`, `description`, `source` |
| `functional_contract.required_artifacts` | array | ≥1 non-empty string |

`checks[].id` must be unique.

### 1.2 Fields required when `mode = performance`

| Field | Type | Notes |
| --- | --- | --- |
| `benchmark.task_set` | string | non-empty |
| `benchmark.revision` | string | non-empty |
| `benchmark.verifier` | string | non-empty |
| `benchmark.verifier_revision` | string | non-empty |
| `environment.backend` | string | non-empty |
| `environment.provider` | string | non-empty |
| `environment.model` | string | non-empty |
| `environment.runtime` | string | non-empty |
| `environment.repetitions` | integer | ≥1 |
| `environment.aggregation` | string | v1 supports only `mean` |
| `metrics.primary.name` | string | non-empty |
| `metrics.primary.direction` | string | `higher-is-better` \| `lower-is-better` |
| `metrics.primary.unit` | string | non-empty |
| `metrics.secondary` | array | may be empty; each entry needs `name`, `direction`, `unit` |
| `acceptance.minimum_primary_delta` | number | ≥0 |
| `acceptance.max_secondary_regression` | object | metric name → non-negative allowed regression; must contain an entry for every declared secondary metric |
| `acceptance.require_functional_pass` | boolean | |
| `stop_conditions` | array | ≥1 non-empty string |
| `evidence_policy.scrubbed_only` | boolean | must be `true` in v1 |
| `evidence_policy.required_kinds` | array | ≥1 of `artifact`, `verifier-report`, `scrubbed-trajectory` |
| `evidence_policy.approved_producers` | array | ≥1 object with non-empty `id` and `revision` |
| `generalization.claim_scope` | string | `benchmark-local` \| `product-general` |
| `generalization.holdout` | object \| null | required object when scope is `product-general` |
| `generalization.human_domain_review_required` | boolean | |

`environment` must agree with the condition manifest's `execution` and
`sampling` sections field by field. `environment` describes the
*expected/selected* conditions. The exact
per-run values (image digest, tool versions, request/sampling/retry/timeout
settings) live in the condition manifest. A mismatch between the two is
`EVALUATION_BLOCKED`, not a silent pass.

`mode = infrastructure-smoke-only` may omit `benchmark`, `environment`,
`metrics`, `acceptance` and `generalization`. It still requires
`functional_contract.checks` and `required_artifacts`. Its state is always
`SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`; it can render diagrams and it can never
accept a performance improvement.

### 1.3 `generalization.holdout` (required for `product-general`)

| Field | Type | Notes |
| --- | --- | --- |
| `task_set_revision` | string | non-empty, distinct from `benchmark.revision` |
| `task_input_sha256` | string | 64 lowercase hex, distinct from the benchmark's |
| `not_used_for_tuning` | boolean | must be `true` |
| `frozen_before_candidate_selection` | boolean | must be `true` |
| `minimum_primary_value` | number | independent acceptance threshold |
| `human_domain_review_required` | boolean | must be `true` |

A holdout that shares the benchmark's task-set revision or input hash is not
independent and yields `GENERALIZATION_REQUIRED`.

### 1.4 Invalid examples

- `schema_version: "1"` — string, not integer → `DESIGN_INCOMPLETE`.
- `mode: "perf"` — not in the enum → `DESIGN_INCOMPLETE`.
- `environment.aggregation: "median"` — unsupported in v1; adding an
  aggregation requires a new `metric_policy_revision` and a fresh baseline.
- `metrics.primary` absent while `mode = performance` → `DESIGN_INCOMPLETE`.
- `acceptance.minimum_primary_delta: -0.05` — negative → `DESIGN_INCOMPLETE`.
- `claim_scope: "product-general"` with `holdout: null` →
  `GENERALIZATION_REQUIRED` at comparison time.
- A `baseline` or `current_best` pointer inside the contract — forbidden; the
  baseline is a separate result document so that promoting a candidate cannot
  change the contract hash.

## 2. Canonical condition manifest

`condition_identity` in a result is a *projection*, not the source of truth.
Each run writes an immutable, secret-free `condition-manifest.json`:

```json
{
  "schema_version": 1,
  "contract": {"revision": "...", "sha256": "..."},
  "benchmark": {
    "task_set_revision": "...",
    "task_input_sha256": "...",
    "holdout_policy_revision": "..."
  },
  "verifier": {"id": "...", "revision": "...", "source_sha256": "..."},
  "metric_policy": {"revision": "...", "definition_sha256": "..."},
  "execution": {
    "backend": "...", "provider": "...", "model": "...", "runtime": "...",
    "image_digest": "...", "tool_versions": {},
    "request_parameters": {}, "sampling": {}, "seed": "...",
    "retry_policy": {}, "timeout_seconds": 0,
    "locale": "C", "timezone": "UTC"
  },
  "sampling": {"repetitions": 3, "aggregation": "mean"}
}
```

Rules:

- Every section and key above is required, including when the value is a
  default. `image_digest`, `tool_versions`, `request_parameters`, `sampling`,
  `seed`, `retry_policy`, `timeout_seconds`, `locale` and `timezone` are not
  optional; an omitted or locally inferred run-affecting input is
  `EVALUATION_BLOCKED`. Prose asserting two runs were equivalent is not
  evidence.
- No credentials, no secret-bearing prompts, no raw provider responses, no
  personal data. A secret-bearing setting is represented by a non-secret
  policy or revision hash, never copied in.
- `contract.sha256` must equal the hash actually computed from the contract
  passed to the comparator.
- A manifest is immutable once a result references it. A changed manifest is a
  new condition identity requiring a fresh current-best measurement; it cannot
  be repaired by editing the result.
- Current best and candidate must reference manifests with **equal canonical
  bytes and equal hashes** before any metric is compared.

## 3. Result schema

```json
{
  "schema_version": 1,
  "role": "candidate",
  "run_id": "...",
  "subject": {"definition_revision": "candidate-commit"},
  "condition_identity": {
    "condition_manifest_path": "condition-manifest.json",
    "condition_manifest_sha256": "...",
    "contract_revision": "...",
    "contract_sha256": "...",
    "benchmark_revision": "...",
    "verifier_revision": "...",
    "metric_policy_revision": "...",
    "backend": "...", "provider": "...", "model": "...", "runtime": "...",
    "repetitions": 3,
    "aggregation": "mean"
  },
  "condition_manifest_path": "condition-manifest.json",
  "condition_manifest_sha256": "...",
  "samples": [
    {
      "sample_id": "run-1",
      "run_status": "completed",
      "failure_class": "none",
      "functional_status": "pass",
      "primary_value": 0.75,
      "secondary_values": {},
      "evidence": [
        {
          "kind": "artifact",
          "path": "evidence/paper.md",
          "sha256": "...",
          "producer": "run-benchmark.sh",
          "producer_revision": "..."
        }
      ]
    }
  ],
  "aggregate": {"primary_value": 0.75, "secondary_values": {}}
}
```

- `role` is `current-best` or `candidate` and must match the CLI slot.
- `run_status`: `completed` | `blocked`.
- `failure_class`: `none` | `credential` | `provider` | `infrastructure` |
  `benchmark-verifier` | `evidence`. A `completed` sample must use `none`; a
  `blocked` sample must not.
- `functional_status`: `pass` | `fail` | `unknown`. A **product functional
  failure** is `run_status: completed` with `functional_status: fail`. That is
  a rejection, not an environment block.
- Sample count must equal the contract's `repetitions`. `sample_id` must be
  unique.
- `primary_value` and `secondary_values` are required numbers on a `completed`
  sample and must be `null` / `{}` on a `blocked` sample. A blocked sample
  carries no metric and no required evidence, because a blocked run is
  classified before any metric is read.
- `aggregate.primary_value` and `aggregate.secondary_values` must be `null` /
  `{}` when any sample is `blocked`. When every sample is `completed`, the
  comparator **recomputes** the mean from the samples with exact decimal
  arithmetic and cross-checks the self-reported `aggregate`. A mismatch is
  `EVALUATION_BLOCKED`; the self-reported aggregate is never trusted on its
  own.
- `condition_identity` must equal the projection of the referenced manifest,
  field by field, and `condition_manifest_path`/`_sha256` must agree with the
  copy inside `condition_identity`.

### 3.1 Evidence rules

Each evidence entry needs `kind`, `path`, `sha256`, `producer`,
`producer_revision`. Every kind in `evidence_policy.required_kinds` must appear
in every `completed` sample.

Path safety, in order:

1. Lexical rejection of absolute paths, any `..` segment, NUL bytes, empty
   paths, and Windows-style drive or UNC prefixes.
2. Resolution with `Path.resolve(strict=True)`; the resolved file must still
   sit inside the directory containing the result file.
3. v1 rejects a symlink at the result file, at any evidence file, and at any
   of their parent directories inside the result directory.

`producer`/`producer_revision` must match an entry in
`evidence_policy.approved_producers`.

**This is integrity and auditable provenance, not remote attestation.** The
comparator proves that the bytes match the recorded digests and that the
declared producer is on the contract's allowlist. It cannot prove a provider
really returned a given response. The trust boundary remains the allowlisted
runner, the controlled execution environment, and human review.

### 3.2 Promotion record (current best only)

A current-best result must carry:

```json
"promotion": {
  "status": "promoted",
  "promoted_result_sha256": "...",
  "approved_producer": {"id": "...", "revision": "..."},
  "decision_reference": "..."
}
```

`promoted_result_sha256` is the hash defined in §0 — the result document with
`promotion` removed — so the record cannot be self-referential. A missing,
malformed or mismatched promotion record makes the current best invalid
(`FUNCTIONAL_BASELINE_MISSING` / reason `CURRENT_BEST_INVALID`); an arbitrary
candidate never becomes the baseline by default. This is an auditable record,
not a cryptographic attestation.

### 3.3 Candidate generalization block

Required only when the contract's `claim_scope` is `product-general`:

```json
"generalization": {
  "holdout": {
    "task_set_revision": "...",
    "task_input_sha256": "...",
    "not_used_for_tuning": true,
    "frozen_before_candidate_selection": true,
    "verifier_revision": "...",
    "metric_policy_revision": "...",
    "functional_status": "pass",
    "primary_value": 0.74,
    "evidence": [ ... ]
  },
  "human_domain_review": {"status": "approved", "reference": "..."}
}
```

The holdout's revisions and input hash must match the contract's holdout policy
and must differ from the benchmark's. Holdout values may not be copied from the
benchmark samples, and the block may not widen the contract's policy. Anything
missing, non-independent, unreviewed, or below the holdout threshold yields
`GENERALIZATION_REQUIRED` and does not update the best.

## 4. Comparator precedence

Evaluated strictly in order; the first match wins.

1. Contract missing, unparsable or schema-invalid → `DESIGN_INCOMPLETE` (20).
   Contract valid and `mode = infrastructure-smoke-only` →
   `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE` (20).
2. Current-best result missing, wrong `role`, schema-invalid, promotion record
   missing or mismatched, manifest/evidence invalid, or not
   `completed`/`pass` → `FUNCTIONAL_BASELINE_MISSING` (20), reason
   `CURRENT_BEST_INVALID`.
3. Either condition manifest missing, unparsable, wrongly hashed, unsafely
   pathed, or a `condition_identity` projection that disagrees with its
   manifest; unapproved producer; structurally incomplete samples →
   `EVALUATION_BLOCKED` (41).
4. The two manifests' canonical bytes or hashes differ →
   `BASELINE_INVALIDATED` (30).
5. Any candidate sample `blocked` with `credential`, `provider` or
   `infrastructure` → `ENVIRONMENT_BLOCKED` (40).
6. Any candidate sample `blocked` with `benchmark-verifier` or `evidence`, or
   any evidence/hash/producer/repetition/aggregation defect →
   `EVALUATION_BLOCKED` (41).
7. Any `completed` candidate sample whose `functional_status` is not `pass`
   (when `require_functional_pass`) → `CANDIDATE_REJECTED` (10).
8. Recomputed primary mean fails the direction-aware `minimum_primary_delta`,
   or a secondary metric regresses past `max_secondary_regression` →
   `CANDIDATE_REJECTED` (10).
9. Contract requires `product-general` and the independent holdout result or
   human/domain review is missing, non-independent or below threshold →
   `GENERALIZATION_REQUIRED` (42).
10. All fixed benchmark-local rules satisfied →
    `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE` (0).

Direction-aware delta: `higher-is-better` requires
`candidate_mean - best_mean >= minimum_primary_delta`; `lower-is-better`
requires `best_mean - candidate_mean >= minimum_primary_delta`.

Secondary regression uses each secondary metric's own direction and its allowed
regression from `max_secondary_regression`; a metric listed in the contract but
absent from a sample is `EVALUATION_BLOCKED`.

## 5. CLI

```text
compare-evaluations.py --contract PATH --current-best PATH --candidate PATH [--output PATH]
```

- Every input passes the same lexical + realpath safety checks before it is
  read.
- `--output` must be an explicit, non-symlink path; the report is written with
  a temporary file plus atomic replace.
- The report records contract/result/manifest hashes, approved-producer checks,
  current-best validity, promotion status, the recomputed metrics, the state,
  the reason and the exit code. The same JSON goes to stdout.
- The comparator never runs a benchmark, never calls a provider, and never
  writes a current best.

## 6. Exit codes

| Exit | States |
| --- | --- |
| 0 | `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE` |
| 10 | `CANDIDATE_REJECTED` |
| 20 | `DESIGN_INCOMPLETE`, `FUNCTIONAL_BASELINE_MISSING`, `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE` |
| 30 | `BASELINE_INVALIDATED` |
| 40 | `ENVIRONMENT_BLOCKED` |
| 41 | `EVALUATION_BLOCKED` |
| 42 | `GENERALIZATION_REQUIRED` |
| 2 | CLI or schema malformed |

The JSON `state` field disambiguates states that share an exit code.
`ACCEPTED_AS_CURRENT_BEST` is a lifecycle state produced by a separate
promotion gate and is never emitted by the comparator.
