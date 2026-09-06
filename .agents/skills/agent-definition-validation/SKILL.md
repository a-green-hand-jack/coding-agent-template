---
name: agent-definition-validation
description: Validate a changed Agent definition or release with the repository's structural checks, clean Docker runtime, and real provider-backed behavior evidence.
metadata:
  short-description: Validate an Agent definition and release boundary
---

# Agent Definition Validation

Use after changing `src/<agent_name>/` or before releasing that Agent. Resolve
the actual Agent name and current repository commands first; do not hardcode
the template's `hewo` example in a downstream repository.

For broad cross-file freshness and contradiction candidates, run
`agent-consistency-audit` before this focused validation. This skill remains
responsible for runtime/provider E2E evidence and release-boundary confirmation.

Before provider-backed behavior testing, run `agent-infrastructure-health` when
the installer, launcher, Docker image, backend packages, or runtime tools have
changed. It proves the execution foundation is usable without handling provider
credentials.

## Validation levels

1. Validate the definition structure:

   ```bash
   ./scripts/validate-definition.sh <agent_name>
   ```

2. Build the clean Docker image when runtime, tools, launcher, dependencies, or
   packaging changed:

   ```bash
   docker build --build-arg AGENT_NAME=<agent_name> \
     -t <agent_name>:e2e -f docker/Dockerfile .
   ```

3. Before claiming Agent behavior, run a real request through
   `docker/run-hewo-e2e.sh` or the downstream repository's renamed equivalent.
   Inject only the selected backend's credential through an explicit runtime
   environment variable or read-only auth/key mount. Observe the model response
   and inspect any requested workspace artifact.

4. When release contents changed, build and inspect a fresh archive:

   ```bash
   AGENT_BACKENDS=opencode,codex,claude \
     ./scripts/build-release.sh <agent_name> <version>
   tar -tzf release/<agent_name>-<version>.tar.gz
   ```

## Evidence boundary

- An image build, binary version check, or run without a real provider is
  infrastructure-only evidence, not a successful Agent E2E.
- Record acceptance evidence in the relevant GitHub issue. Add a durable
  `.agents/memory/` entry only when the repository needs the decision or lesson
  for future development; do not store raw provider output, credentials, or
  sessions there.
- Template-specific HeWo/Issue #1 evidence stays in the template repository and
  must not be copied into a downstream Agent project.
- Release and Docker payloads must exclude every `AGENTS.md`, `.agents/`,
  development directory, credential, raw session, and private user file.
- Do not restore the removed `tests/install/test-install.sh` workflow or create
  an Agent unit-test suite as a substitute for real Docker E2E.

## Exit condition

The applicable structural, runtime, behavior, and release-boundary checks pass;
the evidence identifies the actual Agent, backend, provider/model, runtime
revision, and artifact without exposing credentials.
