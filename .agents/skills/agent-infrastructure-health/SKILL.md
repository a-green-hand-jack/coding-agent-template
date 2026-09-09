---
name: agent-infrastructure-health
description: Verify that the template's installer, launcher, Docker image, isolated tools environment, backend binaries, and product boundary work before Agent development focuses on orchestration.
metadata:
  short-description: Prove the coding-agent infrastructure is usable
---

# Agent Infrastructure Health

> **Role of this document**
> - **Audience:** the development coding agent proving the execution foundation works before Agent orchestration, or before handing the template to a downstream developer.
> - **Authority:** normative. The preflight, the separate provider-backed gate, and the blocking readiness rule are binding.
> - **Tone:** imperative and procedural; commands with what each one proves and, explicitly, what it does not.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** when to run the deterministic preflight, its invocation and options, why the provider-backed smoke is a separate gate, and how to treat the readiness result.
> - **Excludes:** provider-backed behavior evidence itself (see `.agents/skills/agent-definition-validation/SKILL.md`), stale and contradictory content (see `.agents/skills/agent-consistency-audit/SKILL.md`), and credential-injection detail (see `.agents/knowledge/provider-e2e.md`).

Use this skill before starting substantial Agent orchestration work, after
changing installer/Docker/backend/tool plumbing, and before handing the
template to a downstream Agent developer. It checks infrastructure separately
from Agent behavior so a product author does not spend time debugging the
execution foundation.

架构边界：pi 是唯一 backend；安装验证应确认 pi-native runtime/package 已交付。provider、model、credentials 与 host infrastructure 由用户负责，HeWo wrapper 不是产品入口。

## Deterministic preflight

From the repository root, run:

```bash
python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py \
  --agent hewo
```

The check validates required infrastructure files, shell/Python syntax, the
Agent definition, host prerequisites for declared runtime tools, the tool
self-checks the runtime manifest declares in `agent.tool_checks`, a clean Docker
build, the final image's pi binary, the isolated `uv` tool environment,
launcher help/version behavior, and release payload exclusions. Pass
`--skip-build --image <image-id>` to reuse an image already built from a frozen
snapshot by `./scripts/build-agent-image.sh`; the tag is content addressed, so
matching an image to its source is no longer something the operator has to
remember. `--skip-build` asserts the image exists and fails if it does not.

Useful options:

```bash
python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py \
  --agent <agent_name> --image <agent_name>:def-<digest> --release release/<agent_name>-<version>.tar.gz

python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py \
  --agent <agent_name> --skip-build --json
```

The script never reads or injects provider credentials. A successful preflight
proves only that the execution foundation is wired correctly.

## Provider-backed smoke is a separate gate

After the deterministic preflight, run at least one real Docker request through
`docker/run-hewo-e2e.sh` (or the downstream renamed helper) with the intended
provider/model and an explicit runtime key or read-only auth mount. Verify the
actual model response and any workspace artifact. Exercise every provider/model
the downstream Agent promises to support; the backend is always pi. A build,
`--help`, or binary version check without provider injection is
infrastructure-only evidence.

The helper fails closed without a credential source: pass one explicit flag
(`--pi-auth-file`, `--api-key-env`, `--api-key-stdin`, or `--bundle`) and
record the exact flag plus backend/provider/model used. `--allow-unauthenticated`
is for infrastructure-only smokes only and never counts as provider-backed
evidence.

Use `agent-definition-validation` for this provider-backed behavior evidence and
`agent-consistency-audit` for stale, contradictory, or template-residue
content. Do not turn this health check into a duplicate model client or tool
loop.

## Readiness result

Treat `ERROR` as blocking. Treat a provider-backed smoke failure as blocking
even when deterministic preflight passes. Keep raw provider output, credentials,
auth stores, and reports outside Git; record only scrubbed acceptance evidence
in the repository's normal development evidence location.
