# Sub-skill: Migrate an Existing Agent Repository

Use this sub-skill when an existing coding-agent repository should adopt this
template's scaffold, runtime boundary, and backend composition model.

## 1. Inventory without changing behavior

Create a migration branch and map the current repository before moving files:

- product identity/system prompt and user-facing instructions;
- skills, knowledge, memory policy, workflows, and product tools;
- backend CLI calls, model clients, session/approval loops, and provider config;
- development-only guidance, tests/benchmarks, credentials, sessions, and
  generated output.

Separate product behavior from development behavior first. Preserve history with
focused `git mv` operations where practical. Never migrate secrets or raw
provider sessions.

## 2. Map to the template contract

Use this target mapping:

| Existing concern | Template destination |
| --- | --- |
| Agent identity/system prompt | `src/<agent>/runtime/identity.md` |
| User-facing skills | `src/<agent>/runtime/skills/<skill>/SKILL.md` |
| Product knowledge | `src/<agent>/runtime/knowledge/` |
| Memory retention policy | `src/<agent>/runtime/memory-policy.md` |
| Product workflows | `src/<agent>/runtime/workflows/` |
| Product-specific tools | `src/<agent>/runtime/tools/` plus a minimal `pyproject.toml` when needed |
| Agent-specific design material | `src/<agent>/development/` |
| Reusable development resources | `.agents/knowledge/`, `.agents/memory/`, `.agents/skills/`, `.agents/workflows/` |
| Development-agent rules | scoped `AGENTS.md` files |

The mapping describes categories, not permission to copy template content.
Initialize downstream development resources from the migrated repository's own
needs. Do not import the template's Issue #1/HeWo memory, template release
history, benchmark evidence, or CI maintenance context. Generic skills may be
copied only after removing hardcoded template names, paths, helper commands,
provider assumptions, and evidence destinations.

Create `src/<agent>/agent.yaml` with the runtime and development directory
declarations. Keep the scaffold self-contained and give it a valid
`runtime/opencode.json` with:

- `$schema: https://opencode.ai/config.json`;
- `default_agent` equal to `<agent>`;
- a matching `agent.<agent>` entry and prompt path;
- `./skills` in the skills list;
- knowledge/workflow instruction paths appropriate to the runtime.

The OpenCode config is part of the scaffold contract even when a run selects
Codex or Claude Code; the template launcher injects the same runtime context
into all supported backends.

## 3. Remove overlapping runtime infrastructure

Replace custom model clients, parallel CLI entrypoints, session managers,
approval loops, and terminal tool loops with the mature backend capabilities
where they cover the requirement. Keep only the thin scaffold/launcher/provider
wiring needed to compose them. If an overlap is genuinely required, record the
concrete backend gap and decision before adding it.

Do not hardcode one provider in the migrated Agent. Select backend, provider,
model, and credentials at runtime. For tools, use the Agent's isolated `uv`
environment rather than the repository's development environment; keep tools
small, deterministic, and credential-free.

## 4. Validate the migration

Run the structural check:

```bash
./scripts/validate-definition.sh <agent>
```

Build the clean image and execute a real provider-backed request through
`docker/run-hewo-e2e.sh` (or the equivalent renamed helper), using the actual
backend/provider intended for the Agent. Verify that runtime identity,
knowledge, skills, workflows, workspace access, and product tools are observed
in the container. A successful build or CLI startup without injected auth is
not migration evidence.

Before release, search for stale paths and forbidden material, then inspect the
payload:

```bash
rg -n "AGENT_NAME|old/runtime/path|old-agent-name" .
AGENT_BACKENDS=opencode,codex,claude \
  ./scripts/build-release.sh <agent> <version>
tar -tzf release/<agent>-<version>.tar.gz
git diff --check
```

The final archive must contain only product runtime behavior, launcher, and
installer. Development instructions, `.agents/`, credentials, sessions, and
private data stay outside the product boundary.
