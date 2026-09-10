# 开发 coding agent 内部流程

> **Role of this document**
> - **Audience:** 维护 template 或适配下游仓库的 development coding agent，不是产品 agent。
> - **Authority:** informative；根 `AGENTS.md` 和 gate scripts 优先。
> - **Tone:** 面向开发 coding agent 的操作步骤与参考。
> - **Language:** 中文，保留英文标识和命令。
> - **Contains:** 从根 `DEV.md` / `README.md` 迁入的初始化 prompts、组件选择、内部审计、评估闭环、scaffold 契约与图表维护。
> - **Excludes:** 产品行为见 `src/hewo/runtime/`；human 操作指南见 [DEV.md](../../DEV.md)，产品使用见 [USER.md](../../USER.md)。
> - **Provenance:** 本次文档职责迁移；原内容来自根 DEV/README，命令接口对照仓库脚本。所有 shell 示例从仓库根目录执行；Markdown 链接相对本文件。

## 身份与 skill 路由

你是维护仓库的开发 coding agent，不是被开发的 hewo。当前产品源码只能位于 `src/hewo/`，用户载荷仅为 `src/hewo/runtime/`，排除所有 `AGENTS.md`。`src/<agent_name>/` 只用于下游占位，不允许在本仓库新增第二个产品目录。

`AGENTS.md`、`.agents/`、开发证据和评估脚本不是产品上下文，也不能随产品发布。不要因为读到 runtime 的身份/skill 而扮演产品 agent。human 直接阅读的少量操作指南留根目录；仅供开发 coding agent 使用的信息和流程维护在 `.agents/`。

按任务加载：

- 新建、同步、迁移下游：[template-agent-development](../skills/template-agent-development/SKILL.md)，渐进式选择对应 sub-skill。
- 修改 `src/hewo/` 或准备产品 release：[agent-definition-validation](../skills/agent-definition-validation/SKILL.md)。
- 发布 template：[template-release-readiness](../skills/template-release-readiness/SKILL.md)。
- 一致性检查：[agent-consistency-audit](../skills/agent-consistency-audit/SKILL.md)。
- installer、package 加载、Docker、backend、工具环境或开始编排前：[agent-infrastructure-health](../skills/agent-infrastructure-health/SKILL.md)。

同步前阅读 [content registry](../template-content-registry.json) 与 [sync-template](../skills/template-agent-development/references/sync-template.md)。登记表覆盖整个仓库，不仅是 `.agents/`；未归类的 Git 跟踪文件会使检查失败。不要复制 template 仓库或 `.agents/` 整目录；Issue #1/HeWo 历史、template release、benchmark 证据和 registry 本身不属于下游。

```bash
python3 .agents/scripts/check-template-registry.py
```

## 下游初始化 Prompt（Phase 0）

以下是交给下游开发 coding agent 的通用 prompt，不是产品 runtime；仅在下游将 `hewo` 路径适配为自己的 Agent 名称。

```text
你是负责维护下游仓库的开发 coding agent，不是将要交付的产品 agent。
产品身份和用户可见行为只属于 src/<agent_name>/runtime/；本 prompt、AGENTS.md、
.agents/ 和验证脚本不能复制到产品 runtime 或当作产品行为。

以 https://github.com/a-green-hand-jack/coding-agent-template.git 为 template
上游，执行 Phase 0: Initialize，建立最小可运行、可供后续实现的 Agent dev scaffold。
变量：Agent 名称 <agent_name>；backend pi（只支持 pi）；provider/model <provider/model>。

初始化只创建基础目录、src/<agent_name>/agent.yaml、最小 runtime 配置、下游自己的
.agents/ 中性占位符，以及必要的 Docker、distribution、pi package 加载、脚本和
工具环境配置。可从 src/hewo/ 派生 scaffold，但只保留最小 HeWo smoke 资源作为
临时基础设施探针；不得继承 HeWo 名称、身份、领域语义、历史证据或产品假设，
不得把 smoke 扩展为产品功能。临时内容均标记 TODO: replace during implementation。
初始化不要求真实产品 identity 或产品专属 knowledge。

禁止编写产品 identity/声明、领域 knowledge、正式 skills/业务 workflows、领域
工具和业务执行逻辑、产品 benchmark 或验收证据；禁止修改 execution/model client/
session/approval/tool loop；不能生成 release-ready 行为或称 provider 响应为已实现产品。

执行顺序：
1. 阅读上游 AGENTS.md、DEV.md、.agents/knowledge/development-procedures.md、
   .agents/skills/template-agent-development/SKILL.md 和 registry；先运行
   python3 .agents/scripts/check-template-registry.py。
2. 使用 registry 和 sync-template sub-skill 选择性同步，不复制整个 template 或
   .agents/，不复制任何 template AGENTS.md、Issue/HeWo 历史、benchmark/release
   证据、registry 或 provider 凭据。
3. 建立 src/<agent_name>/ 最小 scaffold；派生 src/hewo/ 时排除 AGENTS.md，清理
   HeWo identity、产品语义和非必要 smoke。runtime 只能是带 TODO 的通用占位内容。
4. 建立自己的 .agents/knowledge、memory、workflows，只以中性 PLACEHOLDER.md
   为起点；不要在其中写入应发布的产品设计，为下游目录重写 scoped AGENTS.md。
5. 只按需选择并适配开发 skill；保持 scaffold/backend/provider 独立，不重复实现
   backend 的执行循环、model client、审批或 tool loop。适配基础设施但不加入业务逻辑。
6. 运行结构与基础设施检查：
   ./.agents/scripts/validate-definition.sh <agent_name>
   python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent <agent_name> --strict
   python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py --agent <agent_name>
   区分 structure（文件/配置/目录）、infrastructure（Docker/CLI/工具环境/provider
   注入/响应）和 agent-behavior（真实产品 identity/skill/workflow/工具观察）。
   Phase 0 最多产生 structure 和 infrastructure；provider 响应标为
   infrastructure evidence、not Agent behavior evidence。
7. 对每个目标 backend/provider 运行真实 provider-backed Docker E2E，凭据仅运行时
   注入。检查 release 边界排除 AGENTS.md、.agents/、development、auth store 和
   credentials，但不要生成产品 release。

报告创建文件、复用 registry 条目、排除的 template-specific 内容、保留 HeWo smoke
及其仅基础设施状态、backend/provider E2E 与证据标签、尚未实现内容及下一阶段待授权事项。
完成初始化检查和基础设施 E2E 后立即停止。等待用户明确授权“开始实现 Agent 产品行为”，
不得自动进入 Phase 1，不得把初始化报告当作产品验收。
```

## 实现 Prompt（Phase 1）

只有用户明确授权后，才交给开发 coding agent：

```text
你是开发 coding agent，正在实现产品而不是扮演它。当前 template 的产品是 hewo，
产品改动只在 src/hewo/；仅下游仓库才替换为 src/<agent_name>/。

用户已授权 Phase 1: Implement product behavior。确认 Agent 名称、目标用户和产品
边界，把 Phase 0 的 TODO: replace during implementation 逐项替换为用户确认的 runtime。

写代码前，对每条需求提交 component choice + rationale，按
.agents/knowledge/pi-runtime-component-contract.md 从上到下选择：
1. 声明式 identity / knowledge / skill / prompt template / theme；
2. pi 原生配置：工具白名单、session、project trust、context 策略；
3. 薄 TypeScript extension：typed tool、生命周期 hook、进程内状态；
4. 无状态叶子脚本：由 skill/extension 调用；
5. 外部 CLI/服务。
只有说明上一层为何不能表达需求后才能下降。“tools”不默认等于 Python 项目；
跳到脚本须在 issue 记录哪个 pi primitive 不足，“更快写完”不是能力缺口。

叶子脚本必须有输入输出契约、幂等性/错误码、超时/取消、输出截断、无状态、secret
safety 和无凭据可独立执行的验证命令。脚本不得承担 agent loop、session、模型调用、
审批循环、sub-agent 编排、产品身份、长期状态或跨组件主编排。

重新运行 definition validation、consistency audit，并用真实 provider-backed Docker
E2E 观察产品行为；只有 agent-behavior 证据完成才可声称实现完成。除非用户另行授权且
issue 记录 backend 缺口，不修改已有 backend execution/model client/session/approval/
tool loop。报告产品决策、行为证据和仍待授权的 Phase 2 release。
```

组件决策的权威参考：[pi runtime component contract](pi-runtime-component-contract.md)。

## 非 Agent 项目复用 Prompt

```text
你正在维护不发布 coding Agent 的项目。将
https://github.com/a-green-hand-jack/coding-agent-template.git 作为基础设施和开发
流程参考，不要把当前项目伪装成 Agent dev repo。
项目目的：<project_purpose>
复用能力：<docker|isolated-uv-tools|backend-clis|development-skills>

先检查并保留当前未提交改动，然后：
1. 阅读 template AGENTS.md、DEV.md、.agents/knowledge/development-procedures.md、
   template-agent-development 和 agent-infrastructure-health skills，以及 registry；
   在 template checkout 运行 python3 .agents/scripts/check-template-registry.py。
2. 仅选择 registry 的 selective Docker/distribution/scripts/package/tool 配置与
   skills，逐项说明理由。不复制整个仓库/.agents/、src/hewo/、任何 AGENTS.md、
   HeWo/Issue 历史、benchmark/release 证据、registry 或凭据。
3. 重写自己的根和 scoped AGENTS.md，建立 .agents/knowledge、memory、workflows；
   中性 PLACEHOLDER.md 可作为起点，但须替换为项目内容。
4. 未明确改变需求前，不创建 agent.yaml、Agent identity、runtime/package.json 或
   Agent release。不运行或声称通过仅适用于 Agent scaffold 的 definition validation
   或 provider-backed Agent E2E；定义当前项目自己的 smoke/acceptance contract。
5. 复用 Docker/backend/uv 时移除 HeWo 默认值和产品命令假设，区分开发 CLI 与项目
   runtime 依赖；工具环境独立、最小、无凭据，凭据只在运行时注入。
6. reuse-first，不重写已有 model client/session/approval/tool loop，只加确需的薄
   适配层并在 issue 记录 backend 能力缺口。
7. 执行适配后的 shell/Python/config 检查、Docker smoke 和工具环境检查；采用
   infrastructure skill 时先适配 Agent 名称、必需二进制和验收命令。检查镜像、
   发布物和 Git 无 AGENTS.md、.agents/ 开发历史、auth store、API keys 或个人数据。

报告 registry 选择、排除内容、复用基础设施、项目自己的验证契约，以及需要人工决定
的 backend/provider 或安全边界。不要强行改造成 coding Agent。
```

## Scaffold 与 reuse-first

设计和组合 prompt/identity、skills、memory policy、knowledge、workflows、tools；pi 提供执行循环、模型适配、工具、审批和终端基础。三层保持独立：

```text
Agent scaffold -> coding-agent backend -> LLM provider/model
```

增加 CLI/model client/session manager/tool loop 前先确认 backend 缺口，在 issue 记录理由；优先扩展 runtime 定义或薄 adapter。最小产品结构包含 `agent.yaml`、runtime 的 `identity.md`、`memory-policy.md`、`package.json`（资源 manifest 唯一真源）、knowledge、skills、workflows 和可选独立 uv tools。scoped `AGENTS.md` 仅开发使用，不发布。

用户显式用 pi `-e <prefix>/lib/<agent>/runtime-package` 加载，完整隔离参数见 [USER.md](../../USER.md)。不提供产品 wrapper CLI 或 scaffold registry。extension 消费 identity、memory policy、knowledge、workflows 和工具白名单。`runtime/tools/pyproject.toml` 存在时 installer 用 uv 安装独立环境；用户设置工具 PATH，容器使用 `/opt/install/lib/<agent>/environment/bin`。工具不得依赖 template `.venv`；hewo 的 `hewo-tool` 用于验证实际产品工具路径。

仅在独立下游仓库派生 scaffold（随后必须清理产品身份和适配）：

```bash
mkdir -p src/my-agent
tar -C src/hewo --exclude=AGENTS.md -cf - . | tar -C src/my-agent -xf -
./.agents/scripts/validate-definition.sh my-agent
```

安装以 `AGENT_NAME=my-agent` 选择 scaffold。runtime 禁放 keys/auth stores/tokens/`.env`、原始 provider sessions、个人数据、开发指令或 benchmark-specific hacks。

Docker 只安装 `@earendil-works/pi-coding-agent`，使用 Node 22。`--backend` / `AGENT_BACKEND` 仅接受 `pi`（别名 `pi-coding-agent`），其他值报错。installer 只安装 runtime 与工具，不安装 backend，也不配置 provider/model/credentials。provider/model 运行时注入；helper 接受 `LLM_PROVIDER` / `LLM_MODEL`，但公开操作示例优先使用显式 flags。

## 内部构建与审计

冻结和内容寻址构建：为命令中的路径选择已批准、可重建的任务目录，不使用持久开发 worktree 作为临时产物。

```bash
./.agents/scripts/freeze-agent-run.sh --into /path/to/task/hewo-snapshot
./.agents/scripts/build-agent-image.sh --context /path/to/task/hewo-snapshot
```

tag 为 `<agent>:def-<digest>`，已存在则复用；验证健康检查时可用 `--skip-build --image <image-id>` 复用冻结构建。缺失镜像会明确失败，不静默跳过。

手工诊断构建不产出产品行为证据：

```bash
docker build --build-arg AGENT_NAME=hewo -t hewo:dev -f docker/Dockerfile .
docker run --rm --entrypoint /bin/bash hewo:dev -lc 'pi --version'
```

构建排除 AGENTS.md、node_modules 和 credentials，保留 manifest；声明 tools 时用 uv 生成独立环境。最终多阶段镜像仅含安装后产品、工具和 pi，不含 template 开发资源、benchmarks 或 `.agents/`。

模板发布前加载 release-readiness skill 并运行：

```bash
python3 .agents/scripts/check-template-registry.py
python3 .agents/skills/template-release-readiness/scripts/audit_template_release.py --agent hewo
```

下游创建/迁移/同步之后，在下游仓库运行自己的名称（不要用 hewo）；有归档时加 `--release`：

```bash
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent <agent_name> --strict
python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py --agent <agent_name>
```

一致性审计扫描 memory、skills、tools、runtime、文档和 payload；WARN 和语义矛盾仍需判断。基础设施检查从当前 worktree 构建 clean image。这些不是行为证据；之后仍需通过 [Docker helper](../../docker/run-hewo-e2e.sh) 注入真实 provider，并检查回复/artifact。发布操作留在 [DEV.md](../../DEV.md#5-发布)。

## 产品外评估闭环

权威入口：[agent-development workflow](../workflows/agent-development.md)。实现位于 `.agents/`，不能复制进 runtime。runner `./.agents/scripts/run-agent-loop.sh` 是 stage runner；`compare-evaluations.py` 是薄比较协议，都不是自动性能优化器。

阶段：身份/边界确认 → definition validation 和 repository-scope audit → 冻结快照内容寻址构建 → clean-container health → 显式 credential-source 的真实 E2E/benchmark → artifacts/trajectory/scrubbed trajectory → 分类失败并回流修复。

后台提交、状态、日志、结果消费和镜像回收见 [DEV.md](../../DEV.md#3-长任务后台运行状态与日志)。提交时冻结整个工作树，preflight、构建、benchmark、verifier 都针对该 run 快照；后续修改不污染证据。前台 preflight 验证 backend、credential matrix、task 和 workspace，拒绝无效调用后才可能 detach。登记只含 run id、stage、backend/provider/model、credential-source flag、状态、pid 和路径，不含 key/auth store/raw output/个人数据。

### 冷启动与功能基线

冷启动时产品和 coding agent 对问题的理解可能同时不完善。进入 `CONTRACT_DESIGNED` 必须先经过 `COLD_START_HUMAN_IN_LOOP`，不能擅自定义指标进入优化。向 human 展示未经转述的真实输出；写明问题、目标用户、好答案和明确不做什么，让 human 纠正；问定位而非只问任务。候选连续失败时回到 `UNDERSTANDING_MISMATCH`，不要自信地对错误目标继续调参。

human 明确确认问题、定位和功能完整基线后才交接稳态闭环。功能基线要求输入输出契约、必需 artifacts 和可稳定判定 pass/fail 的 verifier；第一版质量可以一般，但缺失这些是 `FUNCTIONAL_BASELINE_MISSING`，不是低分。以论文 Agent 为例，完整章节是功能契约，“论文更好”则需性能指标、基线、重复和阈值。

性能声明前加载 [agent-evaluation-loop-design](../skills/agent-evaluation-loop-design/SKILL.md)，先有 contract、primary metric、固定条件、重复次数、阈值和停止条件。

`subject.definition_revision` 在 current best 与 candidate 之间不同是比较前提，不使 baseline 失效。只有 canonical condition manifest 改变才失效：benchmark、verifier、metric policy、backend/provider/model、runtime、image digest、请求/采样/重试/超时、locale/timezone/seed、重复与聚合。无法记录的 run-affecting 输入使比较 blocked，不能默认通过；条件改变后重测 current best。

| 状态 | 含义 | 更新 current best |
| --- | --- | --- |
| `DESIGN_INCOMPLETE` | contract 缺失/schema 无效 | 否 |
| `FUNCTIONAL_BASELINE_MISSING` | 无有效、已 promotion、功能通过的基线 | 否 |
| `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE` | 只有 smoke 契约 | 否 |
| `ENVIRONMENT_BLOCKED` | credential/provider/基础设施失败 | 否 |
| `EVALUATION_BLOCKED` | benchmark/verifier/evidence 失败 | 否 |
| `BASELINE_INVALIDATED` | 条件改变，须重测 | 否 |
| `CANDIDATE_REJECTED` | 功能失败、未达阈值或次指标回归 | 否 |
| `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE` | 固定 benchmark 接受建议 | 否，需独立 promotion gate |
| `GENERALIZATION_REQUIRED` | 缺独立 holdout/canary 或人工领域评审 | 否 |

禁止在同一 candidate 变更中放宽 verifier、benchmark、metric policy 或阈值；这些与 contract schema 修改是独立设计变更，需人工评审并使旧 baseline 失效。不能用一次 provider response 声称改进，跨 provider/model/runtime 直接比较，或把环境失败说成产品回归。benchmark 衡量 capability/regression，不定义产品行为；不能添加 verifier 专用 runtime hack。

当前 `src/hewo/development/evaluation-contract.json` 为 `infrastructure-smoke-only`，未声明 primary metric，只能标为 `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`，不虚构质量指标。

### 图表生成器契约

必须保留根 [agent-architecture.mmd](../../agent-architecture.mmd) 和 [agent-optimization-loop.mmd](../../agent-optimization-loop.mmd)：前者说明产品组成，后者是带 guards 的迭代状态机而非 checklist。`.mmd` 是唯一真源；README 的 Mermaid blocks 是生成副本，不手改。

```bash
python3 .agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py \
  --agent hewo --repo-root . --output-dir . --readme README.md
python3 .agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py \
  --agent hewo --repo-root . --output-dir . --readme README.md --strict
```

README 必须保留两组精确 marker：`<!-- BEGIN GENERATED: agent-architecture.mmd -->` / `<!-- END GENERATED: agent-architecture.mmd -->`，以及 `<!-- BEGIN GENERATED: agent-optimization-loop.mmd -->` / `<!-- END GENERATED: agent-optimization-loop.mmd -->`。生成器原地更新这些块。下游必须按自己的 contract 重新生成，不能把 hewo 图表当作产品事实。GitHub 渲染 Mermaid，其他 renderer 可能显示代码。

## 完整 infrastructure smoke

使用已批准的可重建 evidence 目录，不提交原始输出：

```bash
PI_AUTH_FILE="$HOME/.pi/agent/auth.json" \
LLM_PROVIDER=<provider> LLM_MODEL=<model> \
BENCHMARK_RUN_DIR=/path/to/task/hewo-evidence \
./.agents/scripts/run-benchmark.sh hewo
```

`run-benchmark.sh` 凭据/目录入口为 `PI_AUTH_FILE`、`PI_MODELS_FILE`、`BENCHMARK_API_KEY_ENV`。verifier 必须确认独立 workspace 中加载 `runtime-smoke` skill、读取 knowledge/workflow、写入并重新读取 `artifacts/hewo-smoke.md`；检查 `Product runtime`、`Workspace access`、`Skill loaded`、`HEWO_KNOWLEDGE_OK`、`HEWO_TOOL_OK`、`HEWO_WORKFLOW_OK`。不能由开发 agent 预写 artifact 冒充产品生成。

凭据接线见 [provider-e2e](provider-e2e.md)。helper 仅接受四种来源 flags：`--pi-auth-file`、`--api-key-env`、`--api-key-stdin`、`--bundle`；runtime 不写死 provider。不隐式读 `.env`。bundle 生成工具为 `./.agents/scripts/create-provider-bundle.sh <provider> <model> PROVIDER_API_KEY /approved/private/bundle`；bundle 为 0700、credential 为 0600，只含所选 provider metadata 与单个 credential，不含 HOME/auth 数据库；Docker 只读挂载到 `/run/provider-bundle`。bundle 必须位于允许存储凭据的仓库外私有位置，使用后按凭据管理规则清理，不能放入普通任务临时目录。

pi 凭据优先级为显式 `--api-key`、auth.json、环境变量、自定义 provider key。`pi --list-models` 是 auth-filtered 枚举而非 E2E 证明。真实 provider/model、credential-source、CLI version、runtime revision 和 artifact 路径只记本机私有记录，公开仓库仅保留占位示例。轨迹和 benchmark 输出在可重建目录保存，分享前 scrub，不能提交 raw provider output 或 secrets。机器 sandbox 限制必须如实记 blocked，不能默认关闭隔离掩盖。

## 变更验证清单

```bash
./.agents/scripts/validate-definition.sh hewo
bash -n scripts/setup-dev.sh distribution/install.sh \
  distribution/container-entrypoint.sh docker/run-hewo-e2e.sh \
  scripts/build-release.sh .agents/scripts/run-benchmark.sh .agents/scripts/run-agent-loop.sh \
  .agents/scripts/freeze-agent-run.sh .agents/scripts/build-agent-image.sh
git diff --check
```

backend/Docker/release 变更还需构建 image、检查 pi 版本、真实最小 E2E、至少一个完整 smoke、扫描镜像与 payload 中的开发指令/credentials，以及检查 CI definition/image checks。声明 tools 时检查：

```bash
docker run --rm --entrypoint bash hewo:dev -c 'command -v hewo-tool && hewo-tool --check'
```

必须看到 `HEWO_TOOL_OK`；该基础设施诊断不是行为证据，完整 smoke 仍需产品通过 skill 调用并写 artifact。不要重建 Agent 行为单元测试套件；使用真实 Docker E2E 和 GitHub issue 证据。

## 下游用户文档样板

复制 [USER.md](../../USER.md)，适配 Agent name、`src/<agent_name>/runtime/`、pi-only backend、实际验证的 provider/models、`pi -e <installed-runtime-package>`（保留隔离参数）。保留三层边界、reuse-first、凭据安全和真实 E2E 要求；只替换 scaffold、默认模型和实际证据，不复制另一套 runtime 实现。
