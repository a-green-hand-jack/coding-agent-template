# Diagram Schema and README Sync Rules

> **Role of this document**
> - **Audience:** the development coding agent changing the diagram generator or validator, or reviewing a generated diagram.
> - **Authority:** normative. It is the specification `generate-agent-diagrams.py` and `validate-agent-evaluation.py` implement.
> - **Tone:** specification-style; tables of inputs, scan rules, identifiers and validator rules, each with its stated failure case.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** the diagram inputs, the runtime component scan, node identifiers, the README managed-block markers and their validator rules, and the determinism and write guarantees.
> - **Excludes:** when to run the generator inside the loop (see `.agents/skills/agent-evaluation-loop-design/SKILL.md`), and the evaluation contract's schema (see `.agents/skills/agent-evaluation-loop-design/references/evaluation-contract.md`).

Normative for `generate-agent-diagrams.py` and the diagram checks in
`validate-agent-evaluation.py`.

Two generated files, fixed basenames:

| File | Question it answers | Mermaid type |
| --- | --- | --- |
| `agent-architecture.mmd` | What *is* this product Agent? | `flowchart TB` |
| `agent-optimization-loop.mmd` | How is it iterated? | `stateDiagram-v2` |

The `.mmd` files are the single source of truth. README carries generated
blocks only. Neither diagram is product runtime content.

## 1. Inputs

| Input | Source | Missing behaviour |
| --- | --- | --- |
| agent name | `--agent` | required |
| runtime dir | `agent.yaml` → `runtime_dir` | `MISSING_RUNTIME_DIR` node |
| development dir | `agent.yaml` → `development_dir`, relative to Agent root; canonical `../../.agents/development/<agent_name>` for `src/<agent_name>/` | contract lookup fails |
| contract | `<agent-root>/<development_dir>/evaluation-contract.json` or `--contract` | `DESIGN_INCOMPLETE` |
| components | real filesystem scan of the runtime dir | explicit `(none)` node |

`agent.yaml` is read as a dependency-free `key: value` manifest. Blank lines
and `#` comments are skipped; the first `:` separates key from value; values
are stripped of surrounding whitespace and matching quotes. A missing key, or a
key pointing at a non-existent path, produces an explicit missing-state node —
never a guessed default.

### 1.1 Component scan

Scanned relative to the resolved runtime dir, sorted by path, never inferred
from Markdown prose:

| Component | Scan rule |
| --- | --- |
| identity | file `identity.md` |
| memory policy | file `memory-policy.md` |
| knowledge | `knowledge/**/*.md`, excluding `AGENTS.md` |
| skills | directories under `skills/` containing `SKILL.md` |
| workflows | `workflows/**/*.md`, excluding `AGENTS.md` |
| tools | files directly under `tools/`, excluding `AGENTS.md` and `README.md` |

`AGENTS.md` files are development instructions and are never diagram nodes. An
empty or absent group yields a single `(none)` node so that absence is visible
rather than implied.

### 1.2 Node identifiers

Deterministic and Mermaid-safe. A slug lowercases the source name, replaces
every character outside `[a-z0-9]` with `_`, collapses runs of `_`, and strips
leading/trailing `_`. The slugged name is the component's path relative to its
group directory **with the file suffix removed** (for a skill, the skill
directory name).

| Kind | Id | Example |
| --- | --- | --- |
| identity | `rt_identity` | |
| memory policy | `rt_memory_policy` | |
| knowledge entry | `kn_<slug>` | `knowledge/README.md` -> `kn_readme` |
| skill | `sk_<slug>` | `skills/paper-writing/SKILL.md` -> `sk_paper_writing` |
| workflow | `wf_<slug>` | `workflows/write-paper.md` -> `wf_write_paper` |
| tool | `tl_<slug>` | `tools/section_check.py` -> `tl_section_check` |
| empty group | `<prefix>_none` | `kn_none`, `sk_none`, `wf_none`, `tl_none` |

Collisions get a `_2`, `_3`, … suffix in scan order.

## 2. `agent-architecture.mmd`

Fixed subgraph order and required node ids:

1. `user` — "Human / User": `user_input`, `user_output`
2. `runtime` — "Product runtime: `<runtime dir>`": `rt_identity`,
   `rt_memory_policy`, plus the scanned `kn_*`, `sk_*`, `wf_*`, `tl_*` nodes
   inside per-group subgraphs `grp_knowledge`, `grp_skills`, `grp_workflows`,
   `grp_tools`
3. `execution` — "Execution layer (external — not product identity)":
   `ex_backend`, `ex_provider`, `ex_model`
4. `evidence` — "Evidence outputs": `ev_artifact`, `ev_trajectory`,
   `ev_verifier`
5. `development` — "Development-only (not product behavior)": `dv_contract`,
   `dv_validation`, `dv_benchmark`, `dv_loop`

Required edges:

```text
user_input   --> rt_identity
rt_identity  --> ex_backend
ex_backend   --> ex_provider
ex_provider  --> ex_model
ex_model     --> user_output
rt_identity  --> ev_artifact
ev_artifact  --> ev_verifier
ev_verifier  --> dv_benchmark
dv_contract  --> dv_validation
dv_validation--> dv_benchmark
dv_benchmark --> dv_loop
```

Product input, output, functional checks, required artifacts and the
smoke/performance label come from the contract. With no contract the diagram
still renders, labelled `DESIGN_INCOMPLETE`; nothing about product semantics is
guessed.

Forbidden: any node derived from an `AGENTS.md`, from `.agents/`, or from a
capability that no scanned file declares. Backend, provider and model are
external execution, never product identity.

## 3. `agent-optimization-loop.mmd`

A `stateDiagram-v2` whose semantics and guards are fixed. Layout may change;
states and transitions may not be dropped.

Required states:

```text
INTENT_DEFINED  CONTRACT_DESIGNED  FUNCTIONAL_BASELINE_BUILT  BASELINE_MEASURED
HYPOTHESIS_READY  CANDIDATE_IMPLEMENTED  CANDIDATE_EVALUATING  EVIDENCE_VALIDATED
COMPARE_WITH_CURRENT_BEST  DESIGN_INCOMPLETE  FUNCTIONAL_BASELINE_MISSING
SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE  ENVIRONMENT_BLOCKED  EVALUATION_BLOCKED
BASELINE_INVALIDATED  CANDIDATE_REJECTED  CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE
GENERALIZATION_REQUIRED  ACCEPTED_AS_CURRENT_BEST  STOPPED
```

Required transitions, each carrying its guard as the transition label:

```text
INTENT_DEFINED             --> CONTRACT_DESIGNED
CONTRACT_DESIGNED          --> FUNCTIONAL_BASELINE_BUILT
CONTRACT_DESIGNED          --> DESIGN_INCOMPLETE
CONTRACT_DESIGNED          --> SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE
FUNCTIONAL_BASELINE_BUILT  --> BASELINE_MEASURED
FUNCTIONAL_BASELINE_BUILT  --> FUNCTIONAL_BASELINE_MISSING
BASELINE_MEASURED          --> HYPOTHESIS_READY
HYPOTHESIS_READY           --> CANDIDATE_IMPLEMENTED
CANDIDATE_IMPLEMENTED      --> CANDIDATE_EVALUATING
CANDIDATE_EVALUATING       --> EVIDENCE_VALIDATED
EVIDENCE_VALIDATED         --> COMPARE_WITH_CURRENT_BEST
COMPARE_WITH_CURRENT_BEST  --> BASELINE_INVALIDATED
COMPARE_WITH_CURRENT_BEST  --> ENVIRONMENT_BLOCKED
COMPARE_WITH_CURRENT_BEST  --> EVALUATION_BLOCKED
COMPARE_WITH_CURRENT_BEST  --> DESIGN_INCOMPLETE
COMPARE_WITH_CURRENT_BEST  --> FUNCTIONAL_BASELINE_MISSING
COMPARE_WITH_CURRENT_BEST  --> CANDIDATE_REJECTED
COMPARE_WITH_CURRENT_BEST  --> CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE
CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE --> ACCEPTED_AS_CURRENT_BEST
CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE --> GENERALIZATION_REQUIRED
ACCEPTED_AS_CURRENT_BEST   --> HYPOTHESIS_READY
ACCEPTED_AS_CURRENT_BEST   --> STOPPED
CANDIDATE_REJECTED         --> HYPOTHESIS_READY
ENVIRONMENT_BLOCKED        --> CANDIDATE_EVALUATING
EVALUATION_BLOCKED         --> CANDIDATE_EVALUATING
BASELINE_INVALIDATED       --> BASELINE_MEASURED
GENERALIZATION_REQUIRED    --> HYPOTHESIS_READY
```

The diagram must additionally show, as notes:

- `subject.definition_revision` differs between current best and candidate by
  design; that difference is the premise of the comparison, not a baseline
  invalidation.
- The canonical condition manifest, both revisions and the evidence manifest
  are traceable; a run-affecting input that cannot go in the manifest blocks
  the comparison.
- `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE` is benchmark-local only and is never
  auto-promoted by the comparator.
- `GENERALIZATION_REQUIRED` needs an independent holdout/canary plus
  human/domain review.
- `ENVIRONMENT_BLOCKED` and `EVALUATION_BLOCKED` update nothing and are not
  regressions.
- `BASELINE_INVALIDATED` requires re-measuring the current best under the new
  condition identity.
- `STOPPED` needs a recorded reason: goal met, N iterations without material
  improvement, budget/time exhausted, or a human stop.
- A self-bootstrap sub-state group: a skill candidate runs against the fixed
  fixture and the base evaluator and cannot relax the evaluator.
- The current agent's own contract state. For `hewo` that is
  `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`, never "performance accepted".

## 4. README managed blocks

One block per diagram, keyed by basename:

```markdown
<!-- BEGIN GENERATED: agent-architecture.mmd -->
```mermaid
...
```
<!-- END GENERATED: agent-architecture.mmd -->
```

Validator rules, each with a fixed negative case:

| Rule | Negative case |
| --- | --- |
| exactly one begin and one end per basename | missing, duplicate |
| begin precedes its end, blocks do not cross | crossed markers |
| begin and end names pair exactly | wrong basename |
| the fenced Mermaid body equals the canonical `.mmd` bytes | stale block, `.mmd` drift |
| content outside markers is untouched by the generator | — |

`--init-readme` inserts markers only when **both** are entirely absent and the
insertion point is unambiguous. It never repairs damaged, duplicated or crossed
markers. README also links the `.mmd` source files. No SVG or PNG is produced
and no online Mermaid service is used; some Markdown renderers will show the
block as code, which is an accepted v1 limitation.

## 5. Determinism and writes

- Relative paths resolve against their explicit root, never an accidental cwd.
- Every write is a temporary file plus atomic replace.
- Running twice on unchanged inputs produces byte-identical `.mmd` files and
  README blocks. `--check` writes nothing and exits non-zero on any drift.
