# Agent 开发者指南

> **Role of this document**
> - **Audience:** a human developer building, validating or releasing an Agent from this template.
> - **Authority:** informative. It is the working manual; where it disagrees with `AGENTS.md` or a gate script, those win.
> - **Tone:** procedural and specific; commands with the conditions under which they fail.
> - **Language:** Chinese, with English identifiers, paths and commands.
> - **Contains:** environment setup, the definition/validation/E2E/benchmark procedures, build, install, release, and the pre-submit checklist.
> - **Excludes:** binding agent operating rules (see `AGENTS.md`), end-user instructions (see `USER.md`), product behavior (see `src/hewo/runtime/`), and machine-specific facts (see `DevelopmentMachine.md`).

本文先定义本仓库中的两个不同身份，避免把“开发者”与“产品”混为一谈：

- **开发 coding agent**：运行 Codex、OpenCode、Claude Code、pi 或其他 coding-agent
  CLI、并维护本仓库代码的人机代理。它读取根目录和 `.agents/` 下的
  `AGENTS.md`、skills、memory、knowledge 与 workflows；这些内容是开发流程，
  不是产品行为，也绝不会随产品发布。
- **被开发的产品 agent**：本仓库要构建、安装并交付给最终用户的 `hewo`。它的
  唯一产品源码和行为定义在 `src/hewo/`，其中真正进入产品载荷的是
  `src/hewo/runtime/`（不包括任何 `AGENTS.md`）。产品 agent 读取 runtime 中的
  identity、skills、knowledge、workflows 和 tools；它不是负责维护本仓库的
  coding agent。

因此，当前 template 仓库的修改规则是：维护基础设施和开发流程时由开发
coding agent 工作；实现 hewo 的产品行为时只修改 `src/hewo/`。不要因为文档、
benchmark 或 runtime 文件中出现 “Agent” 就切换身份，也不要把 `AGENTS.md`、
`.agents/` 或开发证据当成 hewo 的产品上下文。本文中出现的
`src/<agent_name>/` 仅表示下游仓库复制本 template 后的占位路径，不表示本仓库
可以把 hewo 实现分散到其他 `src/` 子目录。

本文面向维护 template、开发 `hewo`、创建下游 Agent scaffold 和记录验证证据的开发者。
最终用户应阅读 [USER.md](USER.md)。


## 开发 Skill 入口

使用本 template 创建 Agent、同步 template 更新，或把现有 Agent 仓库迁移
到本结构时，开发 coding agent 应首先加载：

```text
.agents/skills/template-agent-development/SKILL.md
```

它会按当前任务渐进式加载一个 sub-skill：新建 Agent、同步 template，或迁移
现有仓库。修改本仓库的 `src/hewo/` 或准备 hewo release 时，再使用
`.agents/skills/agent-definition-validation/SKILL.md` 完成当前验证流程。只有在
为下游仓库编写初始化说明时，才使用 `src/<agent>/` 这类占位路径。

每次发布 template 前，还必须加载
`.agents/skills/template-release-readiness/SKILL.md`。它审核整个 template
是否仍适合下游 Agent dev repo、登记表是否完整、template-specific 内容是否
可能泄露，以及 release/product 边界是否安全。

同步或创建下游仓库前，必须先阅读登记表
`.agents/template-content-registry.json`。它是 template 专属内容、可选择
同步的实现、以及 memory/knowledge/workflows 中性占位符的唯一清单；同步
细节见 `.agents/skills/template-agent-development/references/sync-template.md`。不要复制
`.agents/` 整目录。

登记表覆盖整个仓库，而不只是 `.agents/`。新增或同步 template 内容后，先
确认所有 Git 跟踪文件都已经被登记：

```bash
python3 scripts/check-template-registry.py
```

这个检查会在新增文件没有归类时失败，避免下游无意间继承未审查的内容。

## 给下游 coding agent 的初始化 Prompt（Phase 0）

当前 prompt 是下游仓库的通用模板。这里的 `src/hewo/` 是本 template 仓库唯一的
最小产品 agent 示例；下游执行时才将它适配为变量中的 `src/<agent_name>/`，不要
反过来把下游占位路径用于本仓库的 hewo 实现。

```text
你是负责维护下游仓库的**开发 coding agent**，不是下游将要交付的**产品 agent**。
产品 agent 的身份和用户可见行为必须写在下游仓库的 `src/<agent_name>/runtime/`；
本 prompt、`AGENTS.md`、`.agents/` 和验证脚本只指导开发 coding agent，不能被
复制进产品 runtime 或当作产品行为。

你正在维护下游 coding-agent 开发仓库。请以
https://github.com/a-green-hand-jack/coding-agent-template.git 为 template
上游，执行 Phase 0: Initialize，建立一个最小可运行、可供后续实现的 Agent
dev repo scaffold。

变量：
- Agent 名称：<agent_name>
- 目标 backend：pi（本 template 只支持 pi；不要引入第二个 backend）
- 目标 provider/model：<provider/model>

初始化边界：
- 只创建下游仓库基础目录、`src/<agent_name>/agent.yaml`、最小 runtime 配置、
  下游自己的 `.agents/` 目录和中性占位符，以及必要的 Docker、distribution、
  launcher、脚本和工具环境配置。
- 可以从 `src/hewo/` 派生可执行 scaffold，但只保留最小 HeWo smoke 资源作为
  临时基础设施探针。HeWo 的名称、身份、领域语义、历史证据和产品假设不得继承，
  smoke 资源不得扩展为产品功能。
- 所有临时内容都必须带有明显的 `TODO: replace during implementation` 标记。
  初始化时不要求填写真实产品 identity，也不要求创建产品专属 knowledge。

初始化阶段禁止：
- 编写产品 identity 或产品声明；
- 添加领域专属 knowledge，设计正式 skills 或业务 workflows；
- 增加领域工具、业务执行逻辑、产品 benchmark 或产品验收证据；
- 修改执行循环、model client、session、approval 或 tool loop；
- 生成 release-ready 的产品行为，或把 provider 响应描述为已实现的 Agent。

执行顺序：
1. 阅读 template 的 AGENTS.md、DEV.md、
   .agents/skills/template-agent-development/SKILL.md，以及
   .agents/template-content-registry.json；先运行
   `python3 scripts/check-template-registry.py`。
2. 使用 registry 和 sync-template sub-skill 做选择性同步。不要复制 template
   仓库或 `.agents/` 整目录，不要复制任何 template 的 AGENTS.md、Issue/HeWo
   历史、benchmark/release 证据、registry 文件或 provider 凭据。
3. 建立 `src/<agent_name>/` 的最小 scaffold；复制 `src/hewo/` 时排除
   AGENTS.md，并清理 HeWo identity、产品语义和非必要 smoke 内容。runtime
   文件可以存在，但只能是通用占位内容并带 TODO 标记。
4. 建立下游自己的 `.agents/knowledge/`、`.agents/memory/`、
   `.agents/workflows/`，只复制中性 PLACEHOLDER.md 作为起点；不要在这里写入
   产品设计。为下游目录重新编写 scoped AGENTS.md。
5. 只按需选择性安装并适配开发 skill；保持 scaffold、backend、LLM provider/model
   独立，不重复实现已有 coding-agent CLI 的执行循环、model client、审批或
   tool loop。根据 backend/provider 组合适配 Docker、distribution、launcher
   和工具环境，但不要加入业务逻辑。
6. 运行结构检查和基础设施检查（例如
   `./scripts/validate-definition.sh <agent_name>`、
   `python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent <agent_name> --strict`
   和
   `python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py --agent <agent_name>`）。
   初始化证据只能使用以下标签：
   `structure`（文件、配置和目录结构）、`infrastructure`（Docker、CLI、工具
   环境、provider 注入和模型响应）、`agent-behavior`（产品 identity、skill、
   workflow 和工具行为的真实观察）。Phase 0 最多产生 `structure` 和
   `infrastructure` 证据；provider-backed 响应必须标记为
   `infrastructure evidence`、`not Agent behavior evidence`。
7. 对每个目标 backend/provider 运行真实的 provider-backed Docker E2E；凭据只能
   运行时注入，不能写入 Git。检查 release 边界不包含 AGENTS.md、`.agents/`、
   development 目录、auth store 或 credentials，但不要生成产品 release。

初始化报告必须包含：
- 初始化创建的文件；
- 复用的 registry 条目；
- 明确排除的 template-specific 内容；
- 保留的 HeWo smoke 内容及其“仅用于基础设施验证”的状态；
- backend/provider E2E 结果和证据标签；
- 尚未实现的产品内容；
- 下一阶段需要用户授权的事项。

完成初始化检查和基础设施 E2E 后立即停止并输出报告。等待用户明确发出
“开始实现 Agent 产品行为”之类的授权指令；不得自动进入 Phase 1，也不得
把初始化报告当作产品验收。
```

## 从初始化进入 Agent 实现的 Prompt（Phase 1）

只有用户明确授权后，才把下面这段交给**开发 coding agent**。这里的“Agent 产品行为”
特指下游仓库的产品；在本 template 仓库中则特指 `src/hewo/runtime/`，不是让开发
coding agent 变成 hewo，也不是修改 `.agents/` 来实现 hewo：

```text
你是开发 coding agent，正在实现被开发的产品 agent，而不是扮演它。当前 template
仓库的产品 agent 是 hewo，所有产品改动必须位于 `src/hewo/`；只有在下游仓库中
才把该路径替换为 `src/<agent_name>/`。

用户已明确授权开始实现 Agent 产品行为。请执行 Phase 1: Implement product
behavior。先确认 Agent 名称、目标用户和产品边界，再把 Phase 0 中带有
`TODO: replace during implementation` 的占位内容逐项替换为经过用户确认的
runtime 资源。

在写任何代码之前，先为每一条产品需求提交一次 **component choice + rationale**，
按 `.agents/knowledge/pi-runtime-component-contract.md` 的决策树自上而下选择：

1. 声明式资源（identity / knowledge / skill / prompt template / theme）；
2. pi 原生配置（工具白名单、session 模式、project trust、context 策略）；
3. 很薄的 TypeScript extension（typed tool、生命周期 hook、进程内状态）；
4. 叶子脚本（无状态适配器，由 skill/extension 调用）；
5. 外部 CLI/服务。

只有写下"上一层为什么表达不了这个需求"之后才能下降一层。"tools" 不默认等于一个
Python 项目：直接跳到脚本需要在 issue 中记录具体的 backend 能力缺口（哪个 pi
primitive 本应覆盖它、为什么没有）。"更快写完" 不是缺口。

脚本作为叶子适配器时必须满足：明确的输入输出契约、幂等性与错误码、超时与取消、
输出截断、无状态、secret safety，以及一条不需要凭据就能独立跑通的验证命令。
脚本不得承担 agent loop、session 管理、模型调用、审批循环、sub-agent 编排、
产品身份、长期状态或跨组件主编排。重新运行 definition validation、
consistency audit，并用真实 provider-backed Docker E2E 观察产品行为；只有这些
`agent-behavior` 证据完成后，才能声称 Agent 产品实现完成。不要修改已有 backend
执行循环、model client、session、approval 或 tool loop，除非用户另行授权且
issue 记录了 backend 能力缺口。Phase 1 完成后报告产品决策、行为证据和仍待
授权的 Phase 2 release 工作。
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
   `runtime/package.json` 或 Agent 产品 release，除非项目需求后来明确改变。
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

它会从当前 worktree 构建并检查 clean image。若镜像已由
`./scripts/build-agent-image.sh` 从冻结快照构建，用
`--skip-build --image <image-id>` 复用；因为 tag 是内容寻址的，"这个镜像是否
对应这份源码"不再需要人去记住。`--skip-build` 现在会断言镜像确实存在，缺失即
报错而不是静默继续。通过后仍需用实际 provider credentials 运行真实 Docker
E2E，才能声称 Agent 行为验证完成。

不要把 template 的 `.agents/` 整目录复制到下游项目。Issue #1/HeWo 的历史
证据、template release 工作流和 benchmark 记录只属于本仓库；下游项目应建立
自己的 development memory、knowledge、workflow 和验收证据，只按需保留已经
审查过的通用 skill。

## 产品外评估闭环

开发产品 Agent 时，必须形成项目内、产品外的 loop：定义或修改 runtime 后，
由开发 coding agent 在 `.agents/` 与 `scripts/` 中完成验证、证据收集和失败
回流，而不是把评估逻辑写进 `src/hewo/runtime/`。这个 loop 的权威入口是
`.agents/workflows/agent-development.md`；可执行辅助入口是
`scripts/run-agent-loop.sh`（或下游改名后的等价脚本）。

Loop 的阶段是：

1. 确认身份和边界：开发 coding agent 读取 `AGENTS.md` / `.agents/`，产品
   Agent 只读取 runtime。
2. 运行结构验证和 repository-scope audit。
3. 从冻结快照构建镜像（内容寻址 tag `<agent>:def-<digest>`），再运行
   clean-container infrastructure check。
4. 通过明确 credential-source 注入真实 backend/provider/model，执行
   provider-backed E2E 或 benchmark stage。
5. 保存 artifact、trajectory 和 scrubbed trajectory，只记录 secret-free summary。
6. 把失败分类为 definition、infrastructure、provider、benchmark/verifier 或
   product-behavior 问题，再回到 runtime 定义或开发基础设施中修复。

产品 Agent 的长程任务验证通常不应阻塞前台终端。对耗时验证，用 loop runner 的
后台登记模式：

```bash
./scripts/run-agent-loop.sh --background --provider openai --model gpt-5.5 \
  --pi-auth-file "$HOME/.pi/agent/auth.json" "<task>"
./scripts/run-agent-loop.sh --list-runs
./scripts/run-agent-loop.sh --run-status <run_id>
./scripts/run-agent-loop.sh --clean-run <run_id>      # 结果消费后清除
./scripts/run-agent-loop.sh --gc --older-than 7      # 回收无人引用的 def- 镜像
```

提交的那一刻，整个工作树会被冻结成该 run 私有的快照，此后 preflight、镜像
构建、benchmark 和判定 pass/fail 的 verifier 全部对着快照执行。所以提交返回
之后就可以继续修改 `src/<agent>/`：改动不会影响在飞的 run，也不会污染它的
证据。`--run-status` 会显示每个 run 的 `definition_revision` 与 `image`，
即在测哪一个版本。

完整 preflight（backend、credential matrix、task、workspace）在前台执行，
无效调用当场拒绝，不会变成一个需要事后查询的后台任务。登记内容只包含 run id、
stage、backend/provider/model、credential-source flag、状态、pid、artifact 路径
和 scrubbed evidence 路径，不得包含 key、auth store 内容、raw provider output
或个人数据。登记目录默认在 `$XDG_STATE_HOME/agent-loop`（仓库之外，避免误提交）。
进程消失但没有记录 exit code 的 run 会被报告为 `abandoned`，而不是一直停在
`running`；`--clean-run all` 只清理已结束的 run。

Benchmark 只是 loop 的一个 stage。它衡量 capability/regression，不定义产品
行为；不能为了通过 verifier 在 runtime 中加入 benchmark-specific hack。

### 冷启动：一开始 loop 不是自动的

上面的 loop 描述的是稳态。产品不是从稳态开始的。刚开始时通常有两件事同时是
错的：产品 Agent 效果很差——这一点 coding agent 看得见；以及 coding agent
自己对问题定义和产品定位的理解不到位——这一点它看不见，于是会把自己的误解当成
产品的属性，然后**自信地朝错误方向优化**。

所以状态机里进入 `CONTRACT_DESIGNED` 的唯一路径是 `COLD_START_HUMAN_IN_LOOP`：
在你确认问题定义和产品定位之前，loop 不交给 coding agent。冷启动期间，人是
反馈函数，而且同时在反馈两件事——产品的输出，以及 coding agent 对问题的建模。

作为开发者，你在冷启动期应该要求 coding agent：给你看真实的、未经转述的运行
输出；把它对问题、目标用户、什么算好答案、什么明确不在范围内的理解写下来给你
纠正；问定位问题而不只是任务问题；以及在候选连续被拒时停下来回到你这里，而不是
继续调参。连续失败更可能说明问题被读错了（`UNDERSTANDING_MISMATCH`），而不是
候选不够好。

### 先功能基线，后性能优化

"优化"不是 loop 的第一步。两个阶段必须分开，且顺序不可颠倒：

1. **功能完备基线**：第一版可以质量一般，但必须是可工作的：输入输出契约成立、
   必要 artifact 存在、功能 verifier 能稳定判断 pass/fail。如果这些条件还不
   成立，状态是 `FUNCTIONAL_BASELINE_MISSING`，这不是"低性能版本"，而是产品
   功能或契约尚未完成。
2. **性能优化**：只有在基线成立并被测量之后，才能谈改进。声称"更好"之前必须
   先有 contract、primary metric、固定运行条件、重复次数、阈值和停止条件。

以论文写作 Agent 为例："能产出包含全部必需章节的论文"是功能契约；"论文更好"
是性能声明，需要指标、基线、重复运行和阈值才能成立。

设计入口是开发侧 skill `.agents/skills/agent-evaluation-loop-design/`：

```bash
python3 .agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py \
  --agent hewo --repo-root . --output-dir . --readme README.md
python3 .agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py \
  --agent hewo --repo-root . --output-dir . --readme README.md --strict
```

它同时生成 `agent-architecture.mmd`（产品 Agent 由什么组成）和
`agent-optimization-loop.mmd`（产品 Agent 如何被迭代），并把两者同步到
README 的 generated blocks；`.mmd` 是唯一真源，README 不保存第二份。

**评估条件身份（condition identity）**：被测对象的 revision 与评估条件必须
分开。`subject.definition_revision` 在 current best 和 candidate 之间不同，
这是比较的前提，不是 baseline 失效的原因；只有 canonical condition manifest
（benchmark、verifier、metric policy、backend/provider/model、runtime、image
digest、请求/采样/重试/超时参数、locale/timezone/seed、重复次数与聚合方式）
发生变化，才使 baseline 失效，必须在新条件下重测 current best。任何无法写入
manifest 的 run-affecting 输入都使比较 blocked，而不是默认通过。

**失败必须分类**，不能都折叠成"Agent 变差"或"Agent 变好"：

| 状态 | 含义 | 是否更新 current best |
| --- | --- | --- |
| `DESIGN_INCOMPLETE` | contract 缺失或 schema 无效 | 否 |
| `FUNCTIONAL_BASELINE_MISSING` | 无有效、已 promotion、功能通过的基线 | 否 |
| `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE` | 只有 smoke 契约 | 否 |
| `ENVIRONMENT_BLOCKED` | credential/provider/基础设施失败 | 否 |
| `EVALUATION_BLOCKED` | benchmark/verifier/evidence 失败 | 否 |
| `BASELINE_INVALIDATED` | 评估条件已改变 | 否 |
| `CANDIDATE_REJECTED` | 功能失败、未达阈值或次要指标回归 | 否 |
| `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE` | 固定 benchmark 上的接受建议 | 否，需单独 promotion gate |
| `GENERALIZATION_REQUIRED` | 缺独立 holdout/canary 或人工领域评审 | 否 |

**禁止的自欺行为**：在同一个 candidate 变更里放宽 verifier、修改 benchmark、
改动 metric policy 或阈值；用一次 provider response 声称改进；跨 provider/
model/runtime 直接比较结果；把 provider 或基础设施失败写成产品回归。修改
benchmark、verifier、metric policy 或 contract schema 是独立的设计变更，需要
人工评审，并使旧 baseline 失效。

**当前 hewo 的定位**：`src/hewo/development/evaluation-contract.json` 是
`infrastructure-smoke-only`，没有声明任何 primary metric。因此 hewo 的状态
只能是 `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`；不要为了"进入优化"给它虚构
质量指标。

`scripts/run-agent-loop.sh` 是 stage runner，`compare-evaluations.py` 是薄
比较协议；两者都不是已实现的自动性能优化器，不要这样描述它们。

## 1. 设计原则：reuse-first

开发 Agent 的主要工作是设计和组合：

- prompt 和 Identity
- skills
- memory policy
- knowledge
- workflows
- tools

成熟的 coding-agent（本产品用 pi）负责执行循环、模型适配、工具调用、审批和
终端交互。本仓库只实现必要的 scaffold、runtime context 注入和 provider
wiring，不重复实现 coding-agent runtime。

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

## 2. Scaffold 合约（Phase 1 产品实现后）

在本仓库中，下面的通用合约实际对应 `hewo`：产品源码只能位于
`src/hewo/`，产品 runtime 只能位于 `src/hewo/runtime/`。`src/<agent_name>/`
仅在下游 scaffold 文档中作为变量使用。

一个可安装产品 Agent 的最小结构是（本仓库把 `<agent_name>` 固定为 `hewo`）：

```text
src/hewo/
├── AGENTS.md                 # 仅开发 coding agent 使用，不发布
├── agent.yaml
└── runtime/
    ├── identity.md
    ├── memory-policy.md
    ├── package.json           # runtime 资源清单，唯一 source of truth
    ├── knowledge/
    ├── skills/
    ├── workflows/
    └── tools/                  # 可选，独立 uv tool project
```

下游仓库将上图的 `hewo` 替换为自己的 `<agent_name>`；本仓库不要新增第二个
产品目录。

`distribution/launcher` 读 `runtime/package.json`，把每类资源交给 pi 自己的
loader（`--skill`、`--prompt-template`、`--theme`、`--extension`、`--tools`），
只有 identity/memory-policy/knowledge/workflows 走 `--append-system-prompt`，
因为 pi 没有对应原语。若存在 `runtime/tools/pyproject.toml`，安装器会用 uv
创建独立的 `<prefix>/lib/<agent>/environment/` 并安装其中的 tools；launcher
会把该环境的 `bin/` 放进 PATH。runtime 中不得存在非 pi 的 backend 配置文件，
`validate-definition.sh` 会拒绝。

不要在 `src/hewo/runtime/` 中放置（下游适配后对应其 `src/<agent_name>/runtime/`）：

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

当前 Docker image 只安装一个 backend：

```text
pi            @earendil-works/pi-coding-agent
```

`--backend`（或 `AGENT_BACKEND`）只接受 `pi`（别名 `pi-coding-agent`），其他
取值一律报错退出，不存在回退默认值：

```bash
hewo --backend pi --provider openai --model gpt-5.5 ...
```

`--provider` 选择 pi 的 provider。

### Provider/model

scaffold 不应写死 provider。provider/model 在运行时传入：

```bash
LLM_PROVIDER=openai LLM_MODEL=gpt-5.5 \
  ./docker/run-hewo-e2e.sh --agent hewo \
  --pi-auth-file "$HOME/.pi/agent/auth.json" \
  "Reply with exactly: hi"
```

API key 环境变量按 provider ID 转换为 `<PROVIDER>_API_KEY`；Docker helper
只转发当前 backend 需要的 provider 环境变量，并拒绝不匹配的 credentials
参数。

工具项目应保持最小、无凭据、可重复。例如 hewo 的
`runtime/tools/pyproject.toml` 只安装 `hewo-tool`，用于验证 Agent 是否真的
能调用自己的产品环境；不要让它依赖 template 根目录的开发 `.venv`。

`AGENT_BACKENDS` 只接受 `pi`，其他取值被 installer 和 build-release 拒绝
（exit 2），所以正常情况下不要设置它。用户没有 pi 时 release 安装会自动装；
`SKIP_RUNTIME_INSTALL=1` 可跳过。

## 4. 构建、安装和发布

### 源码安装检查

```bash
AGENT_NAME=hewo PREFIX=/tmp/hewo-install \
  ./distribution/install.sh
```

开发构建会排除 `AGENTS.md`、node_modules、package metadata 和 credentials；
若 scaffold 声明 tools，构建阶段会用 uv 生成其独立环境。

### Docker 构建

镜像由冻结快照构建，tag 是内容寻址的，所以同一份源码永远对应同一个 tag：

```bash
./scripts/freeze-agent-run.sh --into /tmp/hewo-snapshot
./scripts/build-agent-image.sh --context /tmp/hewo-snapshot   # 已存在则不重建
```

需要手工构建当前工作树时（不产出证据）仍可以直接用 Docker：

```bash
docker build --build-arg AGENT_NAME=hewo \
  -t hewo:dev -f docker/Dockerfile .
```

Docker 使用 Node 22，只安装 pi。验证版本时绕过产品 entrypoint：

```bash
docker run --rm --entrypoint /bin/bash hewo:dev -lc 'pi --version'
```

### Release

产品 agent 会快速迭代，每次被接受的产品行为改动后都要发布新版本（git tag +
GitHub release），不要把未发布的改动一直堆积。`scripts/publish-release.sh`
一步完成：定义校验 → 用正确的 `RELEASE_URL` 构建 archive → 打 tag → 推 tag →
创建 GitHub release（archive 作为 asset 附带）：

```bash
./scripts/publish-release.sh hewo 0.2.0
```

脚本内部先跑 `validate-definition.sh`，再用
`https://github.com/<owner>/<repo>/releases/download/v<version>/<name>-<version>.tar.gz`
作为 `RELEASE_URL` 构建 `release/hewo-<version>.tar.gz`，然后执行
`git tag v<version>`、`git push origin v<version>`、`gh release create`。
版本号取 `git tag -l` 里最新值并按改动语义递增（patch/minor）。发布前仍需
完成真实 provider-backed Docker E2E 与一致性审计；`publish-release.sh` 只是
最后一步的机械执行，不替代行为验证。可用 `--dry-run` 预览将执行的命令。

检查 release payload 不含 `AGENTS.md`、auth store、package metadata 或开发
目录。发布归档只包含 runtime definition、launcher 和 installer。发布后，
用户可以只下载 release installer，通过 `RELEASE_URL` 获取 archive，不需要
clone template。

## 5. 真实 Docker E2E 验证

镜像成功构建或 CLI 成功启动不等于 Agent E2E 通过。必须注入实际 provider
runtime，并观察容器中的真实模型响应。

`docker/run-hewo-e2e.sh` 现在默认 fail-closed：不带凭据来源会直接报错退出并
列出注入选项；只有 `--allow-unauthenticated` 才允许无凭据的 infra-only 冒烟
（build/`--help`）。可注入 flag 与宿主机凭据路径速查见
`.agents/knowledge/provider-e2e.md`。

### 最小请求

```bash
./docker/run-hewo-e2e.sh \
  --agent hewo \
  --provider openai \
  --model gpt-5.5 \
  --pi-auth-file "$HOME/.pi/agent/auth.json" \
  "Reply with exactly: hi"
```

helper 只接受 `--pi-auth-file`、`--api-key-env`、`--api-key-stdin` 和
`--bundle` 作为凭据来源，其他 flag 以 unknown option 退出 2。credentials 只读
挂载，不能复制进镜像。

### 完整 infrastructure smoke

```bash
PI_AUTH_FILE="$HOME/.pi/agent/auth.json" \
LLM_PROVIDER=openai \
LLM_MODEL=gpt-5.5 \
BENCHMARK_RUN_DIR=/tmp/hewo-evidence \
./scripts/run-benchmark.sh hewo
```

`run-benchmark.sh` 只读 `PI_AUTH_FILE`、`PI_MODELS_FILE` 和
`BENCHMARK_API_KEY_ENV` 作为凭据来源。

成功的 verifier 必须确认 Agent 在独立 workspace 中：

1. 加载 `runtime-smoke` skill；
2. 读取 knowledge 和 workflow；
3. 写入 `artifacts/hewo-smoke.md`；
4. 重新读取 artifact；
5. 验证 `Product runtime`、`Workspace access`、`Skill loaded`；
6. 验证 `HEWO_KNOWLEDGE_OK`、`HEWO_TOOL_OK` 和 `HEWO_WORKFLOW_OK`。

trajectory 和 benchmark 输出只能放在 disposable 目录，提交前必须 scrub，
不能包含 raw provider output 或 secrets。

### provider/model 验证记录

以下是历史观测，不是当前契约。收敛到 pi-only 之前的记录按当时的 backend
保留（不改写既有证据），但只有 pi 行仍适用于今天的产品路径：

- 当前后端（pi）：`openai-codex/gpt-5.5`（通过只读 pi auth store）
- 收敛前的历史记录（backend 已下线，仅作存档）：`openai/gpt-5.5`、
  `opencode-go/gpt-5.6-luna`、`opencode-go/glm-5.3`、`opencode-go/qwen3.7-plus`、
  `opencode-go/kimi-k2.7-code`、`opencode-go/grok-4.6`、`gpt-5.5`、
  `sonnet`（通过授权的 Apex-compatible Anthropic endpoint）

新增记录时必须写明 backend/provider/model 与 credential-source flag。

provider 通常还提供列表里的其他模型，但不能因为模型出现在
`pi --list-models` 中就声称测试通过（该命令是 auth-filtered 的可达性探针，
不是目录）。每个下游 Agent 应记录实际使用的 provider、model、CLI version、
runtime revision 和 artifact 路径。

当前 Ubuntu 宿主机上，容器内的完整工具任务可能受到 nested bubblewrap
user namespace 限制；简单请求通过不代表该宿主机的工具 sandbox 一定可用。
不要用默认关闭安全隔离的方式掩盖这个限制。

## 6. 验证清单

提交前至少运行：

```bash
./scripts/validate-definition.sh hewo
bash -n distribution/launcher distribution/install.sh \
  distribution/container-entrypoint.sh docker/run-hewo-e2e.sh \
  scripts/build-release.sh scripts/run-benchmark.sh scripts/run-agent-loop.sh \
  scripts/freeze-agent-run.sh scripts/build-agent-image.sh
git diff --check
```

变更 backend、Docker 或 release 时，还应：

1. 构建 Docker image；
2. 检查 pi 版本；
3. 运行真实 provider-backed 最小 E2E；
4. 运行至少一个完整 infrastructure smoke；
5. 扫描镜像和 release payload 中的开发指令与 credentials；
6. 检查 CI 的 definition 和 image checks。

如果 runtime 声明了 tools，还应检查：

```bash
docker run --rm --entrypoint bash hewo:dev -c \
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
Backend: pi (only)
Validated provider/models: <实际 E2E 结果>
CLI command: <agent_name>
```

同时保留本文的三层边界、reuse-first 原则、凭据安全规则和真实 Docker E2E
要求。只替换自己的 scaffold、默认模型和实际验证证据，不复制新的 runtime
实现。
