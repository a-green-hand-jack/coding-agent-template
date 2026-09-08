---
name: agent-evaluation-loop-design
description: Design and verify a product Agent's optimization loop — define the evaluation contract, build a functionally complete baseline, fix the run conditions, compare a candidate against the current best, and decide accept/reject/blocked. Also generates the two Mermaid diagrams (product structure and optimization state machine) and syncs them into README. Use before claiming any product Agent got "better", when setting up a benchmark-backed improvement loop, or when a coding agent is about to optimize without a baseline.
metadata:
  short-description: Design the product-Agent optimization loop and generate its diagrams
---

# Agent Evaluation Loop Design

> **Role of this document**
> - **Audience:** the development coding agent setting up a product Agent's optimization loop, or about to claim that Agent got better.
> - **Authority:** normative. The normal path, the design rules and the comparator's exit codes bind an improvement claim.
> - **Tone:** imperative and specific; states and guards with the commands that produce them, and the failure it prevents stated once.
> - **Language:** English.
> - **Contains:** the normal product path, the two-phase lifecycle, the progressive-loading order, diagram generation, comparator invocation and exit codes, and the design rules.
> - **Excludes:** the contract's normative schema (see `references/evaluation-contract.md`), the diagram schema (see `references/agent-architecture-schema.md`), and optimizing this skill itself (see `references/self-bootstrap.md`).

This skill is for the **development coding agent**. It is project-internal and
product-external: nothing it produces belongs in `src/<agent_name>/runtime/`.

It exists to stop one specific failure: declaring a product Agent "improved"
without a contract, without a baseline, without fixed conditions, and without
evidence — or worse, by quietly relaxing the verifier in the same change.

## Start here: the normal product path

Do **not** read the self-bootstrap sections to optimize a normal product Agent.
The default path is:

```text
product goal
  → functional contract
  → functionally complete baseline
  → one fixed condition manifest
  → candidate result
  → compare with current best
  → accept / reject / block / re-measure baseline
```

The minimum artifact at each step:

1. **Product goal** — users, input, output, and what you explicitly do *not*
   claim.
2. **Functional contract** — stable functional checks, required artifacts, and
   the failure taxonomy. Lives in
   `src/<agent_name>/development/evaluation-contract.json`.
3. **Functional baseline** — a working first version. Mediocre quality is fine;
   *unstable input/output or an unstable verifier is not*. If the contract or
   the verifier cannot yet decide pass/fail, the state is
   `FUNCTIONAL_BASELINE_MISSING`, not "a low-performance version".
4. **Fixed condition** — a canonical `condition-manifest.json` pinning
   benchmark, verifier, runtime, provider/model, sampling, repetitions and
   thresholds. Every run-affecting input goes in it.
5. **Candidate result** — produced by an approved runner, secret-free, with
   evidence and provenance. Never hand-write the aggregate; never rewrite a
   provider failure as a product regression.
6. **Compare** — run `compare-evaluations.py`. It validates baseline validity,
   condition identity, samples, evidence and metrics. It does not call a
   provider and does not modify the current best.
7. **Decision** — only evidence under the fixed benchmark conditions can
   produce an acceptance recommendation. Environment/evaluation blocks do not
   update the best. A changed condition means re-measuring the baseline first.
   A product-general claim additionally needs an independent holdout and human
   review.

`hewo` in this repository has an `infrastructure-smoke-only` contract, so the
normal path legitimately stops at `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`. Do not
invent a primary metric just to "enter optimization".

## Cold start comes before either phase

The loop below is the steady state. A product does not begin there. At the
start the product barely works — which the coding agent can see — and the
coding agent's model of the problem and of the product's positioning is
incomplete — which it cannot see. It will read the second failure as a property
of the product and optimize confidently in the wrong direction.

So `COLD_START_HUMAN_IN_LOOP` is on the only path into `CONTRACT_DESIGNED`: the
human is the feedback function until they confirm the problem definition and
the positioning. Do not optimize and do not invent a metric while in cold
start; a metric invented to enter the loop encodes the misunderstanding and
then hides it. Show real, unedited output, state the understanding back in
plain language, and ask about positioning rather than only about tasks.

`UNDERSTANDING_MISMATCH` is the return path. Repeated candidate rejection, or a
baseline that will not stabilize, is more often a misread problem than a weak
candidate; its only exit is back through the human. Neither state is an error
state. `AGENTS.md` carries the normative version of this rule.

## The two-phase lifecycle

Before saying "optimize", separate these:

```text
HUMAN_INTENT_DEFINED → COLD_START_HUMAN_IN_LOOP → CONTRACT_DESIGNED
  → FUNCTIONALLY_COMPLETE_BASELINE_BUILT → BASELINE_MEASURED
  → IMPROVEMENT_HYPOTHESIS_READY → CANDIDATE_IMPLEMENTED
  → CANDIDATE_EVALUATED_ON_FIXED_CONDITIONS → EVIDENCE_VALIDATED
  → COMPARE_WITH_CURRENT_BEST
        ↳ repeated rejection → UNDERSTANDING_MISMATCH → COLD_START_HUMAN_IN_LOOP
```

A paper-writing Agent makes the distinction concrete: "it produces a complete
paper with the required sections" is the functional contract; "the paper is
better" is a performance claim that needs a metric, a baseline, repetitions and
a threshold. Phase one is not a worse version of phase two — it is its
precondition.

## Progressive loading

1. `references/evaluation-contract.md` — normative contract v1, condition
   manifest, result schema, evidence rules, comparator precedence, exit codes.
   Read this before writing or reviewing any contract or result.
2. `references/agent-architecture-schema.md` — what the two diagrams must
   contain, how the generator scans a runtime tree, and the README managed-block
   rules.
3. `references/self-bootstrap.md` — **advanced.** Only for optimizing this
   skill itself. Requires Git archive isolation and a protected evaluator.

## Generate and validate the diagrams

From the repository root:

```bash
python3 .agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py \
  --agent hewo --repo-root . --output-dir . --readme README.md
python3 .agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py \
  --agent hewo --repo-root . --output-dir . --readme README.md --strict
```

`agent-architecture.mmd` answers "what is this product Agent"; it is scanned
from real runtime files, never guessed from prose. `agent-optimization-loop.mmd`
answers "how is it iterated"; it is a state machine with guards, not a
checklist. The `.mmd` files are the single source of truth and README carries
generated blocks only. `--check` fails on drift.

## Compare a candidate

```bash
python3 .agents/skills/agent-evaluation-loop-design/scripts/compare-evaluations.py \
  --contract src/<agent>/development/evaluation-contract.json \
  --current-best <path>/current-best-result.json \
  --candidate <path>/candidate-result.json
```

Exit codes are a contract:

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

`CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE` is a benchmark-local *recommendation*.
`ACCEPTED_AS_CURRENT_BEST` is a lifecycle state reached only through a separate
promotion gate; the comparator never writes it and never updates the best.

## Design rules the coding agent must follow

- Define, before optimizing: product goal, functional contract, functional
  baseline, benchmark identity, execution environment, primary and secondary
  metrics, thresholds, regression rules, repetitions and stop conditions.
- Keep `subject.definition_revision` out of condition identity. Two different
  product revisions compared under identical conditions is the *point*; a
  changed condition is what invalidates a baseline.
- Never fold a provider or infrastructure failure into "the Agent got worse" —
  or into "the Agent got better". `ENVIRONMENT_BLOCKED` and
  `EVALUATION_BLOCKED` update nothing; fix that layer and rerun the same
  candidate.
- Benchmarks measure capability and regression. They are not product identity.
  No benchmark-specific runtime hacks.
- Changing the benchmark, verifier, metric policy, threshold or contract schema
  is an independent design change. It needs human review and it invalidates the
  old baseline. Never bundle it with the candidate that it would make pass.
- One lucky provider response is not an improvement. Repetitions and
  aggregation come from the contract.
- Results across different provider/model/runtime are not comparable by
  default.
- A run with no named credential source is `infrastructure-only` or `blocked` —
  never product-behavior evidence. Real provider-backed E2E goes through
  `docker/run-hewo-e2e.sh` (or the downstream equivalent) and reports backend,
  provider, model and credential-source flag. This skill's static checks need
  no provider at all.

## What this skill is not

`scripts/run-agent-loop.sh` is a stage runner, not a finished automatic
optimizer. This skill adds the design contract, the diagrams, a thin
comparison protocol and a protected self-bootstrap check. It deliberately adds
no LLM client, session manager, approval loop, tool loop or provider adapter.
The runner does keep a registry of detached runs (`--background`,
`--list-runs`, `--run-status`, `--clean-run`) so long provider-backed
validation does not block the developer session; that registry holds
secret-free run metadata and nothing else.

## Downstream use

A downstream repository may copy this skill, but must regenerate its own
diagrams and write its own contract, Agent name, benchmark, identity and
evidence paths. The diagrams committed in this template describe `hewo`; they
are not downstream product facts.
