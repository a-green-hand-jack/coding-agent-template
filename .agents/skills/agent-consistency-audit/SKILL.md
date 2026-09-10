---
name: agent-consistency-audit
description: Audit a coding-agent repository for stale paths, broken links, scaffold/config drift, unsafe runtime contents, and contradictions that require human review.
metadata:
  short-description: Audit Agent memory, skills, tools, and documentation
---

# Agent Consistency Audit

> **Role of this document**
> - **Audience:** the development coding agent auditing this repository after a substantial Agent change, before a template sync, or before release.
> - **Authority:** normative. When to run the audit, and how to classify what it reports, are binding.
> - **Tone:** imperative and procedural; commands with their modes, and a fixed reading for each finding severity.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** when to run the audit, its invocation and modes, phase-aware interpretation, how to read ERROR/WARN/INFO, and the downstream boundary for running it elsewhere.
> - **Excludes:** provider-backed behavior evidence (see `.agents/skills/agent-definition-validation/SKILL.md`), and the checks themselves (see `.agents/skills/agent-consistency-audit/scripts/audit_agent.py`).

Use this skill after a substantial Agent change, before syncing a template
update, or before release. It audits the development repository and its
product boundary; it does not execute the product Agent or read provider
credentials.

## Phase-aware interpretation

The audit can be run during **Phase 0: Initialize** to check scaffold structure
and boundary hygiene. A runtime file containing a neutral
`TODO: replace during implementation` placeholder, or a minimal HeWo smoke
resource explicitly retained as an infrastructure probe, is not evidence that a
product identity or product skill has been implemented. Classify those findings
as initialization state and report them rather than filling them in silently.
Use `structure` for file/configuration findings, `infrastructure` for Docker,
CLI, tool-environment, provider-injection, and model-response findings, and
`agent-behavior` only after Phase 1 product resources have been authorized and
observed. The audit itself never produces `agent-behavior` evidence.

## Run the deterministic audit first

From the repository root:

```bash
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py \
  --agent <agent_name>
```

Useful modes:

```bash
# Fail CI on warnings as well as errors.
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py \
  --agent <agent_name> --strict

# Produce machine-readable findings for CI or another coding agent.
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py \
  --agent <agent_name> --json

# Also inspect a release payload when one has been built.
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py \
  --agent <agent_name> --release release/<agent_name>-<version>.tar.gz
```

The script is intentionally dependency-free. It checks every discovered
`src/<agent>/` definition (or the selected agent), cross-file configuration,
runtime file boundaries, development skill frontmatter, relative Markdown
links, stale template/path markers, shell/Python syntax, and obvious secret
material. It exits non-zero for errors, and for warnings when `--strict` is
used.

## Interpret findings

- **ERROR** means the definition is structurally inconsistent, has a broken
  required reference, or violates a product-boundary invariant. Fix it before
  release.
- **WARN** means a likely stale path, template residue, suspicious document
  reference, or contradiction candidate needs review. Do not silence it by
  deleting history; classify the file as active, historical, or template-only.
- **INFO** records intentionally skipped credential-like files or historical
  references. It is not proof that the content is safe or current.

The audit is deterministic preflight, not semantic proof. For every warning,
read the cited files and decide whether the statements still agree with the
current Agent identity, skills, memory policy, tools, backend/provider contract,
and user/developer documentation. If the change affects runtime behavior,
follow with the real provider-backed Docker E2E required by
`agent-definition-validation`; the audit must never be presented as model
behavior evidence.

When `--release` is supplied, the script also checks that the archive has the
runtime-package manifest, release metadata, and installer, and that development instructions,
`.agents/`, development directories, and credential-like paths are absent.

## Downstream boundary

Run the audit in a downstream repository with its actual Agent name. Replace
template examples, helper names, paths, and evidence destinations before
calling a result clean. Do not copy this skill's reports, template issue
history, HeWo-specific fixtures, or credentials into the downstream project.
