# Benchmark Contract

Benchmarks measure general capability and regression; they do not define product behavior. They are one stage in the project-internal evaluation loop, not the whole loop and not product runtime content. Pin task-set revision, model, runtime, Agent Definition commit, and verifier version for every run. Store only scrubbed trajectories and derived results.

```text
benchmark run -> clean container -> public install.sh -> product command
              -> real task -> artifact + trajectory -> verifier -> report
```
