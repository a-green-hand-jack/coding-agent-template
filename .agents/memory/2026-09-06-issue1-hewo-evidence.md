# Issue #1 HeWo Infrastructure Evidence

Date: 2026-09-06

## Implemented

- Added the self-contained `src/hewo` product definition with a valid OpenCode
  custom agent, runtime skill, knowledge, and workflows.
- Added source/release/remote-bootstrap installation modes. Release installs
  automatically install `opencode-ai@latest` when no system OpenCode binary is
  available; the product launcher also supports CLI and TUI dispatch.
- Added workspace mounting, explicit read-only auth-store mounting, JSON event
  output, and deterministic benchmark execution.
- Release and Docker payloads exclude `AGENTS.md`, development dependencies,
  credentials, and host OpenCode state.

## Verified commands

- `./scripts/validate-definition.sh example-agent`
- `./scripts/validate-definition.sh hello-world`
- `./scripts/validate-definition.sh hewo`
- `./scripts/build-release.sh hewo 0.1.0`
- Isolated release install: `hewo --help`, `hewo --version`, and missing-key
  fail-closed guard passed.
- Isolated bootstrap install from a release archive passed.
- Isolated install with no `opencode` in `PATH` automatically installed
  OpenCode and passed `hewo --help`.
- Docker image build `AGENT_NAME=hewo` passed; final image contains no
  `AGENTS.md` or credential-like files.
- Real Provider-backed benchmark passed with a run-time-injected provider model
  and an explicit read-only auth-store mount. The runtime skill loaded, wrote and re-read
  `/workspace/artifacts/hewo-smoke.md`, the deterministic verifier passed, and
  the scrubbed trajectory contained no unredacted credential marker.
- Final sentinel run also recorded `HEWO_KNOWLEDGE_OK` and
  `HEWO_WORKFLOW_OK` in the artifact, proving knowledge and workflow
  instructions were loaded rather than merely inferred from the task prompt.

The benchmark runner records the model, OpenCode CLI version, definition
revision, artifact path, and scrubbed trajectory path for issue evidence.
