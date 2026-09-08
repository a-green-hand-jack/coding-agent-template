# Development Agent Resources

> **Role of this document**
> - **Audience:** the development coding agent orienting itself in `.agents/` before adding or copying a development resource.
> - **Authority:** informative. It maps the directory; the registry and the scoped `AGENTS.md` files are what bind.
> - **Tone:** orienting and brief; a directory map plus the one boundary that is easy to get wrong.
> - **Language:** English.
> - **Contains:** what each subdirectory of `.agents/` holds, and which classes of content may travel to a downstream repository.
> - **Excludes:** product material (see `src/hewo/`), and the authoritative per-path copy list (see `.agents/template-content-registry.json`).

This directory is for the **development coding agent** that maintains this
repository and develops the `hewo` product agent. It is not part of the installed
product. Keep reusable development memory, knowledge, and skills here; keep
hewo-specific product material in `src/hewo/` (and, for a downstream repository,
in that repository's `src/<agent_name>/development/`).

- `memory/`: durable development decisions, checklists, and lessons.
- `knowledge/`: repository conventions and technical references.
- `skills/`: reusable coding and validation procedures written as `SKILL.md`.

The root `AGENTS.md` is the entrypoint for these resources.

## Downstream boundary

Do not copy this directory wholesale into a downstream Agent repository.

Use [`template-content-registry.json`](template-content-registry.json) as the
authoritative allow-list for the entire repository, not only this directory.
The synchronization sub-skill explains how to copy only selected
implementation skills, source scaffold files, and infrastructure, and how to
install the neutral placeholder skeleton under `downstream-skeleton/`.

- Template-only: issue evidence in `memory/`, HeWo-specific history, template
  release decisions, and benchmark/CI maintenance workflows.
- Reusable after review: focused development skills such as
  `template-agent-development`, `agent-definition-validation`, and
  `template-release-readiness`.
- Downstream-owned: the downstream repository's own memory, knowledge,
  workflows, provider policy, acceptance evidence, and scoped `AGENTS.md`.
  The template supplies placeholder files only; replace or remove them before
  recording downstream content.

When bootstrapping or synchronizing a downstream Agent, transfer only the
method needed for that repository and replace template names, paths, evidence,
and assumptions. Never treat template development history as downstream
product or development context.
