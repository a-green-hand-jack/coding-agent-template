# Development Agent Instructions

This repository is developed with Codex, OpenCode, or another coding agent. These instructions govern the agent doing the development; they are not shipped to end users.

## Boundaries

- Keep every product Agent self-contained under `src/<agent_name>/`.
- Treat `src/<agent_name>/runtime/` as the user-facing release definition.
- Treat `src/<agent_name>/development/` as Agent-specific design material.
- Use `.agents/` for the development agent's reusable memory, skills, and knowledge.
- Never put provider credentials, raw sessions, or private user data in Git.

## Development loop

1. Read the relevant `.agents/knowledge` and `.agents/memory` entries.
2. Select a skill from `.agents/skills` when a workflow matches.
3. Change the target Agent only inside `src/<agent_name>/`.
4. Validate the definition and run the clean-container checks.
5. Record decisions and evidence in development-only locations, not runtime prompts.

Do not add benchmark-specific hacks to runtime behavior. Promote development resources into `src/<agent_name>/runtime/` only after review.
