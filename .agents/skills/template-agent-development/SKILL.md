---
name: template-agent-development
description: Use when creating, synchronizing, or migrating a coding-agent repository with this template's independent scaffold, backend, and LLM layers.
metadata:
  short-description: Build and maintain agents from the coding-agent template
---

# Template Agent Development

Use this skill for development work on a repository based on
`a-green-hand-jack/coding-agent-template`. It guides the development coding
agent; it is not product-agent behavior and must never be copied into a
release or Docker product payload.

## Progressive disclosure

Select one sub-skill from the user's immediate intent and read only that file:

- New Agent from this template: [use-template.md](references/use-template.md)
- Bring template changes into an existing downstream repository:
  [sync-template.md](references/sync-template.md)
- Move an existing coding-agent repository onto this template:
  [migrate-existing-agent.md](references/migrate-existing-agent.md)

Do not load all three sub-skills unless the task explicitly combines their
workflows. Return to this file only for the shared contract below.

## Shared contract

- Keep the layers independent:
  `Agent scaffold -> coding-agent backend -> LLM provider/model`.
- Put user-facing product behavior under `src/<agent>/runtime/`. Keep reusable
  development memory, knowledge, skills, and workflows in `.agents/`; keep
  Agent-specific design material in `src/<agent>/development/`.
- Do not copy the template's `.agents/` wholesale into a downstream repository.
  Template issue evidence, HeWo history, release decisions, and benchmark/CI
  maintenance context remain here. A downstream repository creates its own
  memory, knowledge, workflows, and evidence, and copies only reviewed generic
  skills it still needs.
- `AGENTS.md` files guide the development coding agent only. They must be
  excluded from installation, release archives, and final Docker images.
- Follow the reuse-first principle. Extend the runtime definition or a thin
  backend adapter before adding a parallel CLI, model client, session manager,
  approval loop, or tool loop already provided by OpenCode, Codex, Claude Code,
  or another supported backend.
- Never put provider credentials, auth stores, raw sessions, `.env` files, or
  private user data in Git, runtime definitions, release archives, or images.
  Inject credentials only at execution time.
- A successful build or CLI startup is not Agent E2E evidence. When claiming
  behavior, run a real Docker request with the intended provider/auth injected
  through the safe path and observe the model response. If no provider runtime
  was injected, call the result infrastructure-only.
- Prefer the repository's current checks (`scripts/validate-definition.sh`,
  Docker E2E, and release inspection). Do not revive the obsolete install-test
  workflow or add an Agent unit-test suite.

## Completion gate

Before handing off a change, the selected sub-skill must leave:

1. A valid `src/<agent>/agent.yaml` and runtime definition.
2. A clean, credential-free product boundary.
3. Validation evidence appropriate to the changed backend/runtime.
4. Any unresolved provider, migration, or history conflict reported instead of
   silently being dropped.
