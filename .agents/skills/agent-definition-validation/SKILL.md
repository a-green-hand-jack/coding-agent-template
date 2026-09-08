---
name: agent-definition-validation
description: Validate a changed Agent definition or release with the repository's structural checks, clean Docker runtime, and real provider-backed behavior evidence.
metadata:
  short-description: Validate an Agent definition and release boundary
---

# Agent Definition Validation

> **Role of this document**
> - **Audience:** the development coding agent validating a changed `src/<agent_name>/` definition or preparing that Agent's release.
> - **Authority:** normative. The validation levels, the evidence boundary and the exit condition are binding.
> - **Tone:** imperative and procedural; commands, and the exact label a run's evidence is allowed to carry.
> - **Language:** English.
> - **Contains:** the four validation levels with their commands, the credential-source flag every E2E must name, the evidence boundary, and the exit condition.
> - **Excludes:** the cross-file freshness sweep (see `.agents/skills/agent-consistency-audit/SKILL.md`), infrastructure preflight (see `.agents/skills/agent-infrastructure-health/SKILL.md`), and host credential facts (see `.agents/knowledge/provider-e2e.md`).

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
   Inject the credential through one explicit flag (`--pi-auth-file`,
   `--api-key-env`, `--api-key-stdin`, or `--bundle`), never an ad-hoc
   `docker run` and never a bare host CLI. The helper fails
   closed without a credential source; pass `--allow-unauthenticated` only for
   infrastructure-only smokes (build/`--help`). Observe the model response and
   inspect any requested workspace artifact.

4. When release contents changed, build, inspect, and publish a fresh release.
   The product iterates quickly, so publish a git tag plus GitHub release after
   every accepted product-behavior change instead of accumulating unreleased
   changes:

   ```bash
   ./scripts/build-release.sh <agent_name> <version>
   tar -tzf release/<agent_name>-<version>.tar.gz
   ./scripts/publish-release.sh <agent_name> <version>
   ```

   Prefer the one-shot `publish-release.sh`: it runs the definition check,
   builds with the correct `RELEASE_URL`, tags, pushes the tag, and creates the
   GitHub release. Do not treat a bare build or archive inspection as a
   published release.

## Evidence boundary

- An image build, binary version check, or run without a real provider is
  infrastructure-only evidence, not a successful Agent E2E.
- Name the exact credential-source flag used (e.g.
  `--pi-auth-file ~/.pi/agent/auth.json`) in the evidence. A run for which you
  cannot name the backend/provider/model and its credential source is `blocked`
  or `infrastructure-only`, never E2E-passed.
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
revision, and artifact without exposing credentials. If no provider credential
was injected, report `infrastructure-only` or `blocked` and stop; never mark
the Agent E2E passed.
