# Development Agent Resources

This directory is for the coding Agent that develops the product Agent. It is not part of the installed product. Keep reusable development memory, knowledge, and skills here; keep Agent-specific material in `src/<agent_name>/development/`.

- `memory/`: durable development decisions, checklists, and lessons.
- `knowledge/`: repository conventions and technical references.
- `skills/`: reusable coding and validation procedures written as `SKILL.md`.

The root `AGENTS.md` is the entrypoint for these resources.

## Downstream boundary

Do not copy this directory wholesale into a downstream Agent repository.

- Template-only: issue evidence in `memory/`, HeWo-specific history, template
  release decisions, and benchmark/CI maintenance workflows.
- Reusable after review: focused development skills such as
  `template-agent-development` and `agent-definition-validation`.
- Downstream-owned: the downstream repository's own memory, knowledge,
  workflows, provider policy, acceptance evidence, and scoped `AGENTS.md`.

When bootstrapping or synchronizing a downstream Agent, transfer only the
method needed for that repository and replace template names, paths, evidence,
and assumptions. Never treat template development history as downstream
product or development context.
