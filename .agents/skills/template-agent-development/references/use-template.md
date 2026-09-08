# Sub-skill: Use the Template to Build an Agent

> **Role of this document**
> - **Audience:** the development coding agent bootstrapping a new Agent scaffold in a downstream repository during Phase 0.
> - **Authority:** normative. The Phase 0 scope, the neutral-placeholder rule and the stop-for-authorization condition bind.
> - **Tone:** imperative and procedural; numbered steps ending in an explicit report-and-stop condition.
> - **Language:** English.
> - **Contains:** how to establish the boundary, create the Phase 0 scaffold, compose backend and provider at run time, validate the infrastructure boundary, and write the completion report.
> - **Excludes:** real product identity and domain resources, which Phase 1 authorizes (see `src/<agent>/runtime/`); later template updates and migrations (see `.agents/skills/template-agent-development/references/sync-template.md` and `.agents/skills/template-agent-development/references/migrate-existing-agent.md`).

Use this sub-skill when the target repository is starting a new Agent from the
template or when adding a new `src/<agent>` scaffold. It defines Phase 0
initialization; Phase 1 product implementation and Phase 2 release require
separate authorization and gates.

## 1. Establish the boundary

Confirm the target repository, branch/worktree, and Agent name. Read the root
`AGENTS.md`, the relevant `.agents/knowledge` and `.agents/memory` entries, and
the scoped instructions below `src/`. Do not treat runtime identity or product
skills as instructions for the development coding agent. State that the current
task is **Phase 0: Initialize** and stop after the initialization report; do not
infer authorization for Phase 1.

The installed command is normally the scaffold name. Choose a stable name that
matches `^[a-zA-Z0-9][a-zA-Z0-9._-]*$`; do not plan on a runtime
`--scaffold` registry because the launcher currently selects one installed
scaffold at a time.

## 2. Create the Phase 0 scaffold

Start from the minimal executable scaffold when it is appropriate:

```bash
mkdir -p src/<agent_name>
tar -C src/hewo --exclude=AGENTS.md -cf - . | tar -C src/<agent_name> -xf -
```

This copies executable reference files without development instructions. It is a
scaffold seed, not a permission to preserve the `hewo` identity or ship the
example unchanged; the registry marks `src/hewo/` as a `template-example`.
During Phase 0, retain only the smallest smoke capability needed to probe the
infrastructure. HeWo's name, identity, domain semantics, historical evidence,
and product assumptions must not be inherited.

Create only the structural definition and generic runtime configuration needed to
start the backend. `agent.yaml`, `runtime/package.json`, `identity.md`, and any
placeholder knowledge, skill, workflow, or tool files may exist, but their content
must be neutral and visibly marked `TODO: replace during implementation`. Do not
write the real product identity or domain resources until Phase 1 is authorized.

`runtime/package.json` is the resource manifest: a `pi` section for what pi
loads natively, and an `agent` section for everything pi has no primitive for.
A non-pi backend configuration file must not exist in the runtime;
`scripts/validate-definition.sh` rejects one.

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

The Phase 0 scaffold must not add domain tools, business execution logic,
benchmarks, product acceptance evidence, or release-ready behavior. Do not modify
the backend execution loop, model client, session, approval, or tool loop.

## 3. Compose backend and provider at runtime

Do not bake a provider or model into the scaffold. The backend is pi and only
pi; the provider and model are chosen per run:

```bash
hewo --provider openai --model gpt-5.5 "<task>"
```

For a downstream Agent, replace `hewo` with its installed command. `--backend`
accepts only `pi` (alias `pi-coding-agent`) and errors on anything else, so a
second backend is never a silent fallback. Never copy auth stores into the
scaffold.

## 4. Validate the Phase 0 infrastructure boundary

Run the structural checks first:

```bash
./scripts/validate-definition.sh <agent_name>
```

Then run a real provider-backed Docker request. Supply credentials with an
explicit environment variable or read-only auth/key file; do not print the
value or commit it. For example:

```bash
./docker/run-hewo-e2e.sh \
  --agent <agent_name> \
  --provider openai \
  --model gpt-5.5 \
  --pi-auth-file "$HOME/.pi/agent/auth.json" \
  "Reply with exactly: hi"
```

The helper accepts `--pi-auth-file`, `--api-key-env`, `--api-key-stdin`, and
`--bundle` as credential sources; anything else exits 2. Label directory
and configuration checks `structure`. Label Docker, CLI, tool-environment,
provider-injection, and model-response checks `infrastructure`. An image build,
CLI startup, tool check, or provider response is never `agent-behavior` evidence;
that label is reserved for Phase 1 after product resources are authorized and
defined. Do not claim that the downstream Agent is implemented from Phase 0
responses.

## 5. Phase 0 completion report and stop condition

The initialization gate requires valid directories and configuration, a buildable
Docker image, a startable backend CLI, and a response from each requested
provider-backed request. It must also show that no product behavior is declared
and that the product boundary is credential-free.

The report must list:

- files created during initialization;
- registry entries reused;
- template-specific content explicitly excluded;
- retained HeWo smoke content and its status as infrastructure-only;
- backend/provider E2E results and evidence labels;
- product content not yet implemented; and
- decisions requiring user authorization for Phase 1.

After the report and infrastructure checks, stop. Wait for an explicit instruction
such as “开始实现 Agent 产品行为” before entering Phase 1. Do not automatically
design identity, skills, knowledge, workflows, tools, benchmarks, or release
behavior.

## 6. Phase 1 and Phase 2 gates

After explicit authorization, Phase 1 may replace the TODO placeholders with the
user-approved identity, skills, knowledge, workflows, and tools. Run definition
validation, consistency audit, and real provider-backed Docker E2E, and collect
`agent-behavior` observations before claiming product implementation. Start Phase 2
release work only after that gate and separate release authorization.

## 7. Prepare a release (when requested)

Build only the selected Agent's runtime payload:

```bash
./scripts/build-release.sh <agent_name> <version>
```

`AGENT_BACKENDS` is accepted only as `pi` and is rejected otherwise, so leave
it unset.

Inspect the archive and confirm it contains runtime definition, launcher, and
installer only. It must not contain `AGENTS.md`, `.agents/`, development
directories, package metadata, credentials, or raw provider sessions.
