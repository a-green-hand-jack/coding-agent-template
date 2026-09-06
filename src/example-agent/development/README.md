# Development Resources

This directory is used while designing and evaluating the Agent. It is intentionally kept inside the Agent folder so each Agent remains self-contained.

- `memory/`: temporary working memory and project state policy.
- `knowledge/`: references, domain notes, and templates.
- `skills/`: development-only skills and experiments.
- `workflows/`: development and evaluation workflows.

The release installer copies only `runtime/`; these files are not exposed to end users unless deliberately promoted into the runtime definition.
