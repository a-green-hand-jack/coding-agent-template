# Agent 开发者指南

> **Role of this document**
> - **Audience:** 准备环境、验证或发布 Agent 的 human developer。
> - **Authority:** informative；规则冲突以 `AGENTS.md` 和 gate scripts 为准。
> - **Tone:** 操作性，给出真实命令及失败条件。
> - **Language:** 中文，保留英文标识与命令。
> - **Contains:** 环境准备、Docker E2E、后台状态与日志、构建和发布。
> - **Excludes:** coding agent 初始化 prompt、内部审计和优化流程（见 [开发内部流程](.agents/knowledge/development-procedures.md)）；产品安装使用见 `USER.md`。

所有命令从仓库根目录执行。示例中的 `<provider>`、`<model>`、`<version>`、`<run_id>` 必须替换为实际值；不要直接复制尖括号占位符执行。

本仓库交付 **hewo**，产品定义在 `src/hewo/runtime/`；维护仓库的 coding agent 使用 `AGENTS.md` 和 `.agents/`，两者不是产品上下文。scaffold、pi backend、provider/model 保持独立；当前只支持 pi，没有第二 backend 或 fallback。

## 1. 准备开发环境

需要 Git、Bash、Python 3（含 venv）、Node/npm、uv、自己安装的 pi，以及可用的 Docker daemon。发布还需要已登录的 GitHub CLI (`gh`)。安装与依赖说明见 [USER.md](USER.md)。

```bash
./scripts/setup-dev.sh
```

脚本按 `VIRTUAL_ENV_PATH` → `VIRTUAL_ENV` → 仓库 `.venv` 选择环境，已有环境直接复用，否则创建；安装 Python 开发依赖和锁定的 npm 依赖，再安装当前 runtime package。运行前先确认已有兼容环境；需要指定时使用：

```bash
VIRTUAL_ENV_PATH=/path/to/existing/environment ./scripts/setup-dev.sh
```

默认安装到 `~/.local/lib/hewo/`；可用 `PREFIX` 改变安装前缀。脚本不执行产品请求，也不安装 pi、不配置 provider 或凭据。产品工具环境独立于开发 `.venv`。开发 coding agent 只通过下面的 Docker helper 测试产品，不在宿主机直接执行产品请求。

## 2. 真实 Docker E2E

先确认本机实际配置的 provider/model；`pi --list-models` 可做无密钥输出的枚举，不能代替真实请求。不要读取或打印 auth store、key 文件、`.env` 或 resolved configuration 来探测凭据。

```bash
./docker/run-hewo-e2e.sh --agent hewo \
  --provider <provider> --model <model> \
  --pi-auth-file "$HOME/.pi/agent/auth.json" "向 Ada 问好"
```

默认从当前工作树冻结快照并构建镜像，在容器安装产品包，使用与用户相同的 pi 原生资源加载方式执行请求。helper 将 provider/model 实际传给 pi，并记录不可变 image ID、安装模式与退出状态。

凭据来源只接受 `--pi-auth-file`、`--api-key-env`、`--api-key-stdin`、`--bundle`；不隐式读取 `.env`。OAuth auth store 和 bundle 只读挂载；显式 API key 在容器内传给 pi，不能写入镜像、Git 或 runtime。例如使用已经安全注入宿主机环境的变量：

```bash
./docker/run-hewo-e2e.sh --provider <provider> --model <model> \
  --api-key-env PROVIDER_API_KEY "向 Ada 问好"
./docker/run-hewo-e2e.sh --help
```

缺少 provider/model、凭据来源，或使用不支持的 backend/flag，会拒绝执行。`--allow-unauthenticated -- --version` 仅用于 infrastructure-only 检查，不是 Agent E2E。镜像构建成功、CLI 启动或退出 0 都不能替代检查真实回复和任务所要求的 artifacts。

完整 smoke 的执行及 artifact 验收见 [开发内部流程](.agents/knowledge/development-procedures.md#完整-infrastructure-smoke)。机器特定限制应查本机记录；例如 nested sandbox 失败不能通过默认关闭安全隔离掩盖。

## 3. 长任务：后台运行、状态与日志

需要完整验证流水线时可使用内部 runner 的后台接口；它不是另一套产品 CLI，也不是自动优化器。

```bash
./.agents/scripts/run-agent-loop.sh --background \
  --provider <provider> --model <model> \
  --pi-auth-file "$HOME/.pi/agent/auth.json" "<task>"
./.agents/scripts/run-agent-loop.sh --list-runs
./.agents/scripts/run-agent-loop.sh --run-status <run_id>
```

preflight 在前台完成，无效参数立即拒绝；提交成功后，每个阶段都读取该 run 的冻结快照，后续编辑不影响正在运行的验证。状态包含 `definition_revision`、`image`、`log`、summary 及 artifact 路径。用状态返回的 `log` 路径查看日志：

```bash
less /path/from/run-status/output.log
```

登记根目录默认是 `${XDG_STATE_HOME:-$HOME/.local/state}/agent-loop`，可由 `AGENT_LOOP_STATE_DIR` 覆盖；位于仓库之外。进程消失但无退出记录会标为 `abandoned`。在本机检查真实输出，不把 raw trajectory、provider output 或个人数据提交到公开仓库；分享前先 scrub。记录 backend/provider/model、credential-source flag、CLI version、runtime revision 和 artifact 路径，不记录凭据值。

消费结果后清理已结束的 run；`all` 不删除正在运行的任务：

```bash
./.agents/scripts/run-agent-loop.sh --clean-run <run_id>
./.agents/scripts/run-agent-loop.sh --clean-run all
./.agents/scripts/run-agent-loop.sh --gc --older-than 7
```

最后一条仅回收达到年龄阈值且没有登记 run 引用的内容寻址 `def-` 镜像。先保留仍需使用的证据，再清理。

## 4. 构建和验证 release

构建本地归档（不创建 tag，不发布）：

```bash
./scripts/build-release.sh hewo <version>
```

输出为 `release/hewo-<version>.tar.gz`，包含 runtime package、release metadata 和 installer，不包含开发指令、`.agents/` 或 development 目录。产品 npm 依赖需要 lockfile，安装时使用 `npm ci --ignore-scripts`；installer 不安装 pi。

从当前冻结源码生成归档、验证源码/归档/安装 parity 并执行真实请求：

```bash
./docker/run-hewo-e2e.sh --release \
  --provider <provider> --model <model> \
  --pi-auth-file "$HOME/.pi/agent/auth.json" "向 Ada 问好"
```

`--user-path` 是 `--release` 的别名。验证指定的已有归档：

```bash
./docker/run-hewo-e2e.sh --artifact release/hewo-<version>.tar.gz \
  --provider <provider> --model <model> \
  --pi-auth-file "$HOME/.pi/agent/auth.json" "向 Ada 问好"
```

已有归档不要求与当前源码一致。release 模式只能从归档安装，禁止用 `--image` / `--no-build` 绕过；独立评测与审计仍按 [开发内部流程](.agents/knowledge/development-procedures.md) 执行。

## 5. 发布

先完成对应版本的真实 provider-backed E2E 与适用审计，检查发布物无凭据、auth store、开发指令或个人数据。版本按最新 Git tag 和改动语义递增；每次被接受的产品行为改动应发布新版本，不能把机械发布当作行为验证。

```bash
git tag -l
./scripts/publish-release.sh hewo <version> --dry-run
./scripts/publish-release.sh hewo <version>
```

发布要求 tracked worktree 无未提交改动、tag 不存在、`gh` 可访问目标仓库。`--dry-run` 同样检查这些条件；真正执行会校验定义，以正确的 `RELEASE_URL` 构建归档，创建并推送 tag，再创建 GitHub release，上传 archive 和烘焙好的 `install.sh`。这是外部写操作，仅在明确决定发布时运行。

发布后用户无需 clone 仓库，也无需设置版本或 `RELEASE_URL`，可从 GitHub Releases 下载 installer 安装，再用 pi 显式加载 runtime package；完整命令见 [USER.md](USER.md)。

## 进一步阅读

- [README.md](README.md)：定位、目录布局与产品结构/优化状态图。
- [开发内部流程](.agents/knowledge/development-procedures.md)：初始化/实现 prompts、选择性复用、审计、内部 case 和图表维护。
- [AGENTS.md](AGENTS.md)：开发 coding agent 的强制规则。
