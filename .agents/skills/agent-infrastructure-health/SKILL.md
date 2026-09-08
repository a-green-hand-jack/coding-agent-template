---
name: agent-infrastructure-health
description: Verify that the template's installer, launcher, Docker image, isolated tools environment, backend binaries, and product boundary work before Agent development focuses on orchestration.
metadata:
  short-description: Prove the coding-agent infrastructure is usable
---

# Agent Infrastructure Health

Use this skill before starting substantial Agent orchestration work, after
changing installer/Docker/backend/tool plumbing, and before handing the
template to a downstream Agent developer. It checks infrastructure separately
from Agent behavior so a product author does not spend time debugging the
execution foundation.

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
launcher help/version behavior, and release payload exclusions. Use
`--skip-build` only when a known-good image was built from the exact current
worktree; the script then reports which image it reused.

Useful options:

```bash
python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py \
  --agent <agent_name> --image <agent_name>:infra --release release/<agent_name>-<version>.tar.gz

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
