# Sub-skill: Use the Template to Build an Agent

Use this sub-skill when the target repository is starting a new Agent from the
template or when adding a new `src/<agent>` scaffold.

## 1. Establish the boundary

Confirm the target repository, branch/worktree, and Agent name. Read the root
`AGENTS.md`, the relevant `.agents/knowledge` and `.agents/memory` entries, and
the scoped instructions below `src/`. Do not treat runtime identity or product
skills as instructions for the development coding agent.

The installed command is normally the scaffold name. Choose a stable name that
matches `^[a-zA-Z0-9][a-zA-Z0-9._-]*$`; do not plan on a runtime
`--scaffold` registry because the launcher currently selects one installed
scaffold at a time.

## 2. Create the scaffold

Start from the minimal executable scaffold when it is appropriate:

```bash
mkdir -p src/<agent_name>
tar -C src/hewo --exclude=AGENTS.md -cf - . | tar -C src/<agent_name> -xf -
```

This copies the executable reference files without its development
instructions. It is a scaffold seed, not a permission to preserve the `hewo`
identity or ship the example unchanged; the registry marks `src/hewo/` as a
`template-example`.

Then update all identity-bearing values:

- `src/<agent_name>/agent.yaml`: `name`, `runtime_dir`, `development_dir`, and
  runtime subdirectory declarations.
- `src/<agent_name>/runtime/opencode.json`: `default_agent`, the matching
  `agent.<agent_name>` key, prompt path, skills path, and instructions paths.
- `src/<agent_name>/runtime/identity.md`: the product Agent's role and claims
  boundary.
- `runtime/knowledge/`, `runtime/skills/`, and `runtime/workflows/`: only
  user-facing resources that should ship with the Agent.

Keep product resources self-contained under `src/<agent_name>/`. Development
guidance belongs in scoped `AGENTS.md` files or `.agents/`, never in runtime
prompts. A product tool may live under `runtime/tools/` with its own
`pyproject.toml`; the installer creates its isolated `uv` environment and the
launcher places that environment on `PATH`. Do not make it depend on the root
development `.venv`.

Before treating the result as a downstream repository, remove or replace
template-only material rather than inheriting it as Agent context:

- read `.agents/template-content-registry.json` and install only its selected
  entries; use `.agents/downstream-skeleton/` for neutral placeholders;
- replace HeWo identity, smoke skills, workflows, artifacts, and benchmark
  assumptions with the downstream Agent's behavior;
- do not copy `.agents/memory/2026-09-06-issue1-hewo-evidence.md` or other
  template issue/release history;
- create downstream-specific `.agents/knowledge`, `.agents/memory`, and
  `.agents/workflows` entries only when that repository needs them;
- retain a generic development skill only after reviewing its Agent names,
  paths, helper names, provider assumptions, and evidence destination.

## 3. Compose backend and provider at runtime

Do not bake a provider or model into the scaffold. The same command can select
the mature coding-agent backend at runtime:

```bash
hewo --backend opencode --provider opencode-go --model glm-5.3 "<task>"
hewo --backend codex --model gpt-5.5 "<task>"
hewo --backend claude --model sonnet "<task>"
```

For a downstream Agent, replace `hewo` with its installed command. `--provider`
is an OpenCode provider selector; Codex and Claude Code keep their own model
and credential namespaces. Never copy auth stores into the scaffold.

## 4. Validate behavior

Run definition validation first:

```bash
./scripts/validate-definition.sh <agent_name>
```

Then run a real provider-backed Docker request. Supply credentials with an
explicit environment variable or read-only auth/key file; do not print the
value or commit it. For example:

```bash
./docker/run-hewo-e2e.sh \
  --agent <agent_name> \
  --backend opencode \
  --provider opencode-go \
  --model glm-5.3 \
  --auth-file "$HOME/.local/share/opencode/auth.json" \
  "Reply with exactly: hi"
```

Use the backend-specific credential option for Codex or Claude. A Docker image
build alone, or a run without injected provider credentials, is only
infrastructure evidence. Confirm the task response and inspect any requested
artifact in the clean workspace.

## 5. Prepare a release (when requested)

Build only the selected Agent's runtime payload:

```bash
AGENT_BACKENDS=opencode,codex,claude \
  ./scripts/build-release.sh <agent_name> <version>
```

Inspect the archive and confirm it contains runtime definition, launcher, and
installer only. It must not contain `AGENTS.md`, `.agents/`, development
directories, package metadata, credentials, or raw provider sessions.
