---
name: development-provider-usage
description: Use at the start of product-Agent development, validation, or provider-backed debugging to proactively confirm which LLM providers/models the development coding agent already has available, before choosing or configuring a provider.
metadata:
  short-description: Proactively confirm available development LLM providers
---

# Development Provider Usage

> **Role of this document**
> - **Audience:** the development coding agent maintaining or evaluating a product Agent repository.
> - **Authority:** normative for proactively checking the development machine's available LLM providers before using them.
> - **Tone:** imperative and lightweight; confirm first, then act.
> - **Language:** 中文（代码、命令、协议标识保留原文）。
> - **Contains:** when to check existing providers, how to enumerate them safely, how to choose among them, and what evidence to report.
> - **Excludes:** product-agent behavior, credential provisioning, and broad provider migration procedures.

Use this skill whenever you are about to develop, validate, debug, or compare a product Agent with an LLM-backed run. Its main purpose is to stop the development coding agent from guessing which provider/model exists, relying on stale memory, or silently using a default account.

## 主动确认规则

Before the first provider-backed action in a task, proactively confirm the current development-machine provider situation. Do this even when you think you know the answer.

Confirm at least:

1. **Host and tool surface** — active host, repository, and which backend/client will run the request (`pi`, `opencode`, `claude-code`, Docker E2E helper, etc.).
2. **Repository preference** — read `.agents/knowledge/development-provider-preferences.md` and identify the preferred provider/model for the task class.
3. **Visible providers** — the providers/models that are currently visible to that client.
4. **Default resolution** — what provider/model would be used if you do not pass an explicit model.
5. **Credential source class** — whether the intended run can be tied to a safe credential source label or helper flag, without printing the credential.
6. **Known blockers** — missing provider, stale catalog, quota/rate limit, endpoint maintenance, or missing injection path.

If the task is quick and provider-backed evidence is not needed, do not run a live prompt; just confirm visibility when model choice matters.

## Safe confirmation commands

Use secret-free enumeration and allowlisted helper scripts. Prefer commands like:

```bash
pi --list-models
opencode models <provider>
opencode models <provider> --verbose
claude --version
```

For product Agent E2E, prefer the repository helper (for this template, `docker/run-hewo-e2e.sh` or the downstream renamed equivalent) with an explicit credential-source flag. Host CLI checks are provider diagnostics, not product behavior evidence.

Never run commands that print resolved secrets or auth stores. In this environment, do **not** run `opencode debug config`, do not read key files, do not print auth JSON, and do not dump `.env` files.

Load the matching private provider skill when the task requires details beyond enumeration:

- `pi-providers-private` for Pi provider setup or drift.
- `opencode-providers-private` for OpenCode provider setup or drift.
- `docker-providers-private` for container/provider injection.
- Claude Code provider checks must be confirmed independently; do not infer them from OpenCode.

## Selection protocol

After confirming availability, choose the provider/model deliberately:

- Prefer an explicit `provider/model` for evidence-producing runs.
- If you use a default, state the resolved default in the report.
- Do not assume `pi`, `opencode`, `claude-code`, and Docker bundles expose the same catalog.
- Do not assume a MacBook provider fact applies on Ubuntu, or the reverse.
- Do not change provider configuration just because a request fails. First classify whether the failure is configuration drift, credentials, quota, endpoint health, model availability, or product behavior.

## Minimal evidence labels

Use these labels when reporting provider checks:

- `provider-visible`: the provider/model appears in a safe model listing.
- `provider-live`: a minimal live prompt returned the expected response.
- `infrastructure-only`: backend/provider plumbing ran, but product behavior was not exercised.
- `agent-behavior`: the product Agent was run through the repository E2E path with explicit provider injection and the observed response/artifacts match the requested behavior.
- `blocked`: validation could not proceed because of credentials, quota, model availability, endpoint health, or missing injection path.

Do not upgrade labels: visible is not live; live provider response is not product Agent behavior; a build/startup is not E2E evidence.

## Report checklist

When provider-backed evidence matters, report:

- host/device;
- backend/client and command/helper;
- provider/model, preferably fully qualified;
- credential-source flag or non-secret credential source label;
- evidence label;
- result or blocker.

If a credential is accidentally printed, stop, do not repeat it, identify the credential class, and recommend rotation.
