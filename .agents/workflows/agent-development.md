# Agent Development Workflow

1. Define behavior in identity, skills, knowledge, workflows, memory policy, tools, and permissions before changing runtime code.
2. Build a candidate with `./scripts/build-release.sh example-agent`.
3. Run it in a fresh Docker container without mounting this repository or reusing host OpenCode state.
4. Inject Provider credentials only at runtime.
5. Save final artifacts and scrubbed trajectories, never raw provider sessions or secrets.
6. Classify failures and fix the general definition, then rerun representative tasks and the stable benchmark.
