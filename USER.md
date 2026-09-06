# hewo 用户指南

`hewo` 是一个面向最终用户的 Agent CLI/TUI 入口。它把一个 Agent
scaffold 的行为定义交给成熟的 coding-agent backend 执行，再由 backend
连接具体的 LLM provider 和 model。

```text
Agent scaffold  ->  coding-agent backend  ->  LLM provider/model
hewo runtime        OpenCode/Codex/Claude    opencode-go/openai/...
```

用户通常只需要使用 `hewo`，不需要直接调用 OpenCode、Codex 或 Claude Code。

## 1. 安装

### 从源码安装

在 template 根目录执行：

```bash
AGENT_NAME=hewo \
PREFIX="$HOME/.local" \
AGENT_BACKENDS=opencode,codex,claude \
./distribution/install.sh
```

确保命令目录在 `PATH` 中：

```bash
export PATH="$HOME/.local/bin:$PATH"
hewo --version
hewo --help
```

`AGENT_BACKENDS` 可以只安装需要的 backend：

```bash
AGENT_BACKENDS=opencode ./distribution/install.sh
AGENT_BACKENDS=opencode,codex,claude ./distribution/install.sh
```

### 从 release 安装

release archive 自带 Agent definition、launcher 和 installer。下载其中的
`install.sh` 后执行：

```bash
RELEASE_URL="https://example.com/releases/hewo-0.1.0.tar.gz" \
AGENT_NAME=hewo \
AGENT_BACKENDS=opencode,codex,claude \
bash install.sh
```

只使用可信的 release URL，不要把 credentials 放入命令或归档。

### 使用 Docker

```bash
docker build --build-arg AGENT_NAME=hewo \
  -t hewo:dev -f docker/Dockerfile .

docker run --rm -it \
  --env-file .env \
  hewo:dev \
  "完成这个任务"
```

Docker 镜像内置 OpenCode、Codex 和 Claude Code。镜像不包含开发目录、
`AGENTS.md`、`.agents/` 或 provider credentials。

## 2. Agent scaffold、backend 和 LLM

这三层是独立的：

- **Agent scaffold**：一个 Agent 的 Identity、Knowledge、Skills、Memory
  policy 和 Workflows。
- **Backend**：执行 Agent 的成熟 coding-agent，例如 OpenCode、Codex、
  Claude Code。
- **Provider/model**：运行时选择的模型服务和模型名称。

当前一个安装好的命令对应一个 scaffold：`hewo` 对应 `hewo` scaffold。要
使用另一个 scaffold，安装时指定它的名称，之后使用对应命令：

```bash
AGENT_NAME=my-agent ./distribution/install.sh
my-agent "运行我的 Agent"
```

当前版本可以在运行时切换 backend 和 provider/model，但还不能用
`hewo --scaffold another-agent` 在多个 scaffold 之间切换。

## 3. 选择 backend

### OpenCode

```bash
hewo --backend opencode \
  --provider opencode-go \
  --model glm-5.3 \
  "分析这个项目"
```

OpenCode 使用 `[provider/]model` 命名空间；`--provider` 主要用于 OpenCode。

### Codex

```bash
hewo --backend codex \
  --model gpt-5.5 \
  "分析这个项目"
```

### Claude Code

```bash
hewo --backend claude \
  --model sonnet \
  "分析这个项目"
```

Claude Code 使用 `sonnet`、`opus` 等自己的 model alias。

## 4. 配置 provider 和 credentials

credentials 只在运行时提供，不要写入 Git、scaffold、Dockerfile 或镜像。

### OpenCode

```bash
export AGENT_BACKEND=opencode
export LLM_PROVIDER=opencode-go
export LLM_MODEL=glm-5.3
```

使用 API key 时，变量名是 `<PROVIDER>_API_KEY`。例如：

```bash
export OPENAI_API_KEY="..."
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-5.5
hewo "你好"
```

如果 OpenCode 已通过自己的标准 auth store 登录，运行 hewo 前设置：

```bash
export AGENT_AUTH_STORE=1
```

### Codex

```bash
export OPENAI_API_KEY="..."
export CODEX_MODEL=gpt-5.5
hewo --backend codex "你好"
```

也可以使用 Codex 的标准 `CODEX_HOME/auth.json`。使用外部 auth store 时，
设置 `CODEX_AUTH_STORE=1`。

### Claude Code

```bash
export ANTHROPIC_API_KEY="..."
export ANTHROPIC_BASE_URL="https://api.example.com"
hewo --backend claude --model sonnet "你好"
```

也可以使用 `ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_API_KEY_FILE` 或 Claude
credentials store。使用 credentials store 时，设置 `CLAUDE_AUTH_STORE=1`。

## 5. CLI 和 TUI

### CLI：一次性任务

带任务参数时，hewo 使用 backend 的非交互模式：

```bash
hewo "总结当前目录的代码"
hewo --backend codex "检查这个错误"
hewo --backend claude --model sonnet "设计一个修复方案"
```

### TUI：交互式工作

不带任务时，hewo 默认进入选定 backend 的交互界面：

```bash
hewo
hewo --backend codex
hewo --backend claude
```

也可以显式指定：

```bash
hewo --tui
hewo --backend opencode --tui
```

CLI 和 TUI 都使用同一个 scaffold runtime；变化的只是 backend 和
provider/model。

常用环境变量：

```text
AGENT_BACKEND   opencode、codex 或 claude
LLM_PROVIDER    OpenCode provider ID
LLM_MODEL       默认模型
LLM_VARIANT     OpenCode model variant
```

## 6. 安全边界和故障排查

- 不要提交 API key、auth store、session、`.env` 或个人数据。
- 不要把宿主机整个 `HOME` 目录挂入容器。
- Docker 场景只挂载明确指定的 credentials，并使用只读挂载。
- `--provider` 对 Codex/Claude Code 不起作用；它们使用自己的认证和模型命名空间。
- 缺少 provider key 或 auth store 时，hewo 会拒绝启动。
- `hewo --version` 和 `hewo --help` 可用于确认安装是否成功。

开发者验证 Agent 行为请参考 [DEV.md](DEV.md)；最终用户不需要运行开发仓库
中的 benchmark 或发布脚本。
