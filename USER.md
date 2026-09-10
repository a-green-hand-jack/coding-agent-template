# hewo 用户指南

HeWo 是 pi-native runtime package，不提供独立的 `hewo` CLI。用户安装并配置
pi，安装器只交付产品资源和独立工具环境；provider/model 始终由 pi 原生参数选择。

## 1. 准备依赖

需要 Node.js/npm（Node.js 22 或更新的兼容版本）、Python 3、uv、curl 和 tar。
先按各工具的官方说明安装，然后自行安装 pi：

```bash
npm install -g @earendil-works/pi-coding-agent
pi --version
uv --version
python3 --version
```

安装器不安装 pi，也不配置 provider、model 或 credentials。

## 2. 从 release 安装（无需 clone）

```bash
curl -fsSL https://github.com/a-green-hand-jack/coding-agent-template/releases/latest/download/install.sh | bash
```

固定版本时，将 `latest` 换成 `download/v<version>` 所对应的发布 URL。
可用版本以 GitHub Releases 为准。安装器下载与自身匹配的归档，再从归档安装。
默认产品目录是 `~/.local/lib/hewo/runtime-package/`，工具环境是
`~/.local/lib/hewo/environment/`。使用自定义 `PREFIX` 时，相应替换以下路径。

```bash
export PATH="$HOME/.local/lib/hewo/environment/bin:$PATH"
hewo-tool --check
```

工具检查应输出 `HEWO_TOOL_OK`。该 PATH 需要在每个运行产品的终端设置，或加入
自己的 shell 配置。工具环境独立于开发仓库，不使用开发 `.venv`。

源码用户可在仓库根目录运行同一安装器：

```bash
AGENT_NAME=hewo PREFIX="$HOME/.local" ./distribution/install.sh
```

## 3. 配置 pi 和选择模型

使用 pi 自己的登录流程（交互界面中的 `/login`）或 provider 官方环境变量。
用 `pi --list-models` 做不含秘密的可用性枚举；不要打印 auth store 或配置转储。
模型出现在列表中不等于已完成请求验证。不要在命令历史中输入 API key。

## 4. 运行：同一条 pi 原生命令

一次性 CLI 请求：

```bash
pi --no-session --no-context-files --no-extensions --no-skills \
  --no-prompt-templates --no-themes \
  -e "$HOME/.local/lib/hewo/runtime-package" \
  --provider <provider> --model <model> --print "向 Ada 问好"
```

TUI 使用完全相同的加载参数，去掉 `--print` 和任务参数：

```bash
pi --no-session --no-context-files --no-extensions --no-skills \
  --no-prompt-templates --no-themes \
  -e "$HOME/.local/lib/hewo/runtime-package" \
  --provider <provider> --model <model>
```

需要 JSON 时添加 pi 原生 `--mode json --print`；其他选项查看 `pi --help`。
这不是一套 HeWo 参数：不存在 `hewo --tui`、`--backend` 或自定义输出环境变量。
`--no-session` 不保存会话；所有 `--no-*` 关闭环境隐式发现，显式 `-e` 加载产品
package。pi 加载 package 声明的原生资源；runtime extension 从 manifest 消费
identity、memory policy、knowledge、workflows 和工具白名单。不要省略这些隔离参数。

多个产品使用不同安装路径，通过 `-e <installed-runtime-package>` 选择；不需要
新的产品命令或 scaffold registry。工具 PATH 也应切换到相应产品。

## 5. 边界和排查

- 凭据由 pi 解析；不在产品包、Git、镜像或 `.env` 示例中保存秘密。
- 缺少模型或授权时检查 `pi --list-models` 和 pi 的登录状态，不打印凭据。
- 找不到工具时先检查上述 PATH，再运行 `hewo-tool --check`。
- 默认天气查询使用离线 fixture；实时网络需要产品定义中的显式授权和主机白名单。
- 产品 extension 的失败应排查所安装 package 与 pi 版本，不退回已删除的产品包装命令。
- 容器场景只读挂载明确选定的凭据文件，不挂载整个宿主机 HOME。

开发 Docker 验证和发布流程见 [DEV.md](DEV.md)；用户不需要执行仓库审计或 benchmark。
