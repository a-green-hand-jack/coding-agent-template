---
name: template-agent-development
description: Use when creating, synchronizing, or migrating a coding-agent repository with this template's independent scaffold, backend, and LLM layers.
metadata:
  short-description: Build and maintain agents from the coding-agent template
---

# Template Agent Development

Use this skill as instructions for the **development coding agent**, never as
product-agent behavior. In this template repository, the concrete product agent
is `hewo` and product changes belong under `src/hewo/`; the `src/<agent>/`
paths below are placeholders used only when this skill is adapted downstream.

## Explicit phase model

Downstream work proceeds through three user-visible phases:

- **Phase 0: Initialize** — create the smallest runnable scaffold and verify the
  infrastructure boundary. HeWo smoke resources may be retained temporarily as
  probes, but no product behavior is designed. The coding agent stops after the
  initialization report and waits for explicit authorization.
- **Phase 1: Implement product behavior** — after explicit user authorization,
  define the product identity and user-facing skills, knowledge, workflows, and
  tools, then collect real Agent behavior evidence.
- **Phase 2: Release** — package and publish the authorized product runtime after
  the product implementation gates pass.

Use these evidence labels consistently: `structure` covers files, configuration,
and directory checks; `infrastructure` covers Docker, CLI, tool environment,
provider injection, and model responses; `agent-behavior` covers observed product
identity, skills, workflows, and tool behavior. Phase 0 may produce only
`structure` and `infrastructure` evidence. A provider response alone is never
`agent-behavior` evidence.

## Progressive disclosure

Select one sub-skill from the user's immediate intent and read only that file:

- New Agent from this template: [use-template.md](references/use-template.md)
- Bring template changes into an existing downstream repository:
  [sync-template.md](references/sync-template.md)
- Move an existing coding-agent repository onto this template:
  [migrate-existing-agent.md](references/migrate-existing-agent.md)

Do not load all three sub-skills unless the task explicitly combines their
workflows. Return to this file only for the shared contract below.

Before synchronizing or bootstrapping a downstream repository, read the
authoritative content registry at
`.agents/template-content-registry.json`. It defines what is template-only,
what is selectively reusable, which reference scaffolds need adaptation, and
which neutral placeholders may be installed. It covers the entire repository,
not only `.agents/`; run `python3 scripts/check-template-registry.py` after
adding tracked template files.

Before publishing a template version, also load
`.agents/skills/template-release-readiness/SKILL.md` for the repository-wide
compatibility and leakage gates.

If the target repository is not going to publish an Agent, do not apply the
scaffold or product-release contract from this skill. Use the non-Agent
infrastructure reuse prompt in `DEV.md`, then selectively adapt only the
infrastructure and development skills the target project needs.

## Shared contract

- Keep the layers independent:
  `Agent scaffold -> coding-agent backend -> LLM provider/model`.
- Put user-facing product behavior under `src/hewo/runtime/` in this repository
  (or under `src/<agent>/runtime/` after adapting this skill downstream). Keep
  reusable development memory, knowledge, skills, and workflows in `.agents/`;
  keep Agent-specific design material in `src/hewo/development/` here.
- Do not copy the template's `.agents/` wholesale into a downstream repository.
  Follow `.agents/template-content-registry.json`: install only explicitly
  selected skills, and bootstrap downstream-owned memory, knowledge, and
  workflows from neutral placeholders. Template issue evidence, HeWo history,
  release decisions, and benchmark/CI maintenance context remain here.
- `AGENTS.md` files guide the development coding agent only. They must be
  excluded from installation, release archives, and final Docker images.
- Follow the reuse-first principle. Extend the runtime definition or a thin
  backend adapter before adding a parallel CLI, model client, session manager,
  approval loop, or tool loop already provided by pi, which is the only
  supported backend.
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

## Component choice before code

The product Agent is a composed runtime, not a bag of scripts. Before
implementing any requirement, record a component choice and its rationale using
the decision tree in `.agents/knowledge/pi-runtime-component-contract.md`:
declarative resource, then pi-native configuration, then a thin TypeScript
extension, then a leaf script, then an external CLI. Descend a level only after
writing down why the level above cannot express the requirement.

Going straight to a script requires a recorded backend-capability gap naming the
pi primitive that should have covered it. A leaf script may never own the agent
loop, sessions, model calls, approval loops, sub-agent orchestration, product
identity, long-lived state, or cross-component orchestration.

The backend is pi and only pi. `src/<agent_name>/runtime/package.json` is the
single source of truth for what the runtime loads; `agent.yaml` stays scaffold
metadata and must never grow a second resource list.

## Completion gates

The Phase 0 initialization gate is satisfied only when the downstream repository
has valid directories and configuration, a Docker image can build, the backend CLI
can start, and each requested provider-backed request returns a response. The
report must label these results `structure` or `infrastructure`, state that no
product behavior is declared, and stop for user authorization. A clean,
credential-free product boundary and any unresolved provider or history conflict
must also be reported.

The Phase 1 product implementation gate is separate. It requires user-authorized
identity, skills, knowledge, workflows, and tools, followed by definition
validation, consistency audit, and real provider-backed Docker E2E that observes
`agent-behavior`. These checks are product acceptance evidence only after the
behavior has been defined; they are not initialization requirements.

Phase 2 release work starts only after the Phase 1 gate and explicit release
authorization. Release payload inspection must still confirm the credential-free
product boundary and exclusion of development instructions.
