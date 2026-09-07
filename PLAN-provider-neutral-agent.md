# 1. Title and status

- Plan id: `provider-neutral-agent`
- Review state: **Verified**
- Scope: correct the product Agent's provider/backend boundary. Do not change the development coding agent's provider choice. Use pi as the first-choice product backend, while keeping the product definition independent of pi and every specific LLM provider/model.

# 2. Motivation

The intended architecture is:

```text
Product Agent runtime definition -> execution backend (preferred: pi) -> user-selected provider/model
```

The product Agent only defines runtime behavior. The platform or user chooses the backend, provider, model, and credentials. Different models may differ in intelligence, speed, cost, and capability; those differences are runtime characteristics, not product identity.

The development coding agent is different: its developer may freely choose Codex, OpenCode, pi, Claude Code, or another suitable coding agent and LLM. That development choice is not a problem and must not be “normalized” by this change.

The repository should not deliberately implement the product Agent, verifier, or evaluation loop as an MVP, degraded version, incomplete version, or artificially small version once the intended form is known. HeWo itself is intentionally a complete Hello World Agent whose purpose is to exercise the template and test infrastructure; its small functionality is not an unfinished MVP. A smoke task may be small as a test fixture, but the implementation being tested must be complete for its defined purpose.

# 3. Verified current state

- `src/hewo/runtime/identity.md:3` calls hewo a “minimal OpenCode Agent”. This incorrectly couples product identity to a backend.
- `distribution/launcher` has provider/model fallbacks, including an OpenAI provider and fixed models. These are overrideable, but direct product invocation can appear provider-bound.
- `src/hewo/runtime/opencode.json:1-15` is an OpenCode adapter configuration. Its presence is legitimate; it must not be confused with product identity or provider binding.
- `README.md`, `USER.md`, and `DEV.md` already describe the three independent layers, but concrete examples and verified matrices are not always clearly separated from the product contract.
- `.opencode/opencode.jsonc` selects a development model. This is intentionally developer-specific and is outside this plan.
- `docker/run-hewo-e2e.sh` already supports explicit backend/provider/model and safe credential injection. This existing adapter infrastructure should be retained.
- The runtime and development documentation contain “minimal”, “MVP-like”, and “temporary probe” wording. “Minimal” is valid when it describes HeWo's deliberately complete Hello World purpose; MVP/degraded/incomplete framing is not valid as an implementation strategy.

# 4. Pinned decisions and rejected alternatives

## Pinned decisions

- Product runtime must not name or require OpenAI, Anthropic, DeepSeek, pi, OpenCode, a model, an API-key convention, or an auth store as part of product behavior.
- pi is the preferred current backend, not a product dependency. Backend-specific adaptation stays outside product semantics.
- Provider/model and credentials are runtime inputs supplied by the user/platform.
- Concrete provider/model values in documentation or evidence are examples or records of a particular run, never canonical product requirements.
- Development coding-agent configuration remains developer-selected and is not changed.
- Existing backend-specific credential boundaries and fail-closed E2E behavior remain unchanged.
- HeWo is a complete Hello World test Agent. The verifier and loop are also complete deliverables; none may be deliberately degraded or incomplete merely to reach an MVP milestone.

## Rejected alternatives

- Do not force the development coding agent to use pi or a provider-neutral model.
- Do not remove provider/model from E2E evidence; it is needed for reproducibility.
- Do not add a custom LLM client, provider registry, router, or second runtime.
- Do not claim different LLMs provide equivalent quality or speed.
- Do not make pi a hidden requirement merely because it is preferred today.

# 5. Non-goals

- No change to `.opencode/opencode.jsonc` or the developer's preferred coding agent/model.
- No rewrite of pi, OpenCode, Codex, Claude Code, or their provider adapters.
- No removal of historical provider-backed evidence.
- No new product domain behavior.
- No replacement of real provider-backed E2E with unauthenticated checks.

# 6. Work breakdown

## C1 — Remove product-level backend/provider coupling

**Gate:** `./scripts/validate-definition.sh hewo && git diff --check`

- Rewrite `src/hewo/runtime/identity.md` as a provider- and backend-neutral product identity.
- Review runtime descriptions, skills, knowledge, workflows, and tools for provider/model assumptions; remove only assumptions that are product behavior.
- Keep `src/hewo/runtime/opencode.json` as an adapter, but ensure its OpenCode-specific structure is not presented as the product identity.
- Replace final-product “minimal OpenCode Agent” and MVP/degraded/incomplete implementation language with an accurate description of HeWo as a complete Hello World test Agent. Retain “minimal” when it describes intentional scope, and retain “smoke” when it describes a fixture or infrastructure test.

## C2 — Make product execution configuration explicitly user/platform supplied

**Gate:** `bash -n distribution/launcher docker/run-hewo-e2e.sh && git diff --check`

- Review `distribution/launcher` defaults. Product behavior must not silently imply that OpenAI or another provider is required.
- Make pi the first-choice backend at the product entrypoint where a backend default is needed, without making pi part of the runtime definition or product semantics.
- Keep backend-specific namespace and credential handling explicit; do not pretend all backends have identical configuration.

## C3 — Align documentation and acceptance language

**Gate:** `python3 scripts/check-template-registry.py && git diff --check`

- Update `README.md`, `USER.md`, and the relevant product/development guidance to distinguish:
  - product runtime contract;
  - preferred backend;
  - user-selected provider/model;
  - development coding-agent choice;
  - historical or current-run verification evidence.
- Remove wording that presents the product, verifier, or loop as an MVP or unfinished temporary system. Keep small smoke tasks as test fixtures.
- Do not alter the developer's own provider/model configuration.

# 7. File map

- `src/hewo/runtime/identity.md`
- `src/hewo/runtime/README.md` or other runtime behavior files, if present
- `src/hewo/runtime/opencode.json`
- `distribution/launcher`
- `README.md`
- `USER.md`
- `DEV.md`
- `AGENTS.md` only if its product-boundary wording is inaccurate
- `.agents/workflows/agent-development.md` only if its MVP/temporary framing needs correction
- `docker/run-hewo-e2e.sh` only if validation wording requires alignment; preserve its credential logic

# 8. Acceptance criteria

- No product runtime behavior identifies hewo as an OpenCode Agent, pi Agent, or Agent belonging to a specific provider/model.
- Product runtime can be executed through pi without changing its product semantics, while remaining backend-neutral in principle.
- The product contract states that users/platforms supply backend, provider/model, and credentials.
- The development coding agent remains free to use its own coding agent and LLM; `.opencode/opencode.jsonc` is unchanged.
- Backend-specific credential and namespace behavior remains explicit and safe.
- Provider/model values in docs and evidence are clearly labeled as examples or run metadata, not requirements.
- Product, verifier, and loop descriptions do not use MVP/degraded/incomplete implementation framing. HeWo's minimal scope is described as a complete Hello World purpose, and “smoke” remains fixture/infrastructure terminology.
- Existing structural validation passes, and at least one real provider-backed Docker E2E through the approved helper confirms the runtime still works with explicitly supplied backend/provider/model/credential-source metadata.

# 9. Verification

- `./scripts/validate-definition.sh hewo`
- `python3 scripts/check-template-registry.py`
- `bash -n distribution/launcher docker/run-hewo-e2e.sh`
- `git diff --check`
- Search product sources only (especially `src/hewo/runtime/`) for provider/model/backend names and manually classify legitimate adapter configuration.
- Run the approved Docker helper with the preferred pi backend and a provider/model discovered on the host without exposing credentials, using an explicit `--pi-auth-file`, `--api-key-env`, or other approved credential-source flag.
- Inspect the product artifact and report the exact backend/provider/model/credential-source as run metadata, not as a support requirement.
- Run the template release audit if the implementation changes release payload files.

# 10. Risks and open items

- The product entrypoint may choose pi as the first-choice backend for convenience, but must not invent a canonical provider/model default. Provider/model selection remains a user/platform runtime input.
- Different LLMs will not produce identical quality, speed, or tool reliability. The acceptance claim is runtime compatibility, not behavioral equivalence.
- pi may expose provider-specific capabilities. Keep those in backend adaptation and document capability differences without leaking them into product identity.
- Historical evidence may mention old providers. Preserve it as historical evidence unless it is presented as a current product requirement.
- Exact provider/model for E2E must be discovered from the current development machine; never hardcode it in the product definition.

# 11. Reviewer dispositions

| Finding | Reviewer(s) | Disposition | Rationale |
| --- | --- | --- | --- |
| Pending user review | user | deferred | The plan is intentionally presented directly for user review before implementation. |

# 12. Unit execution log

| Commit | Status |
| --- | --- |
| C0 | plan authored / included in implementation commit / push pending / acceptance-checked |
| C1 | implemented / gate-passed (`validate-definition.sh`, runtime review) / included in implementation commit / push pending / acceptance-checked |
| C2 | implemented / gate-passed (`bash -n`, infrastructure health) / included in implementation commit / push pending / acceptance-checked |
| C3 | implemented / gate-passed (`check-template-registry.py`, `git diff --check`) / included in implementation commit / push pending / acceptance-checked |
| C4 | implemented / gate-passed (pi Docker E2E and complete benchmark smoke) / included in implementation commit / push pending / acceptance-checked |
