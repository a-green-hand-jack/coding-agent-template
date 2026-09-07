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

`hewo` can use the same product command with four interchangeable coding-agent
backends. OpenCode is the default; Codex, Claude Code, and pi are installed in the
Docker image and selected with `--backend` (or `AGENT_BACKEND`). Each backend
keeps its own model namespace and credential boundary:

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
independent layers:

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

`src/hewo`（Hello World）是本 template 的最小产品 agent 示例，也是当前仓库实际
开发的产品。使用它验证完整 OpenCode 路径；如果要创建下游产品，才复制并改名为
`src/<agent_name>`：

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
