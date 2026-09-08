# hewo 用户指南

> **Role of this document**
> - **Audience:** an end user who installs and runs the product Agent's command.
> - **Authority:** informative. It describes what the installed product does; it imposes nothing on developers.
> - **Tone:** direct and task-oriented; no repository internals, no development vocabulary.
> - **Language:** Chinese, with English identifiers, paths and commands.
> - **Contains:** installation, the command surface, provider/model selection at run time, credential handling, and troubleshooting.
> - **Excludes:** how the Agent is developed or released (see `DEV.md`), development-agent rules (see `AGENTS.md`), and template internals (see `README.md`).

`hewo` 是一个面向最终用户的 Agent CLI/TUI 入口。它把一个 Agent
scaffold 的行为定义交给成熟的 coding-agent backend 执行，再由 backend
连接具体的 LLM provider 和 model。

```text
Agent scaffold  ->  coding-agent backend  ->  LLM provider/model
hewo runtime        pi                        user-selected provider/model
```

用户通常只需要使用 `hewo`，不需要直接调用 pi。三层保持独立：runtime 定义产品
行为，pi 提供执行循环、工具和会话，provider/model 在运行时选择。

## 1. 安装

### 方案 A：从已发布 release 安装（推荐，不需要 clone GitHub）

release archive 自带 hewo 的 runtime definition、launcher 和 installer。
用户只需要下载 release 中的 `install.sh`，再让它下载对应 archive；不需要
clone template 仓库。

已发布的版本在仓库的 GitHub Releases 页面列出；请以那里的最新版本为准，
不要假定下面示例中的版本号就是最新的。地址格式固定如下：

```bash
VERSION=0.1.0
INSTALLER_URL="https://raw.githubusercontent.com/a-green-hand-jack/coding-agent-template/v${VERSION}/distribution/install.sh"
RELEASE_URL="https://github.com/a-green-hand-jack/coding-agent-template/releases/download/v${VERSION}/hewo-${VERSION}.tar.gz"

curl --fail --silent --show-error --location "$INSTALLER_URL" -o /tmp/hewo-install.sh
RELEASE_URL="$RELEASE_URL" \
AGENT_NAME=hewo \
bash /tmp/hewo-install.sh
rm -f /tmp/hewo-install.sh
```

安装完成后：

```bash
export PATH="$HOME/.local/bin:$PATH"
hewo --version
hewo --help
```

安装器只会在本机没有 pi 时才安装它。已经装好 pi 的机器可以设置
`SKIP_RUNTIME_INSTALL=1` 跳过这一步。

不要把 API key、auth store 或 `.env` 放入命令、release archive 或 Git。

### 方案 B：从源码安装（仅适合开发者或未发布 release 时）

这个方案需要先取得 template 源码。在仓库根目录执行：

```bash
AGENT_NAME=hewo \
PREFIX="$HOME/.local" \
./distribution/install.sh
```

源码安装会在需要时安装 pi，并把 hewo 的工具安装到独立的
`~/.local/lib/hewo/environment/`，不会使用开发仓库的 `.venv`。如果 runtime
声明了 npm 依赖，安装器要求同时提供 lockfile，并以 `npm ci --ignore-scripts`
冻结安装；没有 lockfile 会直接拒绝，而不是在安装时解析版本。

### 使用 Docker

```bash
docker build --build-arg AGENT_NAME=hewo \
  -t hewo:dev -f docker/Dockerfile .

docker run --rm -it \
  --env-file .env \
  hewo:dev \
  "完成这个任务"
```

Docker 镜像只内置 pi。镜像不包含开发目录、`AGENTS.md`、`.agents/`、
评估契约或 provider credentials。

## 2. Agent scaffold、backend 和 LLM

这三层是独立的。provider、model 和 credentials 始终由用户或平台在运行时提供。
HeWo 是一个功能完整、刻意限定范围的 Hello World Agent，不是通过故意裁剪形成的
不完整版本：

- **Agent scaffold**：一个 Agent 的 Identity、Knowledge、Skills、Prompt
  templates、Memory policy、Workflows、Theme 和 Extension，全部由 runtime 的
  `package.json` 清单声明。
- **Backend**：执行这些资源的成熟 coding-agent。本产品只支持 pi。
- **Provider/model**：运行时选择的模型服务和模型名称。

当前一个安装好的命令对应一个 scaffold：`hewo` 对应 `hewo` scaffold。要
使用另一个 scaffold，安装时指定它的名称，之后使用对应命令：

```bash
AGENT_NAME=my-agent ./distribution/install.sh
my-agent "运行我的 Agent"
```

本产品只支持 pi，backend 不可切换；provider/model 在运行时选择。当前也还不能用
`hewo --scaffold another-agent` 在多个 scaffold 之间切换：一次只安装一个 scaffold。

## 3. Backend：只有 pi

hewo 只在 **pi** 上运行。没有第二个 backend，也没有回退：请求其他 backend 会
直接报错，而不是悄悄换一个默认值。

```bash
hewo --provider openai --model gpt-5.5 "你好"
```

`--backend` 只接受 `pi`（以及别名 `pi-coding-agent`）。

hewo 的运行时资源不是被拼成一段提示词，而是交给 pi 自己的加载器：skills 通过
`--skill`、slash 命令模板通过 `--prompt-template`、主题通过 `--theme`、
TypeScript extension 通过 `--extension`、工具白名单通过 `--tools`。只有
identity、memory policy、knowledge 和 workflow 使用 `--append-system-prompt`
注入，因为 pi 没有对应的原生资源类型；它们按文件逐段注入并带来源标注。

启动时 hewo 会关闭隐式发现：`--no-context-files` 让 pi 不会把任何
`AGENTS.md` 读进产品 agent，`--no-skills` 与 `--no-extensions` 阻止环境里的
全局/项目资源被混入（显式的 `--skill`、`--extension` 仍然生效），
`--no-approve` 阻止隐式信任项目本地文件。

默认拒绝：出站网络和额外能力都是关闭的。天气能力默认使用不联网的确定性
fixture provider；实时查询需要显式开启、指定允许的主机并设置超时，任何失败都
会退回 fixture 结果并明确标注，而不是让任务失败。

## 4. 配置 provider 和 credentials

provider、model 和凭据都在运行时提供，永远不属于 Agent 定义。

```bash
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-5.5
export OPENAI_API_KEY="..."
hewo "你好"
```

如果 pi 已经通过自己的 auth store 登录，运行 hewo 前设置：

```bash
export PI_AUTH_STORE=1
```

pi 解析凭据的顺序是：`--api-key`、其 `auth.json`、环境变量、`models.json` 中
的自定义 provider key。`pi --list-models` 会按已有凭据过滤，因此它是可用性探
针，而不是完整目录。

凭据永远不会写进镜像、Git 或 Agent 定义。缺少凭据时 hewo 会直接失败，而不是
静默降级。

## 5. CLI 和 TUI

### CLI：一次性任务

带任务参数时，hewo 以 pi 的非交互模式运行（`--print --no-session`），不保存
会话：

```bash
hewo "总结当前目录的代码"
hewo --provider openai --model gpt-5.5 "检查这个错误"
hewo /hewo-report            # slash 命令来自 runtime 的 prompt template
```

需要机器可读输出时：

```bash
AGENT_OUTPUT_FORMAT=json hewo "总结当前目录的代码"
```

`AGENT_OUTPUT_FORMAT` 只接受 `text`、`json`、`rpc`，对应 pi 的 `--mode`。

### TUI：交互式工作

不带任务时，hewo 进入 pi 的交互界面：

```bash
hewo
hewo --tui
```

### 工具白名单

hewo 的工具白名单来自 runtime 的 `package.json`，同时覆盖 pi 的内建工具和本
runtime extension 提供的工具。临时收紧：

```bash
hewo --tools read "只读地看一下这个仓库"
```

## 6. 安全边界和故障排查

- 不要提交 API key、auth store、session、`.env` 或个人数据。
- 不要把宿主机整个 `HOME` 目录挂入容器。
- Docker 场景只挂载明确指定的 credentials，并使用只读挂载。
- `--provider` 是必填的：hewo 不假设 pi 自己的默认 provider。
- 默认拒绝出站网络和额外能力；放宽需要显式设置 `HEWO_NETWORK` 和
  `HEWO_CAPABILITIES`，这是产品决策而不是便利开关。
- 子 agent 以独立进程运行，使用 `--no-session` 和最小只读工具白名单，
  不继承父级权限或会话，并受墙钟超时、并发上限、重试上限和输出截断约束。
- 缺少 provider key 或 auth store 时，hewo 会拒绝启动。
- `hewo --version` 和 `hewo --help` 可用于确认安装是否成功。

开发者验证 Agent 行为请参考 [DEV.md](DEV.md)；最终用户不需要运行开发仓库
中的 benchmark 或发布脚本。
