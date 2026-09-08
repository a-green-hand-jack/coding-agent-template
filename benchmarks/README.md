# Benchmark Contract

Benchmarks measure general capability and regression; they do not define product behavior. They are one stage in the project-internal evaluation loop, not the whole loop and not product runtime content. Pin task-set revision, model, runtime, Agent Definition commit, and verifier version for every run. Store only scrubbed trajectories and derived results.

```text
benchmark run -> clean container -> public install.sh -> product command
              -> real task -> artifact + trajectory -> verifier -> report
```

## Benchmark results are not product claims

A benchmark measures capability and regression under one fixed set of
conditions. It is not product identity and a pass is not a product-general
improvement.

- The evaluation contract, not this directory, decides what counts as an
  improvement. See `.agents/skills/agent-evaluation-loop-design/` and
  `src/<agent_name>/development/evaluation-contract.json`.
- Two runs are comparable only when they reference condition manifests with
  identical canonical bytes. A changed benchmark revision, verifier revision,
  metric policy, provider, model, runtime, image digest, sampling or seed is a
  new condition identity and invalidates the previous baseline.
- Never relax a verifier, edit a task set, or change a metric policy or
  threshold in the same change as the candidate it would make pass. That is an
  independent design change requiring human review and a fresh baseline.
- Never add benchmark-specific behavior to `src/<agent_name>/runtime/`.
- A provider, credential or infrastructure failure is `ENVIRONMENT_BLOCKED`; a
  task-set, verifier or evidence failure is `EVALUATION_BLOCKED`. Neither is a
  product regression and neither updates the current best.
- One response is not a measurement. Repetitions and aggregation come from the
  contract, and the comparator recomputes the mean from the samples rather than
  trusting a self-reported aggregate.
