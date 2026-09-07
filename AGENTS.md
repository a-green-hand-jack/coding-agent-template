# Development Agent Instructions

This repository is developed with Codex, OpenCode, or another coding agent. These instructions govern the agent doing the development; they are not shipped to end users.

## Two distinct identities

- You are the **development coding agent**, maintaining this repository, its infrastructure, and the `src/hewo/` product definition. Do not adopt the product agent's identity or execute its skills merely because you read them as source.
- The **product agent** currently developed here is **hewo**. Its behavior comes only from `src/hewo/runtime/`, excluding all `AGENTS.md` files. `src/<agent_name>/` is a downstream-template placeholder, not a second product location in this repository.
- Every repository `AGENTS.md`, including those under `runtime/`, addresses the development coding agent only. Product identity, skills, and memory policy belong in dedicated runtime files, never these development instructions.
- Installation, release archives, and final Docker images must exclude every `AGENTS.md` from product payloads. Keep the build and release filters aligned.
- Maintain a scoped `AGENTS.md` in every versioned source directory. Do not populate `.git`, dependencies, caches, generated releases, or credential bundles with instructions.
- Use GitHub issues for discussion and acceptance evidence. Do not recreate `docs/` or `tests/`; verify behavior with real Docker E2E tasks, not agent unit tests. Ignore the obsolete install-test step in the legacy development skill.
- A successful image build or CLI startup is not Agent E2E evidence. Before claiming an Agent works, inject the intended development-machine provider runtime through the approved safe path and observe a real model response from the container. If credentials or provider adapters were not actually injected, report the run as infrastructure-only and do not call it a successful Agent test.

## Boundaries

- Keep the current product Agent self-contained under `src/hewo/`. When documenting the reusable downstream template contract, use `src/<agent_name>/` only as a placeholder.
- Treat `src/hewo/runtime/` as the user-facing release definition for this repository.
- Treat `src/hewo/development/` as hewo-specific design material when such a directory is needed.
- Use `.agents/` for the development agent's reusable memory, skills, and knowledge.
- Never put provider credentials, raw sessions, or private user data in Git.

## Reuse-first Agent philosophy

- Build Agent behavior primarily with prompts, skills, memory, knowledge,
  workflows, and tools in the scaffold; do not reimplement a coding-agent
  runtime that an established backend already provides.
- Keep the Agent scaffold, coding-agent backend, and LLM provider/model as
  independent layers. OpenCode, Codex, and Claude Code provide the execution,
  model-adapter, approval, and terminal foundations; this repository should
  add only the composition, runtime injection, and provider wiring needed to
  make those foundations usable by an installed Agent.
- Prefer extending the runtime definition or backend adapter over adding a
  parallel CLI, model client, session manager, or tool loop. Record a concrete
  reason in the issue before introducing infrastructure that overlaps a
  supported backend capability.

## Development loop

1. Read the relevant `.agents/knowledge` and `.agents/memory` entries.
2. Select a skill from `.agents/skills` when a workflow matches.
3. Change the current product Agent only inside `src/hewo/` (and change template infrastructure only when the task concerns the reusable template).
4. Validate the definition and run the clean-container checks.
5. Record decisions and evidence in development-only locations, not runtime prompts.

Do not add benchmark-specific hacks to `src/hewo/runtime/` behavior. Promote development resources into `src/hewo/runtime/` only after review.
