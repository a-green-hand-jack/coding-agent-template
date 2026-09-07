# Agent 开发者指南

本文面向维护 template、创建下游 Agent scaffold 和记录验证证据的开发者。
最终用户应阅读 [USER.md](USER.md)。

## 开发 Skill 入口

使用本 template 创建 Agent、同步 template 更新，或把现有 Agent 仓库迁移
到本结构时，开发 coding agent 应首先加载：

```text
.agents/skills/template-agent-development/SKILL.md
```

它会按当前任务渐进式加载一个 sub-skill：新建 Agent、同步 template，或迁移
现有仓库。修改 `src/<agent>/` 或准备 release 时，再使用
`.agents/skills/agent-definition-validation/SKILL.md` 完成当前验证流程。

每次发布 template 前，还必须加载
`.agents/skills/template-release-readiness/SKILL.md`。它审核整个 template
是否仍适合下游 Agent dev repo、登记表是否完整、template-specific 内容是否
可能泄露，以及 release/product 边界是否安全。

同步或创建下游仓库前，必须先阅读登记表
`.agents/template-content-registry.json`。它是 template 专属内容、可选择
同步的实现、以及 memory/knowledge/workflows 中性占位符的唯一清单；同步
细节见 `template-agent-development/references/sync-template.md`。不要复制
`.agents/` 整目录。

登记表覆盖整个仓库，而不只是 `.agents/`。新增或同步 template 内容后，先
确认所有 Git 跟踪文件都已经被登记：

```bash
python3 scripts/check-template-registry.py
```

这个检查会在新增文件没有归类时失败，避免下游无意间继承未审查的内容。

## 给下游 coding agent 的初始化 Prompt

把下面这段完整复制给负责建立下游 Agent dev repo 的 coding agent，只需要
替换尖括号中的变量：

```text
你正在维护下游 coding-agent 开发仓库。请以
https://github.com/a-green-hand-jack/coding-agent-template.git 为 template
上游，建立一个可长期维护的 Agent dev repo。

变量：
- Agent 名称：<agent_name>
- 目标 backend：<opencode|codex|claude，可多选>
- 目标 provider/model：<provider/model，按 backend 分别填写>

请按以下顺序执行：
1. 阅读 template 的 AGENTS.md、DEV.md、
   .agents/skills/template-agent-development/SKILL.md，以及
   .agents/template-content-registry.json；先运行
   `python3 scripts/check-template-registry.py`。
2. 使用 registry 和 sync-template sub-skill 做选择性同步。不要复制 template
   仓库或 `.agents/` 整目录，不要复制任何 template 的 AGENTS.md、Issue/HeWo
   历史、benchmark/release 证据、registry 文件或 provider 凭据。
3. 在 `src/<agent_name>/` 建立新的 runtime scaffold：可以从 `src/hewo/`
   复制排除 AGENTS.md 的可执行文件作为参考，但必须替换 Agent identity、
   skills、knowledge、workflows、tools 和 backend/provider 默认值。
4. 建立下游自己的 `.agents/knowledge/`、`.agents/memory/`、
   `.agents/workflows/`，只复制 template 的中性 PLACEHOLDER.md 作为起点，
   然后写入下游专属内容；为下游目录重新编写 scoped AGENTS.md。
5. 只按需选择性安装并适配 template 的开发 skill；所有 scaffold、backend、
   LLM provider/model 保持独立，不重复实现已有 coding-agent CLI 的执行循环、
   model client、审批或 tool loop。
6. 根据下游 Agent 的 backend/provider 组合更新 Docker、distribution、scripts、
   package 配置和文档；不要把 template 的 HeWo 命令、仓库名、发布 URL 或
   验收证据原样带入下游。
7. 运行 `./scripts/validate-definition.sh <agent_name>`、
   `python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py
   --agent <agent_name> --strict` 和
   `python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py --agent <agent_name>`。
8. 对每个承诺支持的 backend/provider 运行真实的 provider-backed Docker E2E；
   凭据只能运行时注入，不能写入 Git。最后检查 release payload 不包含
   AGENTS.md、`.agents/`、development 目录、auth store 或 credentials。

请先检查当前仓库是否有未提交改动并保留它们。完成后报告：选择了哪些
registry 条目、哪些内容被明确排除、Agent/backend/provider 组合、验证命令及
真实 Docker 响应证据；遇到需要产品决策的冲突时停下来说明，不要静默缩小范围。
```

## 给非 Agent 项目的基础设施复用 Prompt

有些项目并不发布一个 Agent，但仍然希望复用本 template 的 Docker、隔离工具
环境、backend CLI 安装方式，以及开发 coding agent 的经验。把下面这段复制给
负责初始化该项目的 coding agent；这不是 Agent scaffold 创建流程：

```text
你正在维护一个不发布 coding Agent 的项目。请把
https://github.com/a-green-hand-jack/coding-agent-template.git 当作基础设施和
开发流程参考，初始化当前项目，但不要把它伪装成 Agent dev repo。

项目目的：<project_purpose>
需要复用的能力：<docker|isolated-uv-tools|backend-clis|development-skills>

请按以下顺序执行：
1. 阅读 template 的 AGENTS.md、DEV.md、
   .agents/skills/template-agent-development/SKILL.md、
   .agents/skills/agent-infrastructure-health/SKILL.md，以及
   .agents/template-content-registry.json。先在 template checkout 中运行
   `python3 scripts/check-template-registry.py`，理解每个候选文件的类别。
2. 选择性复用 registry 中标为 `selective` 的 Docker、distribution、scripts、
   package/tool 配置和开发 skill；逐项记录选择理由。不要复制 template 仓库、
   `.agents/`、`src/hewo/`、任何 AGENTS.md、HeWo/Issue 历史、benchmark/release
   证据、registry 文件或 provider 凭据。
3. 为当前项目重新编写根 AGENTS.md，并建立自己的 `.agents/knowledge/`、
   `.agents/memory/`、`.agents/workflows/` 和 scoped AGENTS.md。可以把中性
   PLACEHOLDER.md 作为目录起点，但必须替换成项目专属内容。
4. 不要创建 `src/<agent_name>/agent.yaml`、Agent runtime identity、
   `runtime/opencode.json` 或 Agent 产品 release，除非项目需求后来明确改变。
   不要运行或声称通过只适用于 Agent scaffold 的 definition validation 或
   provider-backed Agent E2E；为当前项目定义自己的 smoke/acceptance contract。
5. 如果复用 Docker/backend CLI/uv 工具环境，删除 HeWo 默认值和 Agent 专属
   launcher 假设，明确哪些 CLI 只是开发工具、哪些是项目运行时依赖。工具环境
   必须独立、最小、无凭据；凭据只能在运行时注入。
6. 遵守 reuse-first：不要重新实现已有 coding-agent CLI 的 model client、
   session/approval loop 或 tool loop。只增加当前项目确实需要的薄适配层，并在
   项目 issue 中记录 backend 能力缺口。
7. 运行适配后的 shell/Python/config 检查、Docker smoke 和工具环境检查；如果
   使用了 agent-infrastructure-health skill，先改写其中的 Agent 名称、必需
   二进制和验收命令。最后检查镜像、发布物和 Git 中没有 AGENTS.md、`.agents/`
   开发历史、auth store、API keys 或个人数据。

请先检查当前项目未提交改动并保留它们。完成后报告：选择了哪些 registry 条目、
哪些 Agent-specific 内容被排除、复用了哪些基础设施、当前项目自己的验证契约，
以及仍需人工决定的 backend/provider 或安全边界问题；不要把项目强行改造成
coding Agent。
```

在较大改动、template 同步或 release 前，先运行一致性审计：

```bash
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py \
  --agent <agent_name> --strict
```

它会自动扫描 memory、skills、tools、runtime、文档和 release payload；模型
仍需对 WARN 和语义矛盾进行人工判断，不能把静态审计当成真实模型行为证据。

在开始 Agent 编排前，或修改 installer、launcher、Docker、backend、tool
environment 后，运行基础设施健康检查：

```bash
python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py \
  --agent <agent_name>
```

它会从当前 worktree 构建并检查 clean image；若只想复用已经由同一 worktree
构建的镜像，可使用 `--skip-build --image <agent_name>:infra`。通过后仍需用
实际 provider credentials 运行真实 Docker E2E，才能声称 Agent 行为验证完成。

不要把 template 的 `.agents/` 整目录复制到下游项目。Issue #1/HeWo 的历史
证据、template release 工作流和 benchmark 记录只属于本仓库；下游项目应建立
自己的 development memory、knowledge、workflow 和验收证据，只按需保留已经
审查过的通用 skill。

## 1. 设计原则：reuse-first

开发 Agent 的主要工作是设计和组合：

- prompt 和 Identity
- skills
- memory policy
- knowledge
- workflows
- tools

OpenCode、Codex、Claude Code 等成熟 coding-agent 负责执行循环、模型适配、
工具调用、审批和终端交互。本仓库只实现必要的 scaffold、runtime context
注入、backend 选择和 provider wiring，不重复实现 coding-agent runtime。

三层必须保持独立：

```text
Agent scaffold  ->  coding-agent backend  ->  LLM provider/model
```

在增加 CLI、model client、session manager 或 tool loop 之前，先确认目标
backend 没有提供该能力，并在 issue 中记录具体理由。优先扩展 runtime 定义
或薄 backend adapter，而不是创建平行 runtime。

`AGENTS.md` 面向开发 coding agent；`USER.md` 面向产品用户；runtime 目录
中的文件才是产品 Agent 的行为定义。`AGENTS.md` 不得进入 release 或 Docker
产品载荷。

## 2. Scaffold 合约

一个可安装 Agent 的最小结构是：

```text
src/<agent_name>/
├── AGENTS.md                 # 仅开发代理使用，不发布
├── agent.yaml
└── runtime/
    ├── identity.md
    ├── memory-policy.md
    ├── opencode.json
    ├── knowledge/
    ├── skills/
    ├── workflows/
    └── tools/                  # 可选，独立 uv tool project
```

`distribution/launcher` 会把 `identity.md` 以及 runtime 下的 knowledge、
skills、workflows 注入 OpenCode、Codex 或 Claude Code。若存在
`runtime/tools/pyproject.toml`，安装器会用 uv 创建独立的
`<prefix>/lib/<agent>/environment/` 并安装其中的 tools；launcher 会把该
环境的 `bin/` 放进 backend 的 PATH。每个 scaffold 都应
保留 `opencode.json`，即使某次运行选择的是 Codex 或 Claude Code。

不要在 `src/<agent_name>/runtime/` 中放置：

- API keys、auth stores、tokens 或 `.env`
- 原始 provider session
- 个人数据
- 开发代理的 `AGENTS.md` 内容
- 与具体 benchmark 绑定的行为 hack

创建下游 Agent：

```bash
mkdir -p src/my-agent
tar -C src/hewo --exclude=AGENTS.md -cf - . | tar -C src/my-agent -xf -
./scripts/validate-definition.sh my-agent
```

安装时由 `AGENT_NAME=my-agent` 选择该 scaffold；产品命令通常也叫
`my-agent`。当前 launcher 不提供运行时 `--scaffold` registry。

## 3. Backend 和 provider 组合

### Backend

当前 Docker image 安装：

```text
OpenCode       opencode-ai
Codex          @openai/codex
Claude Code    @anthropic-ai/claude-code
```

产品命令通过 `--backend` 或 `AGENT_BACKEND` 选择 backend：

```bash
hewo --backend opencode ...
hewo --backend codex ...
hewo --backend claude ...
```

`--provider` 只改变 OpenCode provider；Codex 和 Claude Code 保持各自的
认证、模型命名空间和 CLI 约定。

### Provider/model

scaffold 不应写死 provider。OpenCode provider/model 在运行时传入：

```bash
LLM_PROVIDER=opencode-go LLM_MODEL=glm-5.3 \
  ./docker/run-hewo-e2e.sh --agent hewo \
  --auth-file "$HOME/.local/share/opencode/auth.json" \
  "Reply with exactly: hi"
```

API key 环境变量按 provider ID 转换为 `<PROVIDER>_API_KEY`；Docker helper
只转发当前 backend 需要的 provider 环境变量，并拒绝不匹配的 credentials
参数。

工具项目应保持最小、无凭据、可重复。例如 hewo 的
`runtime/tools/pyproject.toml` 只安装 `hewo-tool`，用于验证 Agent 是否真的
能调用自己的产品环境；不要让它依赖 template 根目录的开发 `.venv`。

非 Docker release 可通过 `AGENT_BACKENDS=opencode,codex,claude` 选择要安装
的 CLI；Docker image 固定包含三个 backend。

## 4. 构建、安装和发布

### 源码安装检查

```bash
AGENT_NAME=hewo AGENT_BACKENDS=opencode,codex,claude \
  PREFIX=/tmp/hewo-install \
  ./distribution/install.sh
```

开发构建会排除 `AGENTS.md`、node_modules、package metadata 和 credentials；
若 scaffold 声明 tools，构建阶段会用 uv 生成其独立环境。

### Docker 构建

```bash
docker build --build-arg AGENT_NAME=hewo \
  -t hewo:e2e -f docker/Dockerfile .
```

Docker 使用 Node 22，并安装当前三个 CLI。验证版本时绕过产品 entrypoint：

```bash
docker run --rm --entrypoint /bin/bash hewo:e2e -lc \
  'opencode --version; codex --version; claude --version'
```

### Release

```bash
AGENT_BACKENDS=opencode,codex,claude \
  ./scripts/build-release.sh hewo 0.1.0
```

检查 release payload 不含 `AGENTS.md`、auth store、package metadata 或开发
目录。发布归档只包含 runtime definition、launcher 和 installer。当前仓库
提供构建和安装逻辑，但尚未自动发布 GitHub Release/tag；用户文档不得把
占位 URL 写成可直接下载的地址。发布后，用户可以只下载 release installer，
通过 `RELEASE_URL` 获取 archive，不需要 clone template。

## 5. 真实 Docker E2E 验证

镜像成功构建或 CLI 成功启动不等于 Agent E2E 通过。必须注入实际 provider
runtime，并观察容器中的真实模型响应。

### 最小请求

```bash
./docker/run-hewo-e2e.sh \
  --agent hewo \
  --backend opencode \
  --auth-file "$HOME/.local/share/opencode/auth.json" \
  --provider opencode-go \
  --model glm-5.3 \
  "Reply with exactly: hi"
```

Codex 和 Claude 使用各自的 `--codex-auth-file`、
`--claude-credentials-file` 或 `--claude-api-key-file`。credentials 只读
挂载，不能复制进镜像。

### 完整 infrastructure smoke

```bash
AGENT_BACKEND=opencode \
LLM_PROVIDER=opencode-go \
LLM_MODEL=glm-5.3 \
OPENCODE_AUTH_FILE="$HOME/.local/share/opencode/auth.json" \
ENV_FILE=/dev/null \
BENCHMARK_RUN_DIR=/tmp/hewo-evidence \
./scripts/run-benchmark.sh hewo
```

成功的 verifier 必须确认 Agent 在独立 workspace 中：

1. 加载 `runtime-smoke` skill；
2. 读取 knowledge 和 workflow；
3. 写入 `artifacts/hewo-smoke.md`；
4. 重新读取 artifact；
5. 验证 `Product runtime`、`Workspace access`、`Skill loaded`；
6. 验证 `HEWO_KNOWLEDGE_OK`、`HEWO_TOOL_OK` 和 `HEWO_WORKFLOW_OK`。

trajectory 和 benchmark 输出只能放在 disposable 目录，提交前必须 scrub，
不能包含 raw provider output 或 secrets。

### 当前 provider/model 验证矩阵

已通过真实 Docker 请求并返回精确 `hi`：

- `openai/gpt-5.5`（OpenCode）
- `opencode-go/gpt-5.6-luna`
- `opencode-go/glm-5.3`
- `opencode-go/qwen3.7-plus`
- `opencode-go/kimi-k2.7-code`
- `opencode-go/grok-4.6`
- Codex `gpt-5.5`
- Claude Code `sonnet`（通过授权的 Apex-compatible Anthropic endpoint）

`opencode-go` 还提供其他模型，但不能因为模型出现在列表中就声称测试
通过。每个下游 Agent 应记录实际使用的 provider、model、CLI version、
runtime revision 和 artifact 路径。

当前 Ubuntu 宿主机上，Codex 的完整工具任务可能受到 nested bubblewrap
user namespace 限制；简单请求通过不代表该宿主机的工具 sandbox 一定可用。
不要用默认关闭安全隔离的方式掩盖这个限制。

## 6. 验证清单

提交前至少运行：

```bash
./scripts/validate-definition.sh hewo
bash -n distribution/launcher distribution/install.sh \
  docker/run-hewo-e2e.sh scripts/build-release.sh scripts/run-benchmark.sh
git diff --check
```

变更 backend、Docker 或 release 时，还应：

1. 构建 Docker image；
2. 检查三个 CLI 版本；
3. 运行真实 provider-backed 最小 E2E；
4. 运行至少一个完整 infrastructure smoke；
5. 扫描镜像和 release payload 中的开发指令与 credentials；
6. 检查 CI 的 definition 和 image checks。

如果 runtime 声明了 tools，还应检查：

```bash
docker run --rm --entrypoint bash hewo:e2e -c \
  'command -v hewo-tool && hewo-tool --check'
```

输出必须包含 `HEWO_TOOL_OK`。完整 smoke 还必须证明 Agent 是通过 skill
调用该命令并把结果写入 artifact，而不是开发代理预先生成 artifact。

不要为 Agent 行为重新创建单元测试套件；使用真实 Docker E2E 和 GitHub
issue 证据。

## 7. 下游 Agent 文档样板

下游 Agent 应复制 [USER.md](USER.md) 作为用户文档，并在其中替换：

```text
Agent name: <agent_name>
Scaffold path: src/<agent_name>/runtime/
Default backend: opencode
Supported backends: opencode, codex, claude
Validated provider/models: <实际 E2E 结果>
CLI command: <agent_name>
```

同时保留本文的三层边界、reuse-first 原则、凭据安全规则和真实 Docker E2E
要求。只替换自己的 scaffold、默认模型和实际验证证据，不复制新的 runtime
实现。
