# Agent Development Workflow

1. Define behavior in identity, skills, knowledge, workflows, memory policy, tools, and permissions before changing runtime code.
2. Validate the definition with `./scripts/validate-definition.sh <agent_name>`.
3. Run it in a fresh Docker container with credentials injected only at runtime through the selected backend's explicit environment variable or read-only auth/key mount.
4. Observe a real provider-backed response; a build or CLI startup alone is infrastructure-only evidence.
5. Build a candidate release with `./scripts/build-release.sh <agent_name> <version>` and inspect the product boundary.
6. Record acceptance evidence in the relevant GitHub issue. Save only scrubbed artifacts or durable lessons needed by this repository, never raw provider sessions or secrets.
7. Classify failures and fix the general definition, then rerun representative tasks and the stable benchmark when that benchmark belongs to the target repository.

This template workflow is not downstream memory. A downstream repository may
adapt the method, but must replace template Agent names, issue history,
benchmarks, provider assumptions, and evidence destinations with its own.
