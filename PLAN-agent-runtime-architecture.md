# Agent Runtime 架构与高层优先开发规范

## 1. 标题与状态

- Plan id：`agent-runtime-architecture`
- Review state：**In review — panel round 1 complete; revision pending panel round 2**
- 建议强度：**L4**（agent-proposed；涉及 runtime 架构、pi backend 适配、发布边界、开发治理与多文件改动）
- 当前对齐状态：第一轮、第二轮 panel findings 已吸收；等待用户重新确认修改后的 plan digest；尚未执行实现。
- 说明：本计划不修改现有未跟踪的 `PLAN-agent-visualization-self-bootstrap.md`。

## 2. 动机

开发 coding agent 在实现产品 agent 时，容易把产品需求直接降解为一个或多个
Python/ shell 脚本。脚本可以是叶子级适配器，但通常不能表达身份、知识、能力
边界、交互协议、编排、状态、权限与生命周期等高层产品语义。结果是产品 runtime
被错误地设计成“脚本集合”，而不是由成熟 backend 执行的、可组合的 Agent runtime。

本计划的目标是建立一个明确的 runtime 架构和开发决策顺序：

1. 先设计产品语义和组件关系，再决定是否需要可执行代码；
2. 优先使用 Pi 的 resource/extension/session 能力和已有 backend 能力；
3. 只有在现有声明式资源或 backend 能力不足时，才增加薄的 TypeScript extension
   或叶子工具；
4. 脚本不得承担产品级 agent loop、session manager、model client、审批循环或
   workflow 编排，除非有明确的 backend 能力缺口记录；
5. 将 Pi 作为唯一 backend，让 runtime 中的高层组件真正通过 Pi 原生机制加载，而
   不是全部被扁平拼接成一段 `--append-system-prompt` 文本。

## 3. 已验证的当前状态

证据来自当前仓库与本机安装的 pi `0.85.1`；本轮使用本机 CLI `pi --help`、随包
`docs/*.md` 和 `examples/extensions/`，未读取凭据，也未执行 provider 请求。

- `AGENTS.md:8-9,51-69` 已规定产品行为位于 `src/hewo/runtime/`，并要求
  reuse-first；但没有定义“何时使用 identity/skill/tool/extension/workflow”等
  组件，也没有禁止脚本承担高层职责的可执行决策规则。
- `DEV.md:273-296` 只把设计原则列为 prompt、skills、memory、knowledge、workflows、
  tools，尚未覆盖 commands/prompt templates、hooks/events、sub-agents、session/state、
  provider adapter、UI、package/manifest 等 Pi runtime 组件。
- 当前 runtime 只有 `identity.md`、`memory-policy.md`、`opencode.json`、knowledge、
  skills、workflows 和可选 `tools/`；`src/hewo/agent.yaml:1-5` 只记录目录位置。
- `src/hewo/runtime/opencode.json:3-16` 是 OpenCode 配置，声明 skills 与 instructions，
  但没有 Pi extension、prompt template、Pi package 或生命周期 hook 的 manifest。
- `distribution/launcher:146-149,209-220` 对所有 runtime Markdown 做扁平
  `runtime_context` 拼接；pi 分支只传 `--append-system-prompt`，没有按 runtime
  组件传递 `--skill`、`--prompt-template`、`--extension` 或显式工具集。
- `distribution/install.sh:63-90` 将产品 runtime 复制到 definition，并排除
  `package.json`/`package-lock.json`；若引入 Pi package/extension 依赖，当前发布路径
  不能直接承载其 manifest 与 Node runtime 依赖。
- 本机 Pi 文档明确说明：Pi 是可扩展 harness；原生提供 skills、prompt templates、
  extensions、themes、packages、sessions、RPC/SDK、provider 注册和 tools；而
  sub-agents、plan mode、MCP、permission popups、built-in todos 不是核心内建能力，
  应通过 extension/package/外部工具组合。
- `docs/extensions.md` 说明 `registerTool`、`registerCommand`、`pi.on(...)` 生命周期
  事件、`resources_discover`、`before_agent_start`、`tool_call` 拦截、session state、
  `pi.events`、`registerProvider` 和动态工具；并提供 `examples/extensions/subagent/`
  与 `plan-mode/` 作为可选实现，而非内建 runtime。
- `docs/skills.md`、`docs/prompt-templates.md`、`docs/packages.md`、`docs/sdk.md`、
  `docs/rpc.md` 共同表明：高层 runtime 可由声明式资源 + TypeScript extension +
  SDK/RPC host 组成，不需要先写 Python 脚本。
- 当前 `src/hewo/runtime/tools/hewo_tool.py` 是一个合理的确定性叶子工具，但它不应
  被当作产品 runtime 的通用实现模式。

## 4. 已定决策与拒绝的替代方案

### 4.1 用户已确认的方向

- **`user-confirmed`：** 产品 agent 应被视为更高层的系统，而不是脚本集合。
- **`user-confirmed`：** 脚本不是绝对禁止；但许多产品需求不能由脚本满足，必须
  先考虑其他 runtime 组件。
- **`user-confirmed`：** 使用 pi 作为 backend 的价值在于灵活性，应围绕 runtime
  组件设计，而不是重新实现一套 coding-agent runtime。
- **`user-confirmed`：** 当前不再要求 OpenCode、Codex、Claude 等其他 backend；以后
  backend 只保留 Pi。
- **`user-confirmed`：** 本次同时更新开发规范、面向 coding agent 的 skills/机制，
  并实际实现 Pi Runtime Bridge。
- **`user-confirmed`：** Pi 提供的相关能力应尽量完整接入；现在就实现 sub-agent，
  HeWo 示例可以很简单，例如输出当前时间和天气。
- **`user-confirmed`：** workflow 使用 Pi 的标准做法；本仓库作为下游 Agent repo
  的示范样板。
- **`user-confirmed`：** 可以使用很薄的 TypeScript extension/package 作为正式
  runtime 实现。
- **`user-confirmed`：** runtime 至少需要认真考虑 skill、knowledge、tools、
  sub-agent、workflow、hooks、commands 等组件，并判断是否还有遗漏。

### 4.2 Agent 提议、等待确认

- **`agent-proposed`：** 将 runtime 分为四层：
  1. **产品语义层（声明式）**：identity/system prompt、knowledge、memory policy、
     skills、workflows、commands/prompt templates、runtime manifest；
  2. **运行时行为层（可组合）**：Pi extensions、tools、hooks/events、sub-agents、
     session/state、permission/policy、provider adapter、UI；
  3. **外部能力层（叶子适配）**：已有 CLI/API/MCP/本地服务，以及必要时的脚本；
  4. **Pi bridge 层**：Pi 资源注入、模式、凭据、package 与可选 SDK/RPC host。
- **`agent-proposed`：** 脚本的默认定位为“无状态、可单独验证、面向外部系统的
  叶子工具/适配器”。脚本不能默认承载产品身份、长期状态、agent loop、sub-agent
  DAG、策略决策、会话恢复、模型调用或多个组件之间的主编排。
- **`agent-proposed`：** 为每种组件定义“职责、输入、输出、生命周期、状态、是否
  进入模型上下文、Pi 映射、何时升级到 extension”的契约，并由 definition/audit
  检查结构与边界。
- **`agent-proposed`：** Pi 是唯一 backend；加载路径为 Pi 原生资源：`--skill`、
  `--prompt-template`、`--extension`、显式 tools、agent definitions、package
  manifest、session/RPC/SDK 能力；仅把 identity 或必要的 context 作为 system
  prompt 注入。不再为其他 backend 维护 adapter 要求。`runtime/package.json` 作为
  Pi resource manifest 的唯一真源；`agent.yaml` 只保留 scaffold 元数据，不能声明
  第二套 Pi resource 清单。
- **`agent-proposed`：** workflows 不假装是 Pi core primitive：声明式 workflow
  用 Markdown/manifest 表达步骤与成功条件；需要循环、并发、事件触发或 sub-agent
  时由 extension/package 实现，必要时才调用外部 CLI/脚本。
- **`agent-proposed`：** sub-agent 本阶段直接实现为随 runtime 发布的受控、很薄的
  TypeScript extension/package，采用 Pi 的 single/parallel/chain 工作流模型；HeWo
  先提供一个“当前时间 + 天气”示例。默认验收使用 `fixture` weather provider：固定
  输入、固定结果、无网络；公网天气 API 只作为显式 `live` opt-in 演示。sub-agent
  使用独立 `--no-session` Pi 进程、最小工具 allowlist 和硬性预算。plan mode、MCP 等
  仍按 Pi 的 extension/package 机制接入并在能力矩阵中覆盖，不在仓库中另写 model
  client/session/tool loop。
- **`agent-proposed`：** memory 需要拆成短期 session state、可恢复 extension state、
  产品允许的 durable knowledge/memory policy；默认不把 raw session 或个人数据变成
  runtime 资源。HeWo 本阶段继续禁用 durable memory，只记录接口、拒绝写入和隐私边界。

### 4.3 已拒绝的替代方案

- **`agent-proposed / rejected`：** “彻底禁止所有 Python/shell”。原因：叶子工具、
  已有 CLI 适配、构建/发布基础设施仍需要脚本；问题是职责越界而非语言本身。
- **`agent-proposed / rejected`：** 只增加一条“不要写脚本”的 prompt。原因：无法
  给出组件选择顺序、边界、验证方式，也无法阻止 launcher/package 层实际丢失 runtime
  组件。
- **`agent-proposed / rejected`：** 为产品实现一个新的 Python/Node agent loop。
  原因：违反 reuse-first，并重复 Pi 已提供的会话、工具、provider、事件与执行循环。
- **`agent-proposed / rejected`：** 把所有需求都实现成 skill/Markdown。原因：hooks、
  typed tools、状态、权限、事件、sub-agent 与 provider 集成需要 extension/API；
  声明式优先不等于声明式包办一切。
- **`agent-proposed / rejected`：** 直接依赖本机全局 subagent/plan extension。
  原因：发布物必须可复现、可审计、与开发机解耦；应显式打包并固定可选能力。
- **`agent-proposed / rejected`：** 继续把所有 runtime 文件拼进一个 system prompt。
  原因：失去 progressive disclosure、command/resource provenance、动态 tool loading
  与生命周期语义，且无法表达 executable extension。

## 5. 非目标

- 不在本计划中实现一个新的 LLM client、agent loop、session manager、approval loop
  或通用 workflow engine。
- 不把开发 coding agent 的 `.agents/`、AGENTS.md、评估脚本或 benchmark 逻辑复制到
  `src/hewo/runtime/`。
- 不强制把 Pi 没有内建的 plan mode、MCP 或 todo 假装成 core；sub-agent 按用户要求
  在本阶段实现最小示例，其他扩展能力通过真实需要、标准 package/extension 或明确
  deferred 处理。HeWo 的默认 sub-agent 验收不得依赖公网网络。
- 不用 benchmark-specific prompt 或脚本绕过产品设计。
- 不读取、复制、提交任何 provider credentials、auth store、raw session 或个人数据。
- 不因为需要验证就恢复被项目约束禁止的 `docs/` 或 Agent unit-test suite；使用现有
  definition/audit/clean-container/provider-backed Docker E2E 契约。
- 不把 Pi 的纯 host 能力强行伪装成 HeWo 产品语义；但必须为所有适用能力建立矩阵，
  并为 RPC/SDK、UI/theme、provider registration 等能力提供明确的 host 验证入口。

## 6. 工作分解

### C1 — 形成 Runtime Component Contract

**Gate：** 文档审查 + `git diff --check`。

- 在开发侧定义 component decision tree：需求 → 声明式资源 → Pi extension →
  叶子工具 → 脚本（仅最后一步）。
- 逐项定义 identity、knowledge、memory、skill、workflow、command/prompt template、
  tool、hook/event、extension、sub-agent、session/state、provider/model、permission、
  UI、package/manifest、external adapter 的职责与反例。
- 明确“进入模型上下文 / 仅运行时 / 仅开发侧”的边界。
- 将本机 Pi 0.85.1 的可用 primitive 与“Pi 不内建但可扩展”的能力做映射，并注明
  版本/来源，避免把第三方 extension 当成 Pi core；其他 backend 不再进入本计划的
  产品 acceptance matrix。

### C2 — 更新开发 coding agent 的治理与模板规范

**Gate：** `python3 scripts/check-template-registry.py`；相关 Markdown 链接与
结构审计通过；Pi-only backend 触点清理扫描通过。

- 修改 `AGENTS.md`、`DEV.md`、`.agents/workflows/agent-development.md` 和必要的
  `.agents/skills/*`，加入高层优先规则、脚本升级条件、component review checklist、
  backend gap issue 要求和产品/开发边界。
- 在开发侧 `.agents/knowledge/` 增加 component contract 文档；不得把开发说明写入
  `src/hewo/runtime/` 或产品载荷。产品 runtime 只包含可执行/可加载的 Pi 资源。
- 让初始化/Phase 1 prompt 不再把“tools”默认为 Python 项目，而是要求先提交
  component choice 与 rationale。
- 增加 backend 收敛清单：枚举并删除/改写 OpenCode、Codex、Claude 的 launcher、
  Docker、安装、文档和验收触点；扫描确保不再存在隐式 fallback 或多 backend contract。

### C3 — 定义并实现 Pi Runtime Bridge 与 Pi-native package

**Gate：** `./scripts/validate-definition.sh hewo`；clean image 中 Pi 能发现并加载
runtime resources；无凭据时只标 infrastructure-only。

- 设计并落地唯一的 Pi runtime manifest/package contract，声明 identity、knowledge、
  memory policy、skills、prompt templates/commands、workflows、agent definitions、
  extensions/hooks、tools、themes、provider configuration 和可选 SDK/RPC host。
- 修改 `distribution/launcher`，让 Pi 原生加载适用资源：`--skill`、
  `--prompt-template`、`--extension`、显式 tools、agent/workflow 入口；禁止把
  executable extension 当作 Markdown 拼接。所有资源路径来自 manifest 的相对路径，
  先规范化并拒绝绝对路径、`..` 穿越、空名和 shell 插值；建立资源-文件-加载命令对照表。
- 修改 installer/Docker/release 逻辑，确保 Pi extension/package 的源码、依赖、
  agent definitions 和 prompt templates 可复现进入产品载荷，同时继续排除 AGENTS.md、
  开发资源与凭据。
- 采用 `runtime/package.json` 作为唯一 Pi resource manifest；锁定 package/lockfile、
  受信安装源、`npm ci --ignore-scripts`/等价 frozen install、依赖审计、离线/缓存行为，
  禁止 package lifecycle scripts，并用 `npm pack --dry-run`/packlist 检查 release 内容
  与哈希，避免 `agent.yaml` 与 package 出现两套真源。
- 将当前其他 backend 代码与文档清理/收敛为 Pi-only contract，不再保留“其他 backend
  必须可用”的验收要求。
- 建立默认拒绝的 capability policy：高危 hook/tool 只有显式 allowlist、trusted
  project 和受保护路径规则同时满足时才启用；资源路径必须是 manifest root 下的规范化
  相对路径，拒绝绝对路径、`..` 穿越和 shell 拼接；取消必须传播并清理 session-scoped
  资源。
- 明确 project trust、`--no-*`、资源 provenance、`--tools`、`--mode rpc/print`、
  session directory、offline 与 package dependency 策略；默认禁止出站网络，只有显式
  live weather capability 才能联网，并须经过 allowlist/超时/取消策略。

### C4 — 用 HeWo 实现 Pi 全量组件示例与脚本边界

**Gate：** 每个适用 Pi 能力都有可运行示例或明确的“不适用”理由；脚本静态审查不
发现高层职责越界。

- 将 HeWo smoke 保持为最小基础设施探针，不把 `hewo_tool.py` 扩展为通用 runtime。
- 以 HeWo 建立声明式 identity、knowledge、skill、workflow、prompt template/command、
  memory policy、theme 与 package manifest 示例。
- 实现最小 TypeScript extension：typed tool、生命周期 hook、permission/path gate、
  session/state、UI/status（适用模式下）和 provider/resource integration。
- 实现 Pi sub-agent：沿用 Pi subagent extension 的 agent definition + single/parallel/
  chain workflow 标准，至少提供一个简单任务，输出当前时间与天气；默认 weather
  provider 为 deterministic fixture，可选公开 API 仅显式开启。sub-agent 使用独立
  `--no-session` 进程、最小只读/自定义工具 allowlist，不继承父级高危权限；定义最大
  轮次、总时长、并发上限、取消传播、失败重试上限、结果合并和资源回收。
- 对 session/compaction/tree、RPC/SDK、动态 tools、package provenance 等能力补充
  示例或验证入口；Pi core 没有的 plan/MCP/todo 等能力不得伪装成 core，采用 extension/
  package 方式明确接入或记录 deferred。
- 为脚本工具建立约束：输入输出契约、幂等/错误码、超时/取消、输出截断、无状态、
  secret safety、独立验证命令；脚本只能被 skill/extension/tool 以叶子方式调用。

### C5 — 验证产品 runtime 与发布边界

**Gate：** 结构验证、template audit、clean-container check 通过；有凭据的行为验证
  必须通过 `docker/run-hewo-e2e.sh` 并记录 backend/provider/model/credential-source。

- 运行 `./scripts/validate-definition.sh hewo`。
- 运行 `python3 scripts/check-template-registry.py`。
- 加载并运行 template release-readiness audit；若涉及跨文件旧路径，再运行
  `agent-consistency-audit --agent hewo --strict`。
- 运行 infrastructure health；验证没有引入平行 backend runtime。
- 使用 Pi backend、实际可用 provider/model 与明确的 `--pi-auth-file`/其他安全凭据
  flag，通过 Docker helper 观察：identity、skill/knowledge/workflow/command、tool、
  extension、sub-agent 及其时间/天气结果；同时覆盖无网络 deterministic provider。
  没有实际 provider 注入时标记 `infrastructure-only` 或 `blocked`，绝不报告为
  agent-behavior。
- 额外验证 hook/tool 默认拒绝、protected path、project trust、资源路径规范化拒绝、
  sub-agent 独立 session/工具 allowlist/超时/取消/并发限制、天气 provider 失败降级、
  extension 资源回收和无网络 fixture 路径。
- 只验证 Pi backend；不再把其他 backend 纳入 acceptance matrix。
- 检查 release/Docker payload：runtime 组件在内，AGENTS.md、`.agents/`、开发目录、
  凭据、raw session 不在内。

### C6 — 复盘并固化组件选择规则

**Gate：** 所有开放项已关闭或明确 deferred；组件矩阵、脚本边界和 Pi-only contract
均已形成下游可复用示范。

- 将实际验证中的 Pi 版本限制、resource provenance、权限拒绝、sub-agent 预算和脚本
  越界风险记录在开发侧 issue/memory，而不是 runtime prompt。
- 更新 component matrix、开发 prompt 和 downstream adaptation 说明。
- 不把 deferred 的 Pi 扩展能力伪装为已实现；明确每一项的适用性、验证入口和后续触发条件。

## 7. 文件地图

### 预期修改（待用户确认范围）

- `AGENTS.md`
- `DEV.md`
- `.agents/workflows/agent-development.md`
- `.agents/skills/template-agent-development/SKILL.md`
- `.agents/skills/agent-definition-validation/SKILL.md`（若验证契约需更新）
- `.agents/skills/agent-consistency-audit/SKILL.md`（若新增边界检查）
- `src/hewo/agent.yaml`（仅 scaffold 元数据，不作为 Pi resource manifest）
- `src/hewo/runtime/package.json`（Pi resource manifest 唯一真源）
- `distribution/launcher`
- `distribution/install.sh`
- `docker/Dockerfile`
- `scripts/build-release.sh`
- `scripts/validate-definition.sh`
- `.agents/template-content-registry.json`
- 现有 OpenCode/Codex/Claude 相关 launcher、Docker、README/DEV 逻辑（收敛或删除为 Pi-only）

### 预期新增（位置/是否产品载荷待确认）

- Runtime component contract / architecture reference
- Pi extension/package 入口与 `src/hewo/runtime/package.json` / lockfile
- Pi agent definitions、prompt templates/commands、themes、workflow 入口
- HeWo sub-agent（当前时间 + 天气）及其标准 single/parallel/chain workflow 示例
- 开发侧 component decision tree、脚本边界检查或审计规则

### 明确不修改

- `PLAN-agent-visualization-self-bootstrap.md`
- provider credentials/auth stores、raw sessions、用户私有数据
- Pi/OpenCode/Codex/Claude 的上游源码或其核心执行循环

## 8. 验收标准

1. 开发 coding agent 面对新需求时有一套可执行的 component decision tree，并明确
   脚本是叶子适配器而非默认产品实现。
2. 文档完整覆盖至少：identity/system prompt、knowledge、memory policy/state、
   skills、workflows、commands/prompt templates、tools、extensions/hooks/events、
   sub-agents、session、provider/model、permissions、UI、packages/manifest、外部
   adapters，以及它们之间的边界。
3. 每个组件都说明：职责、生命周期、模型上下文可见性、Pi primitive、状态/错误/
   取消、何时不应使用、与脚本的关系。
4. Pi 不内建的 sub-agent/plan/MCP 等能力被明确标注为 extension/package/SDK 能力，
   不再被误写成 Pi core feature。
5. 产品 runtime 不再只靠 `--append-system-prompt` 承载所有高层资源；Pi 原生
   resource/extension 能按组件加载，并且 release 可复现。
6. 未经 rationale 与 backend-gap 记录，不新增 Python/shell 高层编排、model client、
   session manager、approval loop 或 tool loop；sub-agent 必须使用独立 session、最小
   工具 allowlist、最大轮次/时长/并发/重试预算，取消后不得遗留子进程或临时资源。
7. `validate-definition`、registry/audit、clean-container 和 release boundary 检查
   均通过；package 使用 frozen install、禁用 lifecycle scripts、packlist allowlist 和
   完整性校验；脚本叶子工具具备独立、可重复、无凭据的验证契约。
8. 至少一条真实 pi backend Docker E2E 观察到产品 runtime 的目标高层行为，并报告
   `backend`、`provider`、`model` 与 credential-source flag；没有凭据时不作行为通过
   声明。另有无网络 deterministic fixture 验收，并验证 sub-agent 的独立 session、工具
   allowlist、预算、取消、重试和资源回收。
9. 产品只保证 Pi backend；runtime 中的 Pi 专属资源必须通过显式 Pi manifest/bridge
   加载，不允许再留下隐式的多 backend contract；Pi-only 扫描必须对 launcher、Docker、
   installer、README/DEV、manifest 和验收脚本逐项通过。

## 9. 验证

静态/结构：

```bash
python3 scripts/check-template-registry.py
./scripts/validate-definition.sh hewo
git diff --check
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent hewo --strict
python3 .agents/skills/template-release-readiness/scripts/audit_template_release.py --agent hewo
```

Pi 能力与资源发现（secret-free）：

```bash
pi --version
pi --help
pi --list-models
# 构建产物存在 → Pi resource discovery → Pi command/tool/sub-agent execution
# 另行检查 manifest 路径规范化、无网络 fixture、package packlist 和 Pi-only backend scan
```

脚本/extension/package（按实际新增内容选择）：

```bash
bash -n distribution/launcher distribution/install.sh
bash -n docker/run-hewo-e2e.sh
python3 -m py_compile src/hewo/runtime/tools/*.py
# 若新增 TypeScript extension/package，使用其 package 声明的 lockfile/install/typecheck gate
```

运行时边界：

```bash
python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py --agent hewo
# 再通过 docker/run-hewo-e2e.sh，以显式 --pi-auth-file / --api-key-env / --bundle 注入实际凭据
```

行为证据报告必须包含：`agent`、definition revision、`backend=pi`、实际 provider、
实际 model、credential-source flag、artifact/trajectory（仅 scrubbed 路径），并区分
`infrastructure` 与 `agent-behavior`。

## 10. 风险与开放项

1. **“全量 Pi 能力”（panel-adapted）：** 所有适用于产品 runtime 的能力都要有
   component matrix 和示例；RPC/SDK、UI/theme、provider registration 等偏
   host/infrastructure 能力必须有验证入口，但不强行变成 HeWo 的领域产品语义。已锁定。
2. **Manifest（panel-adapted）：** 使用 `runtime/package.json` 作为 Pi resource manifest
   的唯一真源；`agent.yaml` 只保留 scaffold 元数据；C3 必须验证发布/安装闭环。已锁定。
3. **Workflow（user-confirmed + panel-confirmed）：** 使用 prompt template + extension
   tool 的 Pi single/parallel/chain 模型，不另建通用 DAG engine。已锁定。
4. **天气数据源（panel-adapted）：** 默认 deterministic weather provider 进入验收；
   公共天气 API 作为显式 opt-in 演示，并定义位置输入、超时、失败降级和隐私边界。已锁定。
5. **Hooks 安全（panel-adapted）：** 默认拒绝；显式 capability allowlist、trusted project、
   protected paths、取消传播与生命周期清理全部纳入验收。已锁定。
6. **Commands（agent-proposed）：** 同时示范 skill command、prompt-template command 与
   `registerCommand`，通过 RPC `get_commands` 验证 provenance。
7. **Runtime 依赖（panel-adapted）：** package/lockfile、受信安装源、frozen install、禁用
   lifecycle scripts、packlist、离线/缓存策略、依赖审计和 release 哈希校验纳入 C3/C5。
8. **Durable memory（agent-proposed，HeWo 默认禁用）：** 仅定义接口、拒绝写入和隐私
   边界，不实现跨 session 用户记忆。
9. **联网研究：** 本轮已用本机 Pi 0.85.1 的 CLI/help/docs/examples 做版本对应的事实核验；
   若需要比较 upstream 最新版本、Agent Skills 标准、MCP/工作流生态，另行授权联网研究。
10. **验收成本：** Pi extension/sub-agent 的真实 E2E 需要明确可用 provider/model 与只读
    credential source；否则只能完成 infrastructure-only 验证。

## 11. Reviewer dispositions

| Finding | Reviewer(s) | Disposition | Rationale |
| --- | --- | --- | --- |
| Pi package/manifest 发布路径未锁定，可能继续排除 package.json/lockfile | feasibility-001 | adapted | 固定 `package.json` 为唯一 runtime resource manifest，并将 package/lockfile 复制、安装、审计和 release 校验纳入 C3/C5。 |
| 天气 provider 未锁定，E2E 可能受公网波动影响 | feasibility-002; alternatives-002 | adapted | 默认 deterministic provider 进入验收；公网 API 只作为显式 opt-in 演示，并定义失败降级。 |
| Pi resource discovery/load/execute 闭环不足 | feasibility-003 | adapted | C3/C5 增加资源-文件-加载命令对照表，以及“产物存在、Pi 可发现、Pi 可执行”三段验证。 |
| Pi extension 高权限边界不足 | risk-001 | adapted | 加入默认拒绝、capability allowlist、trusted project、protected paths、取消传播和可验证拒绝路径。 |
| package 供应链与可复现安装不足 | risk-002 | adapted | 纳入 lockfile、受信安装源、离线/缓存策略、依赖审计、release 内容与哈希校验。 |
| sub-agent 缺少预算、取消、并发和资源回收硬约束 | risk-004 | adapted | 将最大轮次、总时长、并发、取消、重试、结果合并和资源回收列为合同与 E2E 验收。 |
| backend 清理可能残留隐式 fallback | risk-005 | adapted | C2 增加逐项 backend 触点清理清单和 Pi-only 扫描 gate。 |
| “全量 Pi 能力”可能扩张到不必要的平台工作 | alternatives-003 | adapted | 产品适用能力必须示范；UI/theme、RPC/SDK、provider registration 等 host 能力提供验证入口，不强行变成领域语义。 |
| manifest 两套真源风险 | alternatives-001 | adopted | 明确 `package.json` 为唯一 runtime manifest，`agent.yaml` 仅保留模板元数据。 |
| 第一次 feasibility seat 达到 turn limit | planning-run | deferred | 已按同一模型重试并获得 findings；记录原始 seat 未完整返回，不静默丢弃。 |
| 第一次 alternatives seat provider overload | planning-run | deferred | 已按同一模型重试并获得 findings；记录 fallback 未触发，因为重试成功。 |
| 三个 reviewer 的共同 verdict 是 needs-attention | all reviewers | adapted | 吸收为上述可执行 gates；计划需再进行一次 L4 panel review 后才能执行。 |
| Component contract 与 manifest 落点仍不够固定 | feasibility-round2; alternatives-round2-fallback | adopted | 固定 `runtime/package.json` 为唯一 Pi resource manifest，开发 contract 固定放在 `.agents/knowledge/`，补充资源-文件-加载-执行-回收闭环。 |
| deterministic weather provider 缺少注入点、输入、断言和降级合同 | feasibility-round2 | adapted | 为 fixture 定义显式 mode、固定输入/结果、注入接口、断言和失败降级；live API 只 opt-in。 |
| Pi-only cleanup gate 过于抽象 | feasibility-round2 | adopted | 列出 launcher、Docker、installer、README/DEV、manifest、验收脚本的扫描对象和 fail 条件。 |
| sub-agent 仍可能继承父级权限/session | risk-round2 | adopted | 强制独立 `--no-session`、最小工具 allowlist、只读工作区/secret 隔离、预算和取消清理。 |
| package lifecycle scripts 与 release packlist 未限制 | risk-round2 | adopted | 使用 frozen install、`--ignore-scripts`、受信源、依赖审计、`npm pack --dry-run` 和 files allowlist。 |
| runtime-wide 出站网络策略缺失 | risk-round2 | adopted | 默认禁止网络；只有显式 live weather capability 允许 allowlisted endpoint，并受 timeout/cancel 约束。 |
| launcher 资源路径可能有注入/穿越风险 | risk-round2 | adapted | manifest 只允许 root 下规范化相对路径，拒绝绝对路径、`..`、空名和 shell interpolation。 |
| workflow/subagent/host 边界需收紧 | alternatives-round2-fallback | adapted | workflow 固定为 Pi prompt template + extension single/parallel/chain；RPC/SDK/theme/provider registration 仅作 host 验证入口。 |
| 第二轮 alternatives seat 初始与重试失败 | planning-run | deferred | px-plan-reviewer 类型在本轮 registry 中不可用，自动回退 general-purpose；gpt-5.5 两次达到 turn limit，gpt-5.4 不受当前 ChatGPT account 支持，gpt-5.4-mini 成功返回关键 findings；已报告所有切换与失败。 |

## 12. Unit execution log

| Commit | Status |
| --- | --- |
| C0 | plan authored and user-aligned; panel rounds 1-2 completed; revision pending final user re-alignment |
| C1 | not started |
| C2 | not started |
| C3 | not started; Pi-only scope confirmed; package.json sole-manifest decision proposed and panel-adapted |
| C4 | not started |
| C5 | not started |
| C6 | not started |

## 13. 对齐记录

### Round 1 — 初始用户需求（当前轮）

**用户输入：** coding agent 开发产品 agent 时过度偏好写 Python 等脚本；产品 agent
应是更高层的系统，脚本只能在适合时使用；因为使用 pi backend 是为了灵活性，需要
系统考虑 skill、knowledge、tools、sub-agent、workflow、hooks、commands 等组件，
并可能查找更多组件。

**本轮计划变更：**

- 将问题定义为 runtime architecture + development governance，而不是简单增加“不要
  写脚本”的提示语。
- 以本机 Pi 0.85.1 的 CLI/help、完整相关 docs 与 examples 建立 primitive map。
- 新增四层架构提案、component contract、Pi bridge、脚本叶子边界、发布/验证边界。
- 将 Pi-only、Pi-native workflow/sub-agent、manifest、memory policy、天气数据源和
  “全量 Pi 能力”的适用范围列为剩余对齐项，不在用户确认前擅自执行。

### Round 2 — 用户反馈（当前轮）

**用户输入：** 只保留 Pi backend；同时更新开发规范、面向 coding agent 的 skills/机制
和 Pi Runtime Bridge；现在实现简单 sub-agent（时间与天气）；workflow 使用 Pi 标准做法，
本仓库作为下游示范；允许薄 TypeScript extension/package；询问 durable memory 的含义。

**本轮计划变更：**

- 将 Pi 从默认 backend 提升为唯一 backend，删除其他 backend acceptance 要求。
- 将 Pi bridge 从条件项改为本次正式工作项。
- 将 sub-agent 从可选占位改为 HeWo 的最小真实示例，并采用 Pi 的 agent definition +
  single/parallel/chain workflow 形式。
- 扩展开发规范覆盖 Pi 的资源、extension、hooks、tools、commands、session/state、UI、
  package、RPC/SDK、provider 与安全边界。
- 将 durable memory 保持为需要额外确认的产品策略：它指跨 session 主动持久化并在后续
  session 检索的用户偏好、项目事实或决策，区别于当前 session、compaction summary 和
  静态 knowledge；当前 HeWo 默认仍不持久化用户 memory。

### Round 3 — Panel round 1 findings 与 disposition

**Panel 输入：** feasibility、risk、alternatives 三个 L4 reviewer seat 均指出计划方向
可行但需要锁定 package manifest、资源加载闭环、天气可复现性、extension 权限、sub-agent
预算/取消/并发、供应链审计和 Pi-only 清理门槛。一个 seat 初次达到 turn limit，一个
seat 初次 provider overload，均按同一模型规则重试；重试成功，未触发 provider fallback。

**本轮计划变更：**

- 将 panel findings 逐条登记在第 11 节，没有静默丢弃。
- 将 `package.json` 作为唯一 Pi runtime resource manifest 的方案固化为 panel-adapted
  提议，`agent.yaml` 仅保留模板元数据。
- 将 deterministic weather provider 作为默认验收路径，公共天气 API 降为显式 opt-in。
- 增加默认拒绝 capability policy、package/lockfile/安装源/哈希审计、sub-agent 预算与
  取消合同、backend 触点清理 gate，以及 resource discovery 三段验证。
- 将“所有适用 Pi 能力必须示范；host 能力必须有验证入口但不强行变成领域语义”写入
  计划。

由于计划发生实质性修改，按 planning 规则必须再次进行 L4 panel review；第二轮 panel
发现仍需补充安全、manifest 闭环和具体触点后，已继续修订计划；在下一轮 panel 完成且
用户重新确认修改后的 digest 前不进入 worktree 执行。

### Round 4 — Panel round 2 findings 与 disposition

**Panel 输入：** 第二轮 reviewer 认为仍需锁定 component contract/manifest 落点、fixture
weather 的注入与断言、Pi-only 清理触点、sub-agent 独立 session/工具/secret 隔离、
package lifecycle/packlist、runtime-wide 网络策略和资源路径规范化。alternatives seat
因 `px-plan-reviewer` registry 不可用自动回退 general-purpose；gpt-5.5 两次达到 turn
limit，gpt-5.4 不受当前 ChatGPT account 支持，gpt-5.4-mini 返回关键 findings。

**本轮计划变更：**

- component contract 固定在 `.agents/knowledge/`，`runtime/package.json` 固定为唯一
  Pi resource manifest，`agent.yaml` 只保留 scaffold 元数据。
- fixture weather 增加显式 mode、固定输入/结果、注入接口、断言和失败降级；默认验收
  禁止公网网络。
- 增加 sub-agent 独立 `--no-session`、最小工具 allowlist、只读工作区、secret 隔离、
  最大预算、取消清理和 runtime-wide 默认拒绝网络。
- 增加 `--ignore-scripts`、frozen install、packlist/files allowlist、资源路径校验和
  逐项 Pi-only cleanup gate。

本轮 panel 结果仍需最后一次用户重新确认修改后的 plan digest；确认后才能调用
`pi_dev_modes_align` 并创建用户要求的新 worktree。
