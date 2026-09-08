# Coding Agent Template

这是一个用于构建可安装 Agent 的开发仓。当前仓库只有一个被开发和交付的产品
agent：**hewo**；它的全部产品源码位于 `src/hewo/`，行为定义位于
`src/hewo/runtime/`。其他目录不是 hewo 的产品实现：`AGENTS.md`、`.agents/`
是维护本仓库的开发 coding agent 使用的开发指令和资源，`scripts`、`docker`、
`benchmarks`、`distribution` 是 template 基础设施。


This repository has two strictly separate identities. The **development coding agent** maintains this repository and follows `AGENTS.md` plus `.agents/`. The **product agent** is `hewo`, what users install and run; it follows only the definition under `src/hewo/runtime/`. Development instructions are never product behavior, and all `AGENTS.md` files are excluded from installation, release archives, and final Docker images.

For downstream repositories, the same product boundary is renamed to
`src/<agent_name>/runtime/`; that placeholder describes how this template is
reused, not an additional product in this repository.


```bash
cp .env.example .env
./scripts/validate-definition.sh hewo
docker build --build-arg AGENT_NAME=hewo -t hewo:dev -f docker/Dockerfile .
docker run --rm -it --env-file .env hewo:dev "Say hello to Ada"
```

The `run-hewo-e2e.sh` helper accepts any OpenCode provider and model without requiring manual exports:

```bash
./docker/run-hewo-e2e.sh --agent hewo --provider openai --model gpt-5.5 --api-key-env OPENAI_API_KEY "完成这个任务"
```

`hewo` can use the same complete Hello World runtime with four interchangeable
coding-agent backends. pi is the first-choice backend; OpenCode, Codex, and
Claude Code are also available and selected with `--backend` (or
`AGENT_BACKEND`). The user/platform supplies the provider, model, and
credentials at runtime. Each backend keeps its own model namespace and
credential boundary:

```bash
# OpenCode: provider/model plus an explicit read-only auth store
./docker/run-hewo-e2e.sh --agent hewo --backend opencode --auth-file "$HOME/.local/share/opencode/auth.json" "hi"

# Codex CLI: Codex model plus an explicit read-only Codex auth store
./docker/run-hewo-e2e.sh --agent hewo --backend codex --codex-auth-file "$HOME/.codex/auth.json" --model gpt-5.5 "hi"

# Claude Code: Claude model plus a runtime API key (or a read-only key file)
./docker/run-hewo-e2e.sh --agent hewo --backend claude --api-key-env ANTHROPIC_API_KEY --model sonnet "hi"
# ./docker/run-hewo-e2e.sh --agent hewo --backend claude --claude-api-key-file /path/to/key --model sonnet "hi"

# pi with an existing read-only pi auth store
./docker/run-hewo-e2e.sh --agent hewo --backend pi \
  --provider openai-codex --model gpt-5.5 \
  --pi-auth-file "$HOME/.pi/agent/auth.json" "hi"
```

The product launcher also accepts `hewo --backend codex ...`,
`hewo --backend claude ...`, `hewo --backend pi ...`, and `hewo --backend opencode ...`. In all four
cases the launcher injects the same runtime Identity, Knowledge, Skills and
Workflows; only the underlying coding-agent CLI and model/provider adapter
changes. The Docker image uses a Node 22 runtime because the current Claude
Code package requires Node 22 or newer.

The scaffold, coding-agent backend, and LLM provider are deliberately
independent layers. HeWo is a complete, intentionally scoped Hello World
Agent—not a deliberately degraded or incomplete version—and the concrete
provider/model below is only a run-time choice or verification example:

- The scaffold is hewo's runtime definition under `src/hewo/runtime` (a downstream
  repository renames this path to `src/<agent_name>/runtime`).
- The backend is a mature CLI such as OpenCode, Codex, Claude Code, or pi.
- The provider/model is selected at runtime and is never baked into the
  scaffold. OpenCode accepts arbitrary provider IDs through `LLM_PROVIDER`,
  `<PROVIDER>_API_KEY`, and provider-specific base-URL variables.

The current real Docker smoke matrix is intentionally explicit: OpenCode with
the `openai/gpt-5.5` auth store, OpenCode with `opencode-go/gpt-5.6-luna`,
Codex with `gpt-5.5`, Claude Code through the authorized Apex-compatible
Anthropic endpoint with `sonnet`, and pi with the existing `openai-codex/gpt-5.5`
auth store all returned the exact `hi` response.
`opencode-go` exposes additional models (including GLM, Qwen, Kimi, Grok,
MiniMax, and DeepSeek variants); those are provider/model choices, not new
scaffolds. Direct DeepSeek-key testing is not part of the passing matrix.

For a short-lived read-only provider runtime bundle, create it and pass it to Docker:

```bash
bundle=$(mktemp -d)
./scripts/create-provider-bundle.sh openai gpt-5.6 OPENAI_API_KEY "$bundle"
./docker/run-hewo-e2e.sh --agent hewo --provider openai --model gpt-5.6 --bundle "$bundle" "完成这个任务"
rm -rf "$bundle"
```

The bundle is mode `0700`, its credential is mode `0600`, and Docker mounts it read-only at `/run/provider-bundle`. It contains only the selected provider metadata and one credential, never the host `HOME` or any CLI authentication database.

Use `--api-key-stdin` when the key should not appear in shell history, `--auth-file PATH` for one explicit read-only OpenCode auth store, or `--env-file PATH` for a provider-specific environment file. Run `./docker/run-hewo-e2e.sh --help` for all options.

Never commit provider keys. Credentials are injected at runtime through environment variables or Docker secrets. `docker/run-hewo-e2e.sh` automatically forwards provider variables already exported in the development shell and also loads `.env` when present; it does not copy OpenCode, Codex, or Claude Code credential files into the image.

## Layout

`src/hewo/runtime` is the hewo product Agent definition shipped to users. The
**development coding agent** that develops this template uses `AGENTS.md` and
`.agents/` for reusable development memory, knowledge, skills, and workflows;
it must not treat those resources as hewo behavior. `scripts`, `docker`, and
`benchmarks` are template infrastructure. `distribution` contains the public
installer and launcher.

The key feature is definition-first development: create or modify an Agent by editing its runtime identity, skills, memory policy, and OpenCode configuration rather than implementing another runtime. Use GitHub Issues for design decisions and acceptance evidence; do not add `docs/` or unit-test suites for Agent behavior.

## Provider contract

The image contains no credentials and does not bake in a provider. The E2E helper passes the selected provider, model, and provider key at runtime. It supports arbitrary provider names using `<PROVIDER>_API_KEY`, explicit key variables, env files, or one explicitly mounted auth store. The entrypoint fails closed when neither a provider key nor an explicit auth store is supplied. Docker uses `opencode-ai@latest` by design; every E2E report records the actual CLI version, provider, model, and Agent Definition revision.

Provider ownership is explicit: OpenCode owns OpenCode-compatible providers
such as `openai` and `opencode-go`; Codex owns its configured Codex profiles;
Claude Code owns the Apex Claude integration. `apex-claude` must not be
configured or tested through OpenCode. Explicit credential mounts are
backend-specific and the helper never copies a complete host home directory;
an explicitly supplied env file remains user-controlled and should contain
only the variables intended for that run.

## Create a new agent

```bash
cp -R src/hewo src/my-agent
./scripts/validate-definition.sh my-agent
```

`src/hewo`（Hello World）是本 template 中功能完整、刻意限定范围的参考产品
Agent，也是当前仓库实际开发的产品。使用它验证完整 runtime 路径；如果要创建
下游产品，才复制并改名为 `src/<agent_name>`：

```bash
./scripts/validate-definition.sh hewo
./docker/run-hewo-e2e.sh --agent hewo --provider openai --model gpt-5.5 "Say hello to Ada"
```

Replace `src/hewo` only when creating a separate downstream product Agent. In
this repository, keep hewo's product behavior under `src/hewo/`; keep the
**development coding agent** instructions in `AGENTS.md` and `.agents/`, and do
not put template workflow instructions inside `src/hewo/runtime`.

Use `scripts/build-release.sh hewo 0.1.0` to produce a bundle containing only runtime behavior. The release contains its own installer and launcher; a downloaded bootstrap installer can fetch that archive with `RELEASE_URL=... bash install.sh`, without a developer checkout. Record release and E2E evidence in the relevant GitHub issue and run `scripts/collect-trace.sh` before storing trajectory evidence.

This project follows a reuse-first development philosophy: an independent
developer should build Agent behavior with prompts, skills, memory, knowledge,
workflows, and tools, while delegating execution, model adapters, approvals,
and terminal UX to the established coding-agent CLIs. The template therefore
adds only the thin scaffold/launcher/provider wiring needed to compose those
systems; it does not reimplement a coding-agent runtime.

For a non-Docker release installation that should bundle all four backends,
set `AGENT_BACKENDS=opencode,pi,codex,claude` when running the installer. The
default release installation includes OpenCode and pi; set
`AGENT_BACKENDS=opencode` if you want to avoid downloading pi. Codex and Claude
Code can be added explicitly with `AGENT_BACKENDS=opencode,pi,codex,claude`.
The Docker image always includes all four. A release archive is
designed to be installed without cloning this repository: download its
installer and set `RELEASE_URL` to the matching archive URL. The repository
currently contains the release builder and installer, but does not yet publish
a GitHub Release/tag; do not present the example URL as a live download until a
version is actually published.

After a version is published, the no-clone installation flow is:

```bash
VERSION=0.1.0
INSTALLER_URL="https://raw.githubusercontent.com/a-green-hand-jack/coding-agent-template/v${VERSION}/distribution/install.sh"
RELEASE_URL="https://github.com/a-green-hand-jack/coding-agent-template/releases/download/v${VERSION}/hewo-${VERSION}.tar.gz"
curl --fail --silent --show-error --location "$INSTALLER_URL" -o /tmp/hewo-install.sh
RELEASE_URL="$RELEASE_URL" AGENT_NAME=hewo AGENT_BACKENDS=opencode,codex,claude,pi \
  bash /tmp/hewo-install.sh
rm -f /tmp/hewo-install.sh
export PATH="$HOME/.local/bin:$PATH"
hewo --version
```

`benchmarks/` contains a benchmark contract, the `hewo-infrastructure-smoke`
task, and a deterministic verifier. Run the complete smoke with:

```bash
OPENCODE_AUTH_FILE="$HOME/.local/share/opencode/auth.json" \
LLM_PROVIDER=openai LLM_MODEL=gpt-5.5 \
BENCHMARK_RUN_DIR=/tmp/hewo-evidence \
./scripts/run-benchmark.sh hewo
```

The benchmark writes only disposable workspace artifacts and a scrubbed
trajectory; never commit the evidence directory or raw provider output. For
full product-agent iteration, run the project-internal evaluation loop from
`.agents/workflows/agent-development.md`; long E2E or benchmark validation
should be submitted through the loop helper's registered background mode so it
can be queried and cleaned up without blocking the developer session.

## Development environments

The template supports both ecosystems. Python tooling is declared in `pyproject.toml` (with `requirements-dev.txt` for pip users); run `./scripts/setup-dev.sh` to create `.venv` and install development dependencies. TypeScript tooling is declared in `package.json` and `tsconfig.json`; use `npm ci` when a lockfile is present. These environments are for the **development coding agent** and validation scripts only. They are not copied into `src/hewo/runtime/` (or a downstream `src/<agent_name>/runtime/`) or shipped to end users.

The Dockerfile is multi-stage. Its builder may read the repository, but the final runtime image copies only the installed product runtime and launcher plus the OpenCode, Codex, Claude Code, and pi CLI packages. Template development resources, tests, benchmarks, `AGENTS.md`, and `.agents/` cannot be reached from the user container.

## Agent diagrams

Generated by the development-only `agent-evaluation-loop-design` skill. The
`.mmd` files are the single source of truth; the blocks below are generated and
are rewritten in place, so never hand-edit them.

Regenerate them with:

```bash
python3 .agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py \
  --agent hewo --repo-root . --output-dir . --readme README.md
python3 .agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py \
  --agent hewo --repo-root . --output-dir . --readme README.md --strict
```

The first diagram answers what the product Agent is; the second answers how it
is iterated, as a state machine with guards rather than a checklist. They
describe **this template's** `hewo`, whose evaluation contract is
`infrastructure-smoke-only` — so its honest state is
`SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`, not a demonstrated performance gain. A
downstream repository must write its own contract and regenerate its own
diagrams; these are not downstream product facts. GitHub renders the Mermaid
blocks; some other Markdown renderers will show them as code.

Source: [`agent-architecture.mmd`](agent-architecture.mmd)

<!-- BEGIN GENERATED: agent-architecture.mmd -->
```mermaid
%% GENERATED FILE - do not edit by hand.
%% Regenerate with the agent-evaluation-loop-design skill's generate-agent-diagrams.py.
%% Agent: hewo
%% Contract mode: infrastructure-smoke-only
%% Contract state: SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE
%% Product goal: Serve as a complete, intentionally scoped Hello World Agent that proves the installation, runtime-injection, skill-loading, workspace and artifact path work end to end.
%% Product input: A greeting request with a name, or an infrastructure smoke task naming a required artifact.
%% Product output: A short greeting including the supplied name, or the requested smoke artifact plus a verified hewo-tool --check result.
%% Functional checks: greeting-includes-supplied-name, smoke-artifact-written, tool-check-result-inspected
flowchart TB
  subgraph user["Human / User"]
    user_input["Input<br/>A greeting request with a name, or an infrastructure smoke task naming a required artifact."]
    user_output["Output<br/>A short greeting including the supplied name, or the requested smoke artifact plus a verified hewo-tool --che…"]
  end
  subgraph runtime["Product runtime: src/hewo/runtime"]
    rt_identity["identity.md<br/>product identity and instructions"]
    rt_memory_policy["memory-policy.md<br/>durable memory boundary"]
    subgraph grp_knowledge["knowledge"]
      kn_readme["README.md"]
    end
    subgraph grp_skills["skills"]
      sk_runtime_smoke["runtime-smoke"]
    end
    subgraph grp_workflows["workflows"]
      wf_greeting["greeting.md"]
      wf_infrastructure_smoke["infrastructure-smoke.md"]
    end
    subgraph grp_tools["tools (deterministic leaf adapters)"]
      tl_hewo_tool["hewo_tool.py"]
    end
  end
  subgraph execution["Execution layer (external — not product identity)"]
    ex_backend["coding-agent backend<br/>supplied at run time"]
    ex_provider["LLM provider<br/>credentials injected at run time"]
    ex_model["model<br/>selected at run time"]
  end
  subgraph evidence["Evidence outputs"]
    ev_artifact["required artifacts<br/>smoke artifact named by the task"]
    ev_trajectory["scrubbed trajectory<br/>no credentials, no raw sessions"]
    ev_verifier["verifier report<br/>functional pass or fail"]
  end
  subgraph development["Development-only (not product behavior)"]
    dv_contract["evaluation contract<br/>mode=infrastructure-smoke-only, scope=not applicable"]
    dv_validation["validate-agent-evaluation.py<br/>structure and determinism"]
    dv_benchmark["benchmark and comparator<br/>primary metric none declared (smoke-only contract)"]
    dv_loop["run-agent-loop.sh<br/>stage runner, not an auto-optimizer"]
  end
  user_input --> rt_identity
  rt_identity --> rt_memory_policy
  rt_identity --> ex_backend
  ex_backend --> ex_provider
  ex_provider --> ex_model
  ex_model --> user_output
  rt_identity --> ev_artifact
  ev_artifact --> ev_trajectory
  ev_artifact --> ev_verifier
  ev_verifier --> dv_benchmark
  dv_contract --> dv_validation
  dv_validation --> dv_benchmark
  dv_benchmark --> dv_loop
  rt_identity --> sk_runtime_smoke
  rt_identity --> wf_greeting
  rt_identity --> wf_infrastructure_smoke
  kn_readme --> rt_identity
  tl_hewo_tool --> ev_artifact
```
<!-- END GENERATED: agent-architecture.mmd -->

Source: [`agent-optimization-loop.mmd`](agent-optimization-loop.mmd)

<!-- BEGIN GENERATED: agent-optimization-loop.mmd -->
```mermaid
%% GENERATED FILE - do not edit by hand.
%% Regenerate with the agent-evaluation-loop-design skill's generate-agent-diagrams.py.
%% Agent: hewo
%% Contract state: SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE
stateDiagram-v2
  direction TB
  state "INTENT_DEFINED" as INTENT_DEFINED
  state "CONTRACT_DESIGNED" as CONTRACT_DESIGNED
  state "FUNCTIONAL_BASELINE_BUILT" as FUNCTIONAL_BASELINE_BUILT
  state "BASELINE_MEASURED" as BASELINE_MEASURED
  state "HYPOTHESIS_READY" as HYPOTHESIS_READY
  state "CANDIDATE_IMPLEMENTED" as CANDIDATE_IMPLEMENTED
  state "CANDIDATE_EVALUATING" as CANDIDATE_EVALUATING
  state "EVIDENCE_VALIDATED" as EVIDENCE_VALIDATED
  state "COMPARE_WITH_CURRENT_BEST" as COMPARE_WITH_CURRENT_BEST
  state "DESIGN_INCOMPLETE" as DESIGN_INCOMPLETE
  state "FUNCTIONAL_BASELINE_MISSING" as FUNCTIONAL_BASELINE_MISSING
  state "SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE" as SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE
  state "ENVIRONMENT_BLOCKED" as ENVIRONMENT_BLOCKED
  state "EVALUATION_BLOCKED" as EVALUATION_BLOCKED
  state "BASELINE_INVALIDATED" as BASELINE_INVALIDATED
  state "CANDIDATE_REJECTED" as CANDIDATE_REJECTED
  state "CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE" as CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE
  state "GENERALIZATION_REQUIRED" as GENERALIZATION_REQUIRED
  state "ACCEPTED_AS_CURRENT_BEST" as ACCEPTED_AS_CURRENT_BEST
  state "STOPPED" as STOPPED
  INTENT_DEFINED --> CONTRACT_DESIGNED : human intent recorded
  CONTRACT_DESIGNED --> FUNCTIONAL_BASELINE_BUILT : contract valid and performance mode
  CONTRACT_DESIGNED --> DESIGN_INCOMPLETE : contract missing or schema invalid
  CONTRACT_DESIGNED --> SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE : contract mode is infrastructure smoke only
  FUNCTIONAL_BASELINE_BUILT --> BASELINE_MEASURED : functional checks decide pass or fail stably
  FUNCTIONAL_BASELINE_BUILT --> FUNCTIONAL_BASELINE_MISSING : contract or verifier cannot decide yet
  BASELINE_MEASURED --> HYPOTHESIS_READY : current best measured and promoted
  HYPOTHESIS_READY --> CANDIDATE_IMPLEMENTED : one improvement hypothesis at a time
  CANDIDATE_IMPLEMENTED --> CANDIDATE_EVALUATING : approved runner under the fixed condition manifest
  CANDIDATE_EVALUATING --> EVIDENCE_VALIDATED : samples and evidence collected
  EVIDENCE_VALIDATED --> COMPARE_WITH_CURRENT_BEST : schema, hashes and provenance check out
  COMPARE_WITH_CURRENT_BEST --> BASELINE_INVALIDATED : condition manifests differ
  COMPARE_WITH_CURRENT_BEST --> ENVIRONMENT_BLOCKED : credential, provider or infrastructure failure
  COMPARE_WITH_CURRENT_BEST --> EVALUATION_BLOCKED : benchmark, verifier or evidence failure
  COMPARE_WITH_CURRENT_BEST --> DESIGN_INCOMPLETE : required design fields missing or invalid
  COMPARE_WITH_CURRENT_BEST --> FUNCTIONAL_BASELINE_MISSING : current best invalid or not promoted
  COMPARE_WITH_CURRENT_BEST --> CANDIDATE_REJECTED : functional failure, threshold not met or regression
  COMPARE_WITH_CURRENT_BEST --> CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE : fixed benchmark threshold met
  CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE --> ACCEPTED_AS_CURRENT_BEST : benchmark-local scope plus promotion gate
  CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE --> GENERALIZATION_REQUIRED : product-general claim requested
  ACCEPTED_AS_CURRENT_BEST --> HYPOTHESIS_READY : keep iterating
  ACCEPTED_AS_CURRENT_BEST --> STOPPED : stop condition reached
  CANDIDATE_REJECTED --> HYPOTHESIS_READY : new hypothesis or rollback to previous best
  ENVIRONMENT_BLOCKED --> CANDIDATE_EVALUATING : fix the environment and rerun the same candidate
  EVALUATION_BLOCKED --> CANDIDATE_EVALUATING : fix benchmark, verifier or evidence and rerun
  BASELINE_INVALIDATED --> BASELINE_MEASURED : re-measure current best under the new condition identity
  GENERALIZATION_REQUIRED --> HYPOTHESIS_READY : independent holdout and human review still pending
  state SELF_BOOTSTRAP_ADVANCED {
    SB_BASE_COMMITTED --> SB_DISTINCT_CLEAN_CANDIDATE : distinct clean descendant revision
    SB_DISTINCT_CLEAN_CANDIDATE --> SB_RUN_BASE_EVALUATOR : evaluator comes from the immutable base archive
    SB_RUN_BASE_EVALUATOR --> SB_CHECK_OBSERVABLE_DELTA : structure and determinism preserved
    SB_CHECK_OBSERVABLE_DELTA --> SB_HUMAN_REVIEW : pre-declared delta observed
    SB_CHECK_OBSERVABLE_DELTA --> SB_BLOCKED : evaluator, fixture or protected path changed
    SB_CHECK_OBSERVABLE_DELTA --> SB_REJECTED : invariant lost or no observable delta
  }
  note right of COMPARE_WITH_CURRENT_BEST
    subject.definition_revision differs between current best and candidate by design.
    That difference is the premise of the comparison, never a baseline invalidation.
    Only the canonical condition manifest defines comparability; a run-affecting input
    that cannot be recorded in the manifest blocks the comparison instead of passing.
  end note
  note right of CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE
    A benchmark-local acceptance recommendation only. The comparator never promotes
    and never writes the current best; ACCEPTED_AS_CURRENT_BEST needs a separate
    promotion gate binding the result hash, the manifest hash and a human decision.
  end note
  note right of GENERALIZATION_REQUIRED
    A product-general claim needs an independent holdout or canary that was frozen
    before candidate selection and never used for tuning, plus human domain review.
  end note
  note right of ENVIRONMENT_BLOCKED
    Environment and evaluation blocks update nothing. A provider or infrastructure
    failure is not a regression and not an improvement; fix that layer and rerun
    the same candidate.
  end note
  note right of BASELINE_INVALIDATED
    The evaluation conditions changed. Re-measure the current best under the new
    condition identity before comparing anything else.
  end note
  note right of STOPPED
    STOPPED needs a recorded reason: goal reached, N consecutive candidates without
    material improvement, budget or wall-clock exhausted, or a human stop.
  end note
  note right of SELF_BOOTSTRAP_ADVANCED
    Advanced path for optimizing the design skill itself. The self-bootstrap
    candidate runs against the fixed fixture and the base evaluator and cannot
    relax the evaluator, the fixtures or the expected results.
  end note
  note right of SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE
    A smoke or infrastructure pass is never performance evidence. A smoke-only
    contract can render these diagrams but can never accept an improvement.
  end note
  note right of CONTRACT_DESIGNED
    Current contract state for hewo: mode infrastructure-smoke-only gives SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE.
  end note
  [*] --> INTENT_DEFINED
  STOPPED --> [*]
```
<!-- END GENERATED: agent-optimization-loop.mmd -->
