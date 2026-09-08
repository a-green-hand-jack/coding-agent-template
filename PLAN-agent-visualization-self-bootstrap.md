# Agent 可视化与自举优化 Loop 计划

## 1. 标题与状态

- **Plan id**：`agent-visualization-self-bootstrap`
- **强度**：L3（多文件开发 skill、生成物、开发规范、固定评估协议与受保护的自举验证）
- **Review state**：Closure panel reviewed → Revised → Aligning
- **当前状态**：closure feasibility 席位已 approve；risk 席位发现 7 条 material findings，均已逐条 disposition 并写入本版；尚未开始实现
- **计划对齐记录**：初始对齐 fingerprint 为 `8acd732f706aa3ffec0efbc2dd8c336c841d109a387de56d567c213e84a21057`；经过多轮 panel 与用户重新对齐；closure risk 修订改变了计划摘要，alignment 现为 pending
- **产品边界**：本计划不修改 `src/hewo/runtime/` 的产品行为。skill、contract、comparator、图、README 生成区和开发规范都属于项目内、产品外的 development resources
- **计划文件说明**：仓库已有一个历史性的 `PLAN.md`（development-machine-profile 计划），本计划遵守仓库的 `PLAN-<slug>.md` 约定，使用 `PLAN-agent-visualization-self-bootstrap.md`，不覆盖已有 `PLAN.md`

## 2. 动机与目标

当前仓库已经有一个项目内、产品外的阶段编排器，但开发 coding agent 仍缺少一份足够醒目、结构化且可执行的设计约束，来回答：

1. 被开发的产品 Agent 到底由什么组成，哪些是产品行为，哪些是开发基础设施？
2. 一个“功能已经完整但性能一般”的第一版，如何成为可复现的 functional baseline？
3. coding agent 如何用固定 benchmark、固定运行条件、固定指标和明确接受/拒绝条件证明 candidate 确实优于 current best？
4. provider、基础设施、benchmark/verifier 故障如何与产品质量回归区分？
5. 当前 `hewo` 只是 Hello World/infrastructure smoke 时，如何诚实表达限制，而不把 smoke pass 伪装成性能提升？
6. 帮助设计 Loop 的 skill 本身，如何在不修改 evaluator 或 fixture 以制造绿色结果的前提下，通过同一套 Loop 逐步改进？

本计划交付一套面向 **human developer 和 development coding agent** 的可视化与 Loop-design skill：

- 自动生成描述当前产品 Agent 结构的 `agent-architecture.mmd`；
- 自动生成描述产品 Agent 优化状态机的 `agent-optimization-loop.mmd`；
- 由同一个 skill 将两个图同步到 `README.md` 的受控 generated blocks，并保留 `.mmd` 作为唯一 source of truth；
- 把“先功能完整 baseline，后性能优化”的生命周期写成 coding agent 必须遵守的设计 gate；
- 提供一个很薄的、确定性的 evaluation-result schema 和 comparator，足以判断 `accepted / rejected / blocked / baseline-invalidated`，但不实现新的 LLM、benchmark runner 或自动提交器；
- 提供固定 fixture、protected evaluator 和负例，使 skill 自身可以作为 candidate 进行受约束的自举；
- 对当前 `hewo` 只生成真实的 smoke/infrastructure 状态，不虚构领域质量指标。

## 3. 已验证的当前状态

以下事实来自当前 checkout，作为实现边界和验收基线：

- `AGENTS.md:104-118` 已定义 development coding agent 使用的项目内、产品外 loop，但目前主要是 validation、audit、infrastructure 和 benchmark 阶段，没有 baseline/candidate/current-best、指标比较、接受/拒绝或停止状态机。
- `DEV.md:243-271` 已区分开发 loop、benchmark 和产品 runtime，也要求分类失败；尚未把“功能完备版本 → baseline → candidate → 比较 → 接受/拒绝”写成完整的强制契约。
- `.agents/workflows/agent-development.md:7-48` 是现有 workflow 的权威入口，当前是线性八步流程；文档提到后台模式，但当前 `scripts/run-agent-loop.sh` 并未实现完整的 baseline/evaluation registry。本计划不把未实现的后台能力描述成已完成事实。
- `scripts/run-agent-loop.sh:1-5,327-431` 是前台阶段编排器，按 definition validation、consistency audit、infrastructure health、benchmark 顺序执行，并区分 provider-backed 与 `infrastructure-only`；它没有管理 baseline、candidate、best、指标比较或回滚。
- `benchmarks/README.md:1-8` 已说明 benchmark 是 capability/regression 的一个 stage，而不是产品 runtime；尚未定义独立的 evaluation contract、结果 schema 和接受策略。
- `src/hewo/agent.yaml:1-5` 声明 `runtime_dir: runtime`、`development_dir: development`；`src/hewo/development/` 当前不存在。
- `src/hewo/runtime/` 当前只有 greeting/infrastructure-smoke 相关定义；`identity.md` 明确 HeWo 是 Hello World/reference runtime，不能作为论文质量等复杂性能任务的真实产品样本。
- 当前 runtime 文件包括 identity、memory policy、opencode config、knowledge、一个 runtime-smoke skill、两个 workflow 和 tools；因此结构图可以真实生成，但优化图必须标记 smoke-only/design-incomplete。
- `.agents/skills/development-machine-profile/` 展示了本仓库的 skill 约定：渐进式加载、确定性脚本、source-of-truth 与生成物分离、可重复生成；新 skill 沿用这些约定。
- `.agents/template-content-registry.json:30-56,59-180` 要求所有 tracked paths 被 registry 覆盖，并支持 selective skill；新增 skill、contract、图和 scoped instructions 必须在引入路径的 commit 中同步 registry。
- 当前工作树在 `main`，与 `origin/main` 对齐；旧 `PLAN.md` 未作修改，本轮计划文件是唯一新文件。

## 4. 已定决策与待用户确认的提案

### 4.1 用户已确认的目标

以下内容直接来自用户需求，标记为 `user-confirmed`：

- `user-confirmed`：需要两个 Mermaid 源文件，一个介绍产品 Agent 本身，一个介绍优化产品 Agent 的 Loop。
- `user-confirmed`：两个 `.mmd` 要由一个可复用 skill 自动生成，并由该 skill 插入/同步到 `README.md`。
- `user-confirmed`：重点是教会 development coding agent 认真设计产品优化 Loop，而不是让当前简单的 `hewo` 立即拥有复杂调优系统。
- `user-confirmed`：优化 Loop 本质是状态机，应有简单、固定、可重复的产品改进验证方式。
- `user-confirmed`：生命周期必须区分“功能完备但 performance 一般的第一版”与后续性能优化；论文写作 Agent 是解释这个区别的例子。
- `user-confirmed`：skill 自身也必须能通过 Loop 优化，形成受约束的自举。
- `user-confirmed`：先建立计划并由用户 review；用户说 `对齐完成` 后才进入 panel/实现。

### 4.2 Panel 后的提议决策（需用户再次确认）

- `agent-proposed`：skill 名称固定为 `.agents/skills/agent-evaluation-loop-design/`。它不只是画图，还定义 contract、状态机、比较协议和自举规则。
- `agent-proposed`：根目录生成物固定命名为 `agent-architecture.mmd` 与 `agent-optimization-loop.mmd`。它们是 human review 的开发设计产物，不是产品 runtime；downstream 必须重新运行 skill，不得把当前 hewo 图当成自己的产品事实。
- `agent-proposed`：evaluation contract 的唯一默认位置为
  `src/<agent_name>/development/evaluation-contract.json`，由 `agent.yaml` 的 `development_dir` 解析；CLI 提供显式 `--contract` 覆盖，fixture 也使用同一规则，不再允许未定义的“等价路径”优先级。
- `agent-proposed`：contract 使用标准库可解析的 JSON schema v1；schema 明确字段、类型、枚举、metric direction、重复次数、revision identity 和接受阈值。baseline/current-best 是独立 result，不写回 contract，避免 baseline pointer 改动反过来改变 contract hash。
- `agent-proposed`：增加一个薄的 `compare-evaluations.py`。它只读取已产生的 current-best/candidate result JSON，不运行 provider、不修改 runtime、不提交代码；它输出确定性的 `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`（benchmark-local acceptance recommendation，等待 promotion）、`CANDIDATE_REJECTED`、`ENVIRONMENT_BLOCKED`、`EVALUATION_BLOCKED`、`BASELINE_INVALIDATED`、`GENERALIZATION_REQUIRED` 或 design/baseline incomplete 状态。`ACCEPTED_AS_CURRENT_BEST` 是 promotion 后的 lifecycle 状态，不是 comparator 默认直接输出的 result state。
- `agent-proposed`：`condition_manifest` 是独立的 canonical 文件，覆盖所有 run-affecting input；result 只引用它，不内嵌一份可漂移的 condition copy。comparator 分别校验两份 manifest 的 schema/hash，再比较 canonical 内容完全一致；未被 manifest 表达的 input 使结果不可比较。
- `agent-proposed`：contract schema 中的 `environment` 描述预期/选择的执行条件；每次实际运行的 image digest、tool versions、request/sampling/retry/timeout/defaults 等仍必须写入 manifest；两者不一致即 `EVALUATION_BLOCKED`。
- `agent-proposed`：fixed benchmark 结果只能支持 benchmark-local acceptance recommendation；若 contract 的 `claim_scope` 为 `product-general`，必须运行 contract 预先声明且未参与调参的 holdout/canary，并记录独立 task-set hash、candidate selection freeze、阈值和 human/domain review；否则输出 `GENERALIZATION_REQUIRED`，不更新 best。
- `agent-proposed`：将 result 的 acceptance 与 promotion 分开。薄 comparator 在 fixed benchmark 通过时输出 `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`；只有单独的 approved-runner/human promotion gate 完成后，生命周期才记录 `ACCEPTED_AS_CURRENT_BEST`，且 comparator 永不写入 current-best。
- `agent-proposed`：固定 result/comparator 的状态与退出码映射：`0=CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`，`10=CANDIDATE_REJECTED`，`20=DESIGN_INCOMPLETE|FUNCTIONAL_BASELINE_MISSING|SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`，`30=BASELINE_INVALIDATED`，`40=ENVIRONMENT_BLOCKED`，`41=EVALUATION_BLOCKED`，`42=GENERALIZATION_REQUIRED`，`2=CLI/schema malformed`；JSON `state` 字段区分同一 exit-code family。
- `agent-proposed`：当前 hewo 增加显式 `src/hewo/development/evaluation-contract.json`，模式为 `infrastructure-smoke-only`，只声明功能 smoke checks 和 artifact，不声明虚构的 performance metric；图上显示 `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`。
- `agent-proposed`：缺失 contract、缺少必要字段、performance 模式没有 functional baseline 或没有 primary metric，都产生机器可识别的 `DESIGN_INCOMPLETE`/`FUNCTIONAL_BASELINE_MISSING`，而不是自动进入性能评估。
- `agent-proposed`：自举 evaluator 从 immutable Git base snapshot 执行，而不是信任 candidate 自己修改后的 evaluator。base comparator、fixture、expected invariants 和 fixed outcome cases 从 `git archive <base_ref>` 取得；candidate 只接收 disposable fixture copy 和 writable output dir。运行前后校验 base manifest，candidate 无法用自己的 comparator 改写期望结果。
- `agent-proposed`：self-bootstrap 的 candidate manifest 必须在 base commit 中预先提交，并固定 `allowed_candidate_paths`；base evaluator 另外固定 protected path 集合、可写 output root 和 external report schema。candidate 只能修改 allowlist，不能通过 manifest 自己扩大权限或声明新的 evaluator 规则。
- `agent-proposed`：将 `fixtures/self-bootstrap/readme-sync-candidate.json` 扩展为包含 `schema_version`、hypothesis、observable delta、expected artifacts/assertions、allowlisted candidate paths、base-protected paths、external report schema 和禁止写入的 roots；C1 gate 校验 manifest 的路径安全性和 allowlist 不可自我放宽。
- `agent-proposed`：本次不把 `scripts/run-agent-loop.sh` 扩展成完整 optimizer，也不增加 LLM client、session manager、approval loop、tool loop、provider adapter 或后台 registry；comparator 是最小协议，不是第二套 runtime。
- `acceptance` 的阈值、secondary regression、holdout/canary 规则和 `evidence_policy` 是 contract policy；current-best 的 promotion record 是 result/provenance，不得反向写入 contract。

## 5. 非目标

- 不把当前 `hewo` 改造成论文 Agent，不增加复杂业务行为。
- 不把 contract、图生成脚本、comparator 或开发 workflow 放进 `src/hewo/runtime/`。
- 不实现新的 LLM client、agent session manager、approval loop、tool loop、provider adapter 或平行 coding-agent runtime。
- 不把现有前台 `run-agent-loop.sh` 误称为完整自动性能优化器；本计划只补设计契约、图、结果比较协议和自举验证。
- 不用一次 smoke、一次 provider response、换模型或换 provider 证明产品性能提升。
- 不在同一个 candidate 变更里放宽 verifier、修改 benchmark、修改 metric policy 和修改产品以制造通过；这些是独立的 contract change，需要重新 baseline 和 human review。
- 不保存 credentials、raw provider session、未 scrub trajectory 或个人数据。
- 不为 hewo 虚构质量分数、baseline 结果或论文产品行为。
- 不在 README 中维护与 `.mmd` 分叉的手写 Mermaid source of truth。
- 不要求简单 Agent 进行不必要的多目标统计实验；但任何声称“性能优化”的 Agent 都必须定义自己的最小 contract、baseline 和比较规则。
- 不把 fixed benchmark 上的 comparator pass 表述为产品普适提升；v1 不实现完整 holdout 平台，product-general claim 在 independent holdout/canary 与 human/domain review 前保持 `GENERALIZATION_REQUIRED`。
- 不把 result 中自报的 runner/provenance metadata 当成密码学 attestation；薄 comparator 只证明 schema、hash 与 fixed benchmark policy 下的结果一致性，不自动 promotion。
- 不修改或覆盖现有 `PLAN.md`。

## 6. coding agent 必须遵守的 Loop 设计契约

### 6.0 普通产品开发的最短教学路径

`SKILL.md` 必须把下面的路径放在 self-bootstrap/归档隔离说明之前，并把它作为默认入口。它适用于普通产品 Agent，不要求 coding agent 先理解 Git archive、detached worktree 或 protected evaluator：

```text
product goal
  → functional contract
  → functionally complete baseline
  → one fixed condition manifest
  → candidate result
  → compare with current best
  → accept / reject / block / re-measure baseline
```

每一步的最小产物是：

1. **Product goal**：写清用户、输入、输出和不声称的范围；
2. **Functional contract**：列出稳定的功能 checks、必要 artifact 和 failure taxonomy；
3. **Functional baseline**：先做可工作的第一版，即使质量/性能一般；若输入输出或 verifier 尚未稳定，状态只能是 `FUNCTIONAL_BASELINE_MISSING`；
4. **Fixed condition**：生成 canonical condition manifest，固定 benchmark、verifier、runtime、provider/model、sampling、重复次数和阈值；
5. **Candidate result**：用 approved runner 产生 secret-free samples、evidence 和 provenance；不手写 aggregate 或把 provider 失败改写成产品回归；
6. **Compare**：用薄 comparator 校验 baseline validity、condition hash、samples、evidence 和 metric；它不运行 provider、不改写 best；
7. **Decision**：只有固定 benchmark 条件下的证据满足规则才可产生 acceptance recommendation；环境/评估阻塞不更新 best，条件变化先重测 baseline，产品普适声明还需要独立 holdout/canary 和 human/domain review。

当前 `hewo` 只有 `infrastructure-smoke-only` contract，因此普通路径在 smoke 状态停止，不应为了“进入优化”虚构 primary metric。下面的自举协议是 skill 自身优化时才使用的 advanced path。

### 6.1 两阶段生命周期

coding agent 在开始说“优化”之前，必须先区分：

```text
HUMAN_INTENT_DEFINED
        ↓
CONTRACT_DESIGNED
        ↓
FUNCTIONALLY_COMPLETE_BASELINE_BUILT
        ↓
BASELINE_MEASURED
        ↓
IMPROVEMENT_HYPOTHESIS_READY
        ↓
CANDIDATE_IMPLEMENTED
        ↓
CANDIDATE_EVALUATED_ON_FIXED_CONDITIONS
        ↓
EVIDENCE_VALIDATED
        ↓
COMPARE_WITH_CURRENT_BEST
```

第一版可以质量一般，但必须是**可工作的 baseline**：输入输出契约成立、必要 artifact 存在、功能 verifier 能稳定判断结果。若这些条件不成立，状态是 `FUNCTIONAL_BASELINE_MISSING`，不是“低性能版本”；coding agent 必须先完成产品功能或 contract 设计。

### 6.2 最小状态机

`agent-optimization-loop.mmd` 必须表达以下规范状态和转移；排版可以调整，语义和 guard 不能删减：

```text
INTENT_DEFINED
  → CONTRACT_DESIGNED
  → FUNCTIONAL_BASELINE_BUILT
  → BASELINE_MEASURED
  → HYPOTHESIS_READY
  → CANDIDATE_IMPLEMENTED
  → CANDIDATE_EVALUATING
  → EVIDENCE_VALIDATED
  → COMPARE_WITH_CURRENT_BEST
       ├─ evaluation-condition identity mismatch     → BASELINE_INVALIDATED
       ├─ provider/infrastructure/credential failure → ENVIRONMENT_BLOCKED
       ├─ benchmark/verifier/evidence failure        → EVALUATION_BLOCKED
       ├─ missing or invalid design fields           → DESIGN_INCOMPLETE
       ├─ invalid/nonfunctional current best          → FUNCTIONAL_BASELINE_MISSING
       ├─ functional contract failure                → CANDIDATE_REJECTED
       ├─ threshold not met or regression            → CANDIDATE_REJECTED
       └─ fixed benchmark threshold met              → CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE
            ├─ benchmark-local + promotion gate       → ACCEPTED_AS_CURRENT_BEST
            │                                           → HYPOTHESIS_READY
            │                                           → STOPPED
            └─ product-general claim                  → GENERALIZATION_REQUIRED
```

图和 skill 还必须表达：

- current best 与 candidate 的 `subject.definition_revision` 是不同的被测对象 revision；该差异是优化比较的前提，而不是 baseline invalidation 原因；
- canonical `condition_manifest`、current-best revision、candidate revision 和 evidence manifest 可追溯；任何无法放入 manifest 的 run-affecting input 都阻止比较；
- `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE` 只表示 fixed benchmark-local comparator pass；它不等于 product-general improvement，也不会由 comparator 自动更新 best；
- `GENERALIZATION_REQUIRED` 要求一个未用于调参/筛选 candidate 的 holdout/canary 及 human/domain review，缺失时禁止普适产品改进声明；
- `ENVIRONMENT_BLOCKED` 与 `EVALUATION_BLOCKED` 都不更新 best，也不计为产品回归；修复对应层后重跑同一 candidate；
- `BASELINE_INVALIDATED` 表示评估条件已经改变，不允许继续比较，必须在新 condition identity 下重新测 current best；
- candidate 被拒绝后可以回到 `HYPOTHESIS_READY`，或显式回滚到上一份 current best；
- `STOPPED` 必须有原因：目标达到、连续 N 次无实质改善、预算/时间耗尽或 human 停止；
- 缺少 contract/metric/current-best result 时不得进入 performance comparison；hewo 的 smoke 模式明确停在 `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`。

### 6.3 Normative evaluation contract v1

contract 的共同必填结构固定如下（完整字段类型、required/optional 表、枚举和 invalid examples 写入 `references/evaluation-contract.md`）：

```json
{
  "schema_version": 1,
  "agent": "paper-agent",
  "mode": "performance",
  "contract_revision": "2026-09-01",
  "metric_policy_revision": "metric-policy-1",
  "product": {
    "goal": "...",
    "input": "...",
    "output": "..."
  },
  "functional_contract": {
    "checks": [{"id": "...", "description": "...", "source": "..."}],
    "required_artifacts": ["..."]
  },
  "benchmark": {
    "task_set": "...",
    "revision": "...",
    "verifier": "...",
    "verifier_revision": "..."
  },
  "environment": {
    "backend": "...",
    "provider": "...",
    "model": "...",
    "runtime": "...",
    "repetitions": 3,
    "aggregation": "mean"
  },
  "metrics": {
    "primary": {"name": "...", "direction": "higher-is-better", "unit": "..."},
    "secondary": []
  },
  "acceptance": {
    "minimum_primary_delta": 0.01,
    "max_secondary_regression": {},
    "require_functional_pass": true
  },
  "stop_conditions": ["..."],
  "evidence_policy": {
    "scrubbed_only": true,
    "required_kinds": ["artifact", "verifier-report", "scrubbed-trajectory"],
    "approved_producers": [
      {"id": "run-benchmark.sh", "revision": "..."},
      {"id": "approved-verifier", "revision": "..."}
    ]
  },
  "generalization": {
    "claim_scope": "benchmark-local",
    "holdout": null,
    "human_domain_review_required": false
  }
}
```

约束：

- `mode` 只有 `performance` 与 `infrastructure-smoke-only`。
- v1 的 `aggregation` 只支持 `mean`，`repetitions` 是大于等于 1 的整数；未来增加聚合方式必须升级 metric-policy revision 并重新 baseline。
- `performance` 必须定义 primary metric、benchmark/verifier、环境、重复次数和接受阈值；current-best/baseline 不写回 contract，而是作为独立 result 文件传给 comparator。没有 current-best result 时返回 `FUNCTIONAL_BASELINE_MISSING`。
- `performance` 还必须声明 `generalization.claim_scope`：`benchmark-local` 只允许作 benchmark 能力/回归结论；`product-general` 必须声明独立 holdout/canary 的 revision、未参与调参的边界、通过阈值和 human/domain review 要求。没有这些信息时返回 `GENERALIZATION_REQUIRED`，而不是扩大结论范围。
- `generalization.claim_scope=product-general` 时，contract 必须提供一个独立的 holdout/canary policy：task-set/input hash、在 candidate selection 前冻结的 reference、`not_used_for_tuning=true`、独立 acceptance threshold 和 human/domain review 要求。holdout 结果不能从 benchmark result 复制，也不能由 candidate manifest 临时声明。
- `infrastructure-smoke-only` 可以没有质量 metric，但必须有功能 smoke checks 和 artifact 要求；状态为 `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`，可生成图但不能接受 performance improvement。
- contract 缺失或 JSON/schema 无效时状态为 `DESIGN_INCOMPLETE`；生成器可渲染带 TODO 的图，但 strict validator 必须非零退出。
- `contract_sha256` 是 canonical JSON（UTF-8、排序 key、固定 separators）摘要；因为 contract 不含可变 baseline pointer，同一评估政策的 hash 稳定。
- `evidence_policy.approved_producers` 固定列出允许产生 result/evidence 的 runner/verifier 标识和 revision；这只是可审计的信任边界声明，不是 comparator 能独立证明的远程证明。

### 6.3.1 Generalization 与 promotion 的条件

- `benchmark-local` 是 v1 的默认 claim scope；它可以产生 `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`，但报告必须明确“只在固定 benchmark 条件观察到”。
- `product-general` 不是 benchmark comparator 的隐含结论。只有在 candidate selection/tuning 已冻结后，使用独立 holdout/canary 重新运行同一 functional checks 和预先声明的 metric，且 holdout 结果及 human/domain review 通过，才允许 promotion report 使用 product-general wording；否则保持 `GENERALIZATION_REQUIRED`。
- holdout/canary 必须有独立 task-set/input hash、verifier/metric policy revision 和 result/evidence provenance。若 holdout 与 benchmark 共享被调参的样本、prompt、阈值或选择信息，validator 将其视为非独立并返回 `GENERALIZATION_REQUIRED`。
- current-best promotion 不是 comparator 的副作用。promotion record 至少绑定被 promotion 的 result SHA、condition-manifest SHA、approved producer/revision 和 human/decision reference；缺少或不匹配时 current best 无效，不能成为比较基准。
### 6.3.2 Canonical condition manifest（所有运行条件的唯一摘要）

`condition_identity` 不是由 result 自由填写的短字段集合，而是从一个独立的、经过 hash 的 `condition-manifest.json` 派生的比较视图。每次 current-best/candidate run 都必须生成并保存一个 secret-free manifest，至少包含以下 canonical sections：

```json
{
  "schema_version": 1,
  "contract": {"revision": "...", "sha256": "..."},
  "benchmark": {
    "task_set_revision": "...",
    "task_input_sha256": "...",
    "holdout_policy_revision": "..."
  },
  "verifier": {"id": "...", "revision": "...", "source_sha256": "..."},
  "metric_policy": {"revision": "...", "definition_sha256": "..."},
  "execution": {
    "backend": "...", "provider": "...", "model": "...", "runtime": "...",
    "image_digest": "...", "tool_versions": {},
    "request_parameters": {}, "sampling": {}, "seed": "...",
    "retry_policy": {}, "timeout_seconds": 0,
    "locale": "C", "timezone": "UTC"
  },
  "sampling": {"repetitions": 3, "aggregation": "mean"}
}
```

Normative rules：

- Canonical bytes use UTF-8, sorted keys, fixed separators, no credentials, prompts containing secrets, raw provider responses or personal data. `condition_manifest_sha256` is SHA-256 over those bytes.
- The manifest must enumerate every input that can change a run. Unknown, omitted or locally inferred run-affecting inputs produce `EVALUATION_BLOCKED`; a prose claim that two runs are equivalent is insufficient.
- Result fields `condition_identity` and `condition_manifest_*` are cross-checked projections/references, never trusted over the manifest. Current-best and candidate must reference manifests with equal canonical bytes and hashes before metric comparison.
- `task_input_sha256`, verifier source hash, image/tool versions, request/sampling/retry/timeout settings, locale/timezone and seed are required even when their values are defaults. Secret-bearing values are represented by a non-secret policy/revision hash, never copied into the manifest.
- A manifest is immutable after a result is produced. Any changed manifest requires a new condition identity and a fresh current-best measurement; it cannot be repaired by editing the result.

### 6.4 Result、condition identity 与最小 comparator

每次 current-best/candidate 运行产生一个 secret-free result JSON。被测 revision 与评估条件必须分开：

```json
{
  "schema_version": 1,
  "role": "candidate",
  "run_id": "...",
  "subject": {"definition_revision": "candidate-commit"},
  "condition_identity": {
    "condition_manifest_path": "condition-manifest.json",
    "condition_manifest_sha256": "...",
    "contract_revision": "...",
    "contract_sha256": "...",
    "benchmark_revision": "...",
    "verifier_revision": "...",
    "metric_policy_revision": "...",
    "backend": "...",
    "provider": "...",
    "model": "...",
    "runtime": "...",
    "repetitions": 3,
    "aggregation": "mean"
  },
  "condition_manifest_path": "condition-manifest.json",
  "condition_manifest_sha256": "...",
  "samples": [
    {
      "sample_id": "run-1",
      "run_status": "completed",
      "failure_class": "none",
      "functional_status": "pass",
      "primary_value": 0.75,
      "secondary_values": {},
      "evidence": [
        {
          "kind": "artifact",
          "path": "evidence/paper.md",
          "sha256": "...",
          "producer": "run-benchmark.sh",
          "producer_revision": "..."
        }
      ]
    }
  ],
  "aggregate": {
    "primary_value": 0.75,
    "secondary_values": {}
  }
}
```

Normative taxonomy：

- `run_status`：`completed | blocked`。
- `failure_class`：`none | credential | provider | infrastructure | benchmark-verifier | evidence`。
- 产品功能失败表示 `run_status=completed` 且 `functional_status=fail`；它不是 environment blocked。
- evidence path 必须是相对 result 文件目录的安全相对路径（禁止绝对路径和 `..`），并包含 `kind/path/sha256/producer/producer_revision`；comparator 校验存在性、SHA-256 和 contract 要求的 kinds。路径先以 lexical 规则拒绝绝对路径、`..`、NUL 和空路径，再以 `realpath`/`Path.resolve(strict=True)` 校验最终文件仍位于 result 目录内；v1 拒绝 result、evidence 或其父目录中的 symlink，避免路径穿越。它验证完整性和 provenance metadata，但不声称密码学证明 provider 响应的真实性；contract allowlisted approved runner/verifier、受控执行环境与 human review 仍是信任边界。
- `producer` 与 `producer_revision` 必须命中 contract 的 `approved_producers`；result 中自报 producer 只能满足可审计 metadata 检查，不能被 comparator 当作远程 attestation。
- sample 数必须等于 contract `repetitions`；v1 comparator 从 samples 重新计算 mean，不能信任 result 中自报 aggregate。

`condition_identity` 只包含固定评估条件，current best 与 candidate 必须完全匹配；它必须与两个独立 condition manifest 的 canonical bytes/hash 一致。`subject.definition_revision` **不得**加入 exact-match identity；它记录两个不同的产品 revision。current-best 还必须带有可审计但不等同于密码学证明的 promotion record：`status=promoted`、被 promotion 的 result SHA、approved runner/human decision reference；缺失或不一致只能是 `FUNCTIONAL_BASELINE_MISSING`，不能自动把任意 candidate 当作 best。比较 precedence 固定为：

1. contract 缺失/无效或 smoke-only → `DESIGN_INCOMPLETE` / `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`；
2. current-best result 缺失、role 错误、promotion record 缺失、functional/evidence/manifest 无效或 current best 自身不是 completed/pass → `FUNCTIONAL_BASELINE_MISSING`（`CURRENT_BEST_INVALID` reason）；
3. candidate/current-best condition manifest 缺失、不可解析、hash 错误、路径不安全、approved producer 不匹配、样本结构不完整或 projection 与 manifest 不一致 → `EVALUATION_BLOCKED`；
4. condition manifests canonical 内容或 hash 不匹配 → `BASELINE_INVALIDATED`；
5. 任一 sample 为 `blocked` 且 failure class 是 credential/provider/infrastructure → `ENVIRONMENT_BLOCKED`；
6. 任一 sample 为 `blocked` 且 failure class 是 benchmark-verifier/evidence，或 evidence/hash/producer/repetition/aggregation 不完整 → `EVALUATION_BLOCKED`；
7. 任一 completed sample 的 functional status 非 pass → `CANDIDATE_REJECTED`；
8. 从 samples 重算 primary mean，并按 direction 检查 minimum delta，同时检查 secondary regression；不满足 → `CANDIDATE_REJECTED`；
9. contract 要求 `product-general` 且没有独立 holdout/canary 的有效结果和 human/domain review → `GENERALIZATION_REQUIRED`；
10. 全部 fixed benchmark-local 规则满足 → `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`；它是机器 acceptance recommendation，不是自动 promotion。

comparator 固定接受：

```text
--contract PATH
--current-best PATH
--candidate PATH
[--output PATH]
```

输入文件和 evidence 读取前必须通过 safe-realpath 检查；`--output` 只能写入显式、非 symlink 的 report path，使用临时文件加原子 replace。它不运行 benchmark、不自动修改 current best，只输出 machine-readable state/reason/exit code，并在 report 中记录 contract/result/manifest SHA、approved producer checks、base/current-best validity 和 promotion status。human/coding agent 决定是否把 accepted result 记录成新 best，并保留旧 best 以便回滚。

### 6.5 防止 benchmark overfitting 和自欺

skill、validator、comparator、文档和图必须提醒 coding agent：

- benchmark 是 capability/regression measurement，不是产品 identity；
- 不得为 verifier 增加 benchmark-specific runtime hack；
- 修改 benchmark、verifier、metric policy、阈值或 contract schema 是独立设计变更，需要 human review，并使旧 baseline 失效；
- 不同 provider/model/runtime 的结果默认不可直接比较；
- 一次偶然 response 不能更新 best，需要 contract 声明重复次数和 aggregation；
- 所有结论记录 definition/contract/benchmark/verifier/metric identity、运行条件和 scrubbed evidence；
- provider 或基础设施失败不能被折叠为“Agent 变差”，也不能被折叠为“Agent 变好”。

## 7. Skill 与生成物设计

### 7.1 文件地图与 source of truth

计划新增：

```text
.agents/skills/agent-evaluation-loop-design/
├── AGENTS.md
├── SKILL.md
├── references/
│   ├── AGENTS.md
│   ├── agent-architecture-schema.md
│   ├── evaluation-contract.md
│   └── self-bootstrap.md
├── scripts/
│   ├── AGENTS.md
│   ├── generate-agent-diagrams.py
│   ├── validate-agent-evaluation.py
│   ├── compare-evaluations.py
│   └── self-bootstrap-check.py
└── fixtures/
    ├── AGENTS.md
    ├── paper-agent/
    │   ├── AGENTS.md
    │   ├── agent.yaml
    │   ├── development/evaluation-contract.json
    │   ├── development/AGENTS.md
    │   ├── runtime/identity.md
    │   ├── runtime/memory-policy.md
    │   ├── runtime/knowledge/README.md
    │   ├── runtime/skills/paper-writing/SKILL.md
    │   ├── runtime/workflows/write-paper.md
    │   ├── runtime/tools/README.md
    │   └── expected-invariants.json
    └── self-bootstrap/
        ├── AGENTS.md
        ├── readme-sync-candidate.json
        ├── current-best-result.json
        ├── accepted-candidate-result.json
        ├── rejected-candidate-result.json
        ├── environment-blocked-candidate-result.json
        ├── evaluation-blocked-candidate-result.json
        ├── invalidated-candidate-result.json
        └── evidence/
            ├── AGENTS.md
            └── artifact.txt

src/hewo/development/
├── AGENTS.md
└── evaluation-contract.json

agent-architecture.mmd
agent-optimization-loop.mmd
```

所有新增 versioned source directories 都有 scoped `AGENTS.md`；这些 instructions 只服务 development coding agent，并由 release/build 边界排除。fixture 是抽象的论文 Agent 结构样本，不是 hewo 产品，也不产生 provider evidence。

### 7.2 确定性的 CLI 合约

`generate-agent-diagrams.py` 固定支持：

```text
--agent NAME                 默认 hewo
--repo-root PATH             默认当前仓库根目录
--agent-root PATH            默认 <repo-root>/src/<agent>
--contract PATH              默认 <agent-root>/<development_dir>/evaluation-contract.json
--output-dir PATH            默认 <repo-root>；写两个固定 basename
--readme PATH                默认 <repo-root>/README.md
--no-readme                  只写 .mmd，不碰 README（fixture 使用）
--init-readme                缺 marker 时显式插入；不允许默认静默插入
--check                     只比较生成结果，不写文件
```

`validate-agent-evaluation.py` 还支持 `--strict` 与 `--require-performance`：有效的 smoke-only contract 在 `--strict` 下返回 0 并输出 `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`；只有 `--require-performance` 才把 smoke-only 当作非零退出。contract 缺失/schema 无效在两种模式下都非零。

规则：

- `agent-root`、contract、output 和 README 的相对路径都相对对应显式 root 解析；不依赖当前 shell 的偶然 cwd。
- `agent.yaml` 是简单、无第三方依赖的 key/value manifest；`runtime_dir`、`development_dir` 缺失或指向不存在路径时明确生成 missing 状态。
- 产品图的组件节点来自真实 runtime 文件/目录扫描：identity、memory policy、knowledge、skills、workflows、tools；不从 Markdown 内容猜测未声明能力。fixture 提供完整最小 runtime tree，证明扫描不会靠“虚拟节点”通过。
- 产品输入、输出、功能契约、artifact 和 smoke/performance 语义来自显式 evaluation contract；contract 缺失时显示 `DESIGN_INCOMPLETE`，不猜测论文质量等语义。
- 所有写入用临时文件加原子 replace；同一输入连续运行必须产生字节相同的 `.mmd` 和 README block。

`validate-agent-evaluation.py` 固定检查：contract schema、agent/path 引用、必需节点和状态边、README markers、`.mmd`/README 一致性、determinism、runtime boundary 和 secret safety。它不调用 provider。

`compare-evaluations.py` 固定接受 `--contract PATH --current-best PATH --candidate PATH [--output PATH]`，只执行第 6.4 节规则，不运行 benchmark。

### 7.3 第一张图：产品 Agent 结构图

`agent-architecture.mmd` 至少包含：

- Human/user input 与产品 output；
- 产品 runtime 边界及真实的 identity、skills、knowledge、workflows、tools、memory policy；
- backend/provider/model 作为外部执行层，不是产品 identity；
- artifact、scrubbed trajectory、verifier/evidence 出口；
- development-only 的 contract、validation、benchmark 和 loop runner 与 runtime 的边界；
- current hewo 的真实 smoke 语义，及缺失/optional 内容的明确标记。

它回答“产品 Agent 是什么”，不回答“它如何被迭代”。

### 7.4 第二张图：产品优化 Loop 状态图

`agent-optimization-loop.mmd` 从固定状态 schema 和 contract 生成，至少包含：

- Human intent → contract → functional baseline → performance optimization 的阶段分界；
- `DESIGN_INCOMPLETE`、`FUNCTIONAL_BASELINE_MISSING`、`SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`、`ENVIRONMENT_BLOCKED`、`EVALUATION_BLOCKED`、`BASELINE_INVALIDATED`、`CANDIDATE_REJECTED`、`ACCEPTED_AS_CURRENT_BEST`、`STOPPED`；
- 每条关键转移的 guard、失败分类和不更新 best 的规则；
- current-best、revision identity、metric evidence 记录；
- self-bootstrap 子图：skill candidate 使用 fixed fixture/base evaluator，不能修改 evaluator 以降低门槛；
- hewo 当前停留在 smoke-only，而不是 performance accepted。

### 7.5 README 同步规则

README 使用每个图唯一的 marker 区间：

```markdown
<!-- BEGIN GENERATED: agent-architecture.mmd -->
```mermaid
...
```
<!-- END GENERATED: agent-architecture.mmd -->
```

另一个图使用对应 basename。生成器规则：

- README marker validator 必须逐项验证：每个 basename 恰有一个完整、非交叉的 begin/end 区间；begin/end 名称配对；managed block 的 Mermaid 内容与 canonical `.mmd` 字节相同；marker 外的 README 内容不被生成器改写；缺失、重复、交叉、错误名称、stale block 和 `.mmd` drift 都有固定负例。`--init-readme` 仅允许在两个 marker 都完全缺失且插入点明确时工作。
- README 同时提供 `.mmd` 源文件链接；
- 不生成 SVG/PNG，不引入在线 Mermaid 服务或额外渲染依赖。

## 8. 自举（skill 优化 skill）协议

### 8.1 自举对象、candidate manifest 与不可变 base evaluator

被优化对象是 `.agents/skills/agent-evaluation-loop-design/` 的 candidate，而不是 hewo runtime。每个 candidate 必须在实现前，把 manifest 提交到 **base commit**：

```json
{
  "schema_version": 1,
  "hypothesis": {
    "id": "readme-managed-block-sync",
    "statement": "Add deterministic README synchronization without creating a second source of truth"
  },
  "observable_delta": {
    "kind": "readme-managed-block-sync",
    "expected_artifacts": ["README.md", "agent-architecture.mmd", "agent-optimization-loop.mmd"],
    "required_assertions": ["markers-unique", "blocks-match-mmd", "check-mode-detects-drift"]
  },
  "allowed_candidate_paths": [
    ".agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py",
    ".agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py",
    "README.md",
    "AGENTS.md",
    "DEV.md",
    ".agents/workflows/agent-development.md",
    "benchmarks/README.md",
    "PLAN-agent-visualization-self-bootstrap.md",
    "agent-architecture.mmd",
    "agent-optimization-loop.mmd"
  ]
}
```

v1 只接受 base evaluator 实现的 allowlisted `observable_delta.kind`，未知 kind 返回 `DESIGN_INCOMPLETE`；manifest 声明不能自行新增评分逻辑。第一次真实自举以 C2 为 base、C3 为 candidate：C2 已包含 `readme-sync-candidate.json` 和 base evaluator，C3 才实现并应用 README managed-block sync。

官方 self-bootstrap CLI 固定为：

```text
--repo-root PATH
--base-ref COMMIT
--candidate-ref COMMIT
--candidate-root PATH
--candidate-manifest RELATIVE_PATH
[--output PATH]
```

`--output` 是外部 machine-readable execution report，不是计划文件；report 至少包含 schema version、base/candidate full SHA、base/candidate tree SHA、requested/observed HEAD、candidate worktree path digest、base archive manifest SHA、candidate manifest SHA、protected-path diff、每个 gate 的 state/reason/exit code、开始/结束阶段和 cleanup result。report 只能写入显式的 non-symlink path，使用临时文件加原子 replace；stdout 同时输出同一 JSON，便于 CI/issue artifact 收集。

执行前置条件：

1. `base_ref` 与 `candidate_ref` 都必须解析为 commit，且不能相同；
2. `base_ref` 必须是 `candidate_ref` 的祖先；
3. `candidate_root` 必须是位于 `candidate_ref` 的独立 clean detached worktree，`git status --porcelain=v1 --untracked-files=all`、unstaged diff 和 staged diff 都为空；`git rev-parse --show-toplevel` 的 realpath 必须与传入 candidate root 一致，`HEAD` 必须等于 candidate SHA；
4. `candidate_root`、repo root、base archive、fixture copy、output/report root 和所有 manifest/result/evidence path 必须经过 lexical + `realpath` 校验；v1 拒绝 symlinked worktree roots、输入文件和 protected directories，禁止越出声明的 root；
5. candidate manifest 的相对路径必须存在于 base snapshot，且从 base 读取，不从 candidate 读取；manifest 的 allowlist 不能包含 evaluator、fixture、result-case、contract 或 report paths；
6. candidate 相对 base 对 protected evaluator/fixture/result-case 路径的 tracked 变更直接 `BLOCKED`；clean-worktree gate 同时拒绝 candidate 的 untracked protected files；allowlisted candidate paths 之外的 tracked/untracked repository change 也直接 `BLOCKED`；
7. evaluator 运行前记录 candidate `HEAD`、index/worktree status、base archive manifest 和 protected path hashes；运行后再次采集并要求 candidate `HEAD`、index、protected hashes、base archive hashes 未漂移，除预声明 allowlist 和 disposable output 外不得有写入。

base evaluator 的隔离规则：

1. 通过 `git archive <base_ref>` 把 base skill evaluator、base comparator、fixtures、expected invariants、result cases 和 candidate manifest 解包到新的 `0700` 临时目录；归档内容以 canonical path list + SHA-256 manifest 固定，禁止 archive 内 symlink/hardlink 逃逸；
2. 生成 SHA-256 manifest 并把 base snapshot 设为只读；运行后重新从 Git object 校验全部 hash；任何 pre/post 漂移都为 `BLOCKED`，不能用 candidate 输出覆盖或修复 base snapshot；
3. fixed comparator cases **只运行 base snapshot 的 comparator**，从不运行 candidate comparator；base comparator 的 executable/script hash 在运行前后必须相同；
4. candidate generator/validator 只接收 disposable fixture copy、candidate worktree 和独立 writable output dir；base expected results 不作为 writable candidate 输入；所有 subprocess 的 `cwd`、`HOME`、`TMPDIR` 和 output root 显式指向 disposable roots；
5. base evaluator 独立检查 candidate 输出，不接受 candidate validator 的“pass”作为唯一证据；它重新解析 README markers、manifest、result、evidence 和 Git diff；
6. 全部临时 worktree/output 在结果消费后清理；cleanup 失败写入 report 并使 self-bootstrap 为 `BLOCKED`，不能静默忽略。

这套机制防止普通 candidate 通过同一变更放宽 evaluator/fixture；它不是恶意代码的 OS sandbox。Git diff 和 output-root checks 只约束声明的 repository/output 边界，不能声称阻止任意恶意进程访问 host 的其他资源。未经 code review 的不可信 candidate 不应在 host 上执行；若需要对抗恶意代码，必须另行使用只读 container sandbox，不在本计划中假装提供该安全保证。

### 8.2 固定自举 baseline、真实 candidate 与负例

base evaluator 至少验证：

1. `paper-agent` 完整 fixture 生成 architecture 和 optimization 图；
2. 图包含所有固定必需节点、边和边界；
3. 缺 contract/缺 current best 场景产生 `DESIGN_INCOMPLETE` 或 `FUNCTIONAL_BASELINE_MISSING`；
4. 完全相同输入重复生成字节相同；
5. README markers 与 `.mmd` 内容一致；
6. 不写入任何 runtime 目录，不读取或输出 secrets；
7. base comparator 对 fixed results 分别产生 `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`、`CANDIDATE_REJECTED`、`ENVIRONMENT_BLOCKED`、`EVALUATION_BLOCKED` 和 `BASELINE_INVALIDATED`；额外覆盖 `GENERALIZATION_REQUIRED`、`FUNCTIONAL_BASELINE_MISSING` 和 `DESIGN_INCOMPLETE`，不把 recommendation 当作已 promotion；
8. known-bad mutation（删必需状态、放宽 candidate comparator、改 expected invariant、加入 untracked protected file）被拒绝或 block；
9. C3 candidate 相对 C2 base 是不同、clean、祖先关系正确的 revision，并满足 base 中预先声明的 `readme-managed-block-sync` observable delta。

当前实现不声称 hewo 已获得产品性能提升。它只用 C2→C3 的真实 skill/repository capability delta 证明自举协议可以区分 baseline 和 candidate；是否把 C3 接受为新的 skill best 仍需 human 审核可读性、简洁性和设计价值。

### 8.3 自举接受/拒绝

```text
SKILL_BASELINE_COMMITTED_WITH_CANDIDATE_MANIFEST
  → DISTINCT_CLEAN_CANDIDATE_COMMIT
  → RUN_BASE_EVALUATOR_ON_CANDIDATE
  → STATIC_AND_DETERMINISM_CHECK
  → CHECK_PREDECLARED_OBSERVABLE_DELTA
       ├─ refs equal/not ancestor/dirty worktree → BLOCKED
       ├─ evaluator/fixture/result case changed  → BLOCKED
       ├─ required invariant lost                → REJECTED
       ├─ no declared/observable delta           → REJECTED
       ├─ evaluator unavailable                  → BLOCKED
       └─ invariants preserved + delta observed  → HUMAN_REVIEW
                                                     ├─ reject → previous skill best
                                                     └─ accept → new skill best
```

机器 gate 只判断 refs、protected inputs、结构、确定性、边界、fixed outcomes 和预先声明的可观察 delta；human 对可读性、简洁性、误导风险和是否真的帮助开发者保留最终否决权。

## 9. 工作分解与提交边界

每个 C 都是可独立 review/回滚的提交；任何引入新 tracked path 的 C 都必须在同一 C 更新 registry，并运行 registry gate。

### C0 — 本计划

- 建立本文件，记录用户目标、当前状态、panel findings、契约、文件图和开放问题。
- **Gate**：用户 review；用户重新确认 `对齐完成/aligned` 后才进入实现。

### C1 — Normative contract、完整 fixture、candidate manifest 与 registry

- 创建 skill 根目录及所有必要 scoped `AGENTS.md`；
- 创建 `SKILL.md` 与三个 references，明确 product/development boundary、两阶段生命周期、condition identity、result/evidence schema、comparator precedence 和 self-bootstrap protocol；
- 创建 `paper-agent` 完整最小 runtime tree、performance contract、expected invariants、共享 evidence artifact，以及 current-best/accepted/rejected/environment-blocked/evaluation-blocked/invalidated 固定 results；
- 在 base 中预先提交 `readme-sync-candidate.json`，把 C3 的 hypothesis、observable delta 和 allowed paths 固定下来；
- 创建 `src/hewo/development/AGENTS.md` 与 hewo 的 smoke-only contract；
- 在同一 commit 更新 `.agents/template-content-registry.json`，预先覆盖 skill、fixture、hewo development 和根目录 `agent-*.mmd`，并固定 selective/template-only-or-adapt 规则。
- **Gate**：所有 JSON 示例可由标准库解析；result/evidence fixture 中引用的相对路径存在且 hash 正确；`git diff --check`；`python3 scripts/check-template-registry.py`；secret/user-level/private-path grep clean。

### C2 — 可生成图的 baseline skill、validator、base comparator 与 evaluator

- 实现 generator 的 deterministic `.mmd` 生成和 `--no-readme` 路径；README managed-block 写入作为 C3 预先声明的 candidate delta，C2 baseline 不实现该 delta；
- 实现 validator 的 contract/path/state/determinism/runtime-boundary 检查；
- 实现 **base** `compare-evaluations.py`：分离 subject revision/condition identity，按第 6.3.2/6.4 节校验 condition manifest、current-best validity、samples、mean、safe evidence path/hash、approved producer、failure taxonomy、generalization state、状态 precedence 和退出码；
- 实现 `self-bootstrap-check.py` 的 refs/ancestry/pre-post clean-worktree/base-archive/protected-path/safe-realpath/restricted-output/base-comparator 机制；
- 固定退出码：`0=CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`，`10=CANDIDATE_REJECTED`，`20=DESIGN_INCOMPLETE|FUNCTIONAL_BASELINE_MISSING|SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`，`30=BASELINE_INVALIDATED`，`40=ENVIRONMENT_BLOCKED`，`41=EVALUATION_BLOCKED`，`42=GENERALIZATION_REQUIRED`，`2=CLI/schema malformed`；JSON `state` 字段区分同一 exit-code family，promotion 后的 `ACCEPTED_AS_CURRENT_BEST` 不由 comparator 写回。
- **Gate**：`python3 -m py_compile`；在 C1 fixture 上两次生成相同 `.mmd` hash；strict validator pass；base comparator 的 fixed outcomes 全部匹配；self-bootstrap 对 equal refs、dirty candidate 和 protected mutation 返回 BLOCKED；registry gate 通过。
- C2/C3 提交完成后由外部 execution report（CI artifact/GitHub issue 或 non-Git evidence JSON）记录 `SELF_BOOTSTRAP_BASE_REF`、`SELF_BOOTSTRAP_CANDIDATE_REF`、命令、结果和 SHA-256；不得在提交之后回写/修改计划文件来记录自身 commit SHA，也不得用移动的 branch 名代替完整 SHA。

### C3 — 真实 self-bootstrap candidate：README sync、hewo 图与开发规范

- 以 C2 commit 为 immutable base，在 C3 实现 candidate manifest 预先声明的 README managed-block capability：为 generator/validator 增加 `--readme`、`--init-readme`、README-aware `--check`；
- 生成根目录两个 hewo `.mmd`，将其同步到 README 唯一 generated blocks，并加入源文件链接；
- 修改 `AGENTS.md`、`DEV.md`、`.agents/workflows/agent-development.md`、`benchmarks/README.md`，明确先 functional baseline 后 performance、condition identity、失败分类、benchmark anti-hack 和 hewo smoke-only 限制；
- 明确 `run-agent-loop.sh` 是 stage runner，comparator 是薄协议，不声称已实现自动 optimizer；
- C3 commit SHA 由同一外部 execution report 记录；C2 必须是其祖先且二者不同，计划文件在 commit 后保持不变。
- **Gate**：generator `--check` 无 drift；README markers 唯一且非交叉；`.mmd` 与 blocks 字节一致；缺失、重复、交叉、错误 basename、stale block 的固定负例均非零；strict hewo validator 返回 0 且 JSON state 为 `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`；`--require-performance` 对 hewo 非零；registry/diff gates 通过。

### C4 — 独立 candidate worktree 自举验证与 final boundary audit

- 从外部 execution report 读取 `SELF_BOOTSTRAP_BASE_REF`/`SELF_BOOTSTRAP_CANDIDATE_REF`，并由 candidate SHA 创建 clean detached candidate worktree；通过 `git archive` 从 base SHA 提取只读 base evaluator/comparator/fixture；
- 使用 base 中的 `readme-sync-candidate.json` 运行 self-bootstrap，验证 distinct refs、ancestry、candidate HEAD 与 requested SHA、运行前后 clean 状态、allowlisted diff、protected tracked/untracked paths、safe-realpath、restricted writable outputs、base manifest pre/post hash、fixed comparator outcomes、determinism、README sync、runtime boundary 和 secret scan；
- 运行 deliberate negative cases：equal refs、not-ancestor、wrong/detached HEAD、dirty worktree、运行中/运行后污染、out-of-allowlist tracked change、untracked protected path、candidate comparator mutation、symlink/path escape、missing evidence、wrong hash、wrong repetition count、invalid current best、missing/drifted condition manifest、changed condition identity、generalization missing holdout，以及 README missing/duplicate/crossed/wrong-name/stale markers；
- 运行 template release-readiness audit，构建 fresh release archive，并以 `--release` 再审计/检查 archive，确认 skill、fixture、development contract、AGENTS.md 和根目录图不进入产品 payload；
- **Gate**：self-bootstrap machine result 为 `HUMAN_REVIEW` 且 observable delta `readme-managed-block-sync` 已证实；所有负例得到预期 blocked/rejected/invalidated state；全部 repository/release gates 通过；human 完成两图可读性与是否误导的最终 review。

## 10. 文件地图

### 计划新增

- `PLAN-agent-visualization-self-bootstrap.md`（本文件；merge 后按流程删除）
- `.agents/skills/agent-evaluation-loop-design/AGENTS.md`
- `.agents/skills/agent-evaluation-loop-design/SKILL.md`
- `.agents/skills/agent-evaluation-loop-design/references/AGENTS.md`
- `.agents/skills/agent-evaluation-loop-design/references/agent-architecture-schema.md`
- `.agents/skills/agent-evaluation-loop-design/references/evaluation-contract.md`
- `.agents/skills/agent-evaluation-loop-design/references/self-bootstrap.md`
- `.agents/skills/agent-evaluation-loop-design/scripts/AGENTS.md`
- `.agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py`
- `.agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py`
- `.agents/skills/agent-evaluation-loop-design/scripts/compare-evaluations.py`
- `.agents/skills/agent-evaluation-loop-design/scripts/self-bootstrap-check.py`
- `.agents/skills/agent-evaluation-loop-design/fixtures/AGENTS.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/AGENTS.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/agent.yaml`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/development/AGENTS.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/development/evaluation-contract.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/runtime/identity.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/runtime/memory-policy.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/runtime/knowledge/README.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/runtime/skills/paper-writing/SKILL.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/runtime/workflows/write-paper.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/runtime/tools/README.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/expected-invariants.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/AGENTS.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/readme-sync-candidate.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/current-best-result.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/accepted-candidate-result.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/rejected-candidate-result.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/environment-blocked-candidate-result.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/evaluation-blocked-candidate-result.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/invalidated-candidate-result.json`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/evidence/AGENTS.md`
- `.agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/evidence/artifact.txt`
- `src/hewo/development/AGENTS.md`
- `src/hewo/development/evaluation-contract.json`
- `agent-architecture.mmd`（生成）
- `agent-optimization-loop.mmd`（生成）

### 计划修改

- `README.md`
- `AGENTS.md`
- `DEV.md`
- `.agents/workflows/agent-development.md`
- `benchmarks/README.md`
- `.agents/template-content-registry.json`

### 明确不修改

- `src/hewo/runtime/**`（产品行为）
- `scripts/run-agent-loop.sh` 的自动调优/后台状态实现
- 现有 provider/auth 文件和任何用户级 skill/memory
- `USER.md`（除非用户另行要求）
- 已存在的 `PLAN.md`

## 11. 验收标准

### 11.1 可视化和 README

- [ ] 一个 documented command 能从仓库根目录生成两个 `.mmd` 并同步 README，不需手工补图。
- [ ] `agent-architecture.mmd` 反映 hewo 的实际 runtime 文件和产品/开发边界，不凭空添加能力。
- [ ] `agent-optimization-loop.mmd` 是状态机，不是线性 checklist；包含 baseline、candidate、current best、identity invalidation、benchmark acceptance recommendation、generalization gate、接受、拒绝、环境阻塞、评估阻塞、回滚/重试和停止路径。
- [ ] README 含两个唯一 generated blocks 和两个 `.mmd` 链接；`--check` 能检测 drift；README 不存在第二份 source of truth。
- [ ] hewo 图明确显示 `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`，没有虚构 quality metric 或 performance improvement。

### 11.2 coding agent 的设计约束

- [ ] `SKILL.md` 要求 coding agent 在优化前定义 product goal、functional contract、functional baseline、benchmark identity、运行环境、primary/secondary metrics、阈值、回归规则、重复次数和停止条件，并区分 benchmark-local acceptance 与 product-general claim。
- [ ] 缺少 contract、metric 或 baseline 时，validator 输出明确的 `DESIGN_INCOMPLETE` 或 `FUNCTIONAL_BASELINE_MISSING`，不允许直接报告性能优化成功。
- [ ] result 的 `subject.definition_revision` 与 `condition_identity` 分离；不同产品 revision 可以在相同评估条件下比较，评估条件变化才使 baseline invalidated。
- [ ] comparator 校验 run-status taxonomy、样本数量、mean 重算、evidence kinds/path/hash/producer provenance；环境失败与 benchmark/verifier/evidence 失败分别输出 `ENVIRONMENT_BLOCKED` 与 `EVALUATION_BLOCKED`。
- [ ] comparator 能区分 `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`、`ACCEPTED_AS_CURRENT_BEST`、`CANDIDATE_REJECTED`、`ENVIRONMENT_BLOCKED`、`EVALUATION_BLOCKED`、`BASELINE_INVALIDATED`、`GENERALIZATION_REQUIRED`、`FUNCTIONAL_BASELINE_MISSING` 和 `DESIGN_INCOMPLETE`，且不自动修改 best；`ACCEPTED_AS_CURRENT_BEST` 需要显式 promotion gate。
- [ ] condition manifest 覆盖所有 run-affecting inputs，含 task input/verifier source hash、image/tool/request/sampling/retry/timeout/default locale/timezone/seed；result projection/hash 与 manifest 一致，缺失或未表达的输入产生 `EVALUATION_BLOCKED`。
- [ ] comparator 对 evidence 使用 lexical + safe-realpath 检查，拒绝绝对路径、`..`、symlink/path escape，并验证 approved producer metadata；报告明确不构成远程 attestation。
- [ ] benchmark-local acceptance 不被表述为 product-general improvement；product-general claim 缺独立 holdout/canary 或 human/domain review 时为 `GENERALIZATION_REQUIRED`。
- [ ] 文档明确区分产品功能失败、基础设施/provider 失败、benchmark/verifier 失败和真正产品质量回归。
- [ ] 文档禁止 benchmark-specific hack、修改 verifier 掩盖失败、修改 metric policy 偷换比较标准，以及把一次 provider response 当成改进。
- [ ] README 有缺失、重复、交叉、错误 basename、stale block 和 drift 的固定负例；`--check` 对每种负例非零，`--init-readme` 不能绕过损坏 marker。
- [ ] 文档明确现有 `run-agent-loop.sh` 是 stage runner，不是已完成的自动性能优化器。

### 11.3 自举

- [ ] skill 有固定完整 fixture、expected invariants、known-bad mutation 和 accepted/rejected/blocked/invalidated result cases。
- [ ] self-bootstrap evaluator 从只读 base Git archive 读取 evaluator、base comparator、fixture、expected invariants、candidate manifest 和 fixed result cases，不信任 candidate 修改后的评分器。
- [ ] candidate manifest 的 allowlist、protected paths、writable roots 和 external report schema 在 base 中预先固定，candidate 不能通过修改 manifest 扩权；manifest 路径/内容经过 safe-realpath 和 canonical hash 校验。
- [ ] self-bootstrap 覆盖结构、引用一致性、字节级确定性、README sync、runtime boundary、secret safety、base manifest pre/post hash 和固定 comparator outcomes。
- [ ] self-bootstrap 在 candidate worktree 中运行前后都验证 `HEAD`/base refs、cleanliness、detached 状态、candidate allowed-path diff 和 protected tracked/untracked paths；所有 Git/path 读取使用 safe-realpath，输出目录限制为独立 writable temp root；base archive 目录不可由 candidate 写入。
- [ ] protected evaluator/fixture/result case 的 tracked/untracked diff 会被 block；放宽 candidate comparator、删除 invariant、修改 expected output 或污染 protected path 的 known-bad candidate 不得通过。
- [ ] self-bootstrap 使用外部 execution report 记录 base/candidate full SHA、observed HEAD/tree/status、condition/base archive hashes、每个 gate 结果和 cleanup；计划文件不在 commit 后被回写。

### 11.4 安全、复用与边界

- [ ] 新 skill 和 contract 位于 development-only 区域，不进入产品 runtime/release；所有新增 source directories 有 scoped `AGENTS.md`。
- [ ] downstream 可选择性复制 skill，但必须重新生成图、contract、Agent 名称、benchmark、identity 和 evidence 路径；当前 hewo 图不作为 downstream 产品事实。
- [ ] registry 覆盖所有新增 tracked paths，且每个引入新路径的 C 都运行 `check-template-registry.py`。
- [ ] template release-readiness audit 和 archive inspection 证明不会泄露 AGENTS.md、skill evaluator、fixture、contract、auth store、raw session 或个人数据。
- [ ] generator/validator/comparator 不依赖 user-level skill、Harbor source、在线模型服务或 provider credentials。

## 12. 验证命令

实现后至少运行：

```bash
# Python syntax
python3 -m py_compile \
  .agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py \
  .agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py \
  .agents/skills/agent-evaluation-loop-design/scripts/compare-evaluations.py \
  .agents/skills/agent-evaluation-loop-design/scripts/self-bootstrap-check.py

# Generate current hewo diagrams and README
python3 .agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py \
  --agent hewo --repo-root . --output-dir . --readme README.md
python3 .agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py \
  --agent hewo --repo-root . --output-dir . --readme README.md --strict

# Generate and validate the fixed paper-agent fixture without touching README
python3 .agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py \
  --agent paper-agent \
  --agent-root .agents/skills/agent-evaluation-loop-design/fixtures/paper-agent \
  --output-dir /tmp/agent-evaluation-fixture \
  --no-readme
python3 .agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py \
  --agent-root .agents/skills/agent-evaluation-loop-design/fixtures/paper-agent \
  --output-dir /tmp/agent-evaluation-fixture \
  --expected .agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/expected-invariants.json \
  --strict

# Fixed comparator outcomes
python3 .agents/skills/agent-evaluation-loop-design/scripts/compare-evaluations.py \
  --contract .agents/skills/agent-evaluation-loop-design/fixtures/paper-agent/development/evaluation-contract.json \
  --current-best .agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/current-best-result.json \
  --candidate .agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/accepted-candidate-result.json
# Repeat with rejected-candidate-result.json, environment-blocked-candidate-result.json,
# evaluation-blocked-candidate-result.json and invalidated-candidate-result.json;
# assert the machine-readable states and documented exit codes.

# Protected self-bootstrap: use distinct immutable base/candidate refs.
# SELF_BOOTSTRAP_BASE_REF is the full C2 commit SHA; SELF_BOOTSTRAP_CANDIDATE_REF
# is the full C3 commit SHA and must be a descendant in a clean detached worktree.
python3 .agents/skills/agent-evaluation-loop-design/scripts/self-bootstrap-check.py \
  --repo-root . \
  --base-ref "$SELF_BOOTSTRAP_BASE_REF" \
  --candidate-ref "$SELF_BOOTSTRAP_CANDIDATE_REF" \
  --candidate-root /tmp/agent-evaluation-candidate \
  --candidate-manifest .agents/skills/agent-evaluation-loop-design/fixtures/self-bootstrap/readme-sync-candidate.json

# Repository gates
./scripts/validate-definition.sh hewo
python3 scripts/check-template-registry.py
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent hewo --strict
python3 .agents/skills/template-release-readiness/scripts/audit_template_release.py --agent hewo
git diff --check
```

`--strict` 的设计状态语义必须写入 skill：没有明确 provider credential source 的运行只能是 `infrastructure-only` 或 `blocked`，不能报告产品 Agent 行为或性能提升。真正 provider-backed E2E 仍只能通过 `docker/run-hewo-e2e.sh`/下游等价 helper，并报告 backend、provider、model 和 credential-source flag；本 skill 的静态自举默认不需要 provider。

## 13. 风险与开放问题

1. **输出目录**：根目录 `.mmd` 最容易被 human 发现，但会增加根目录生成文件；如果用户偏好 `visualizations/`，需在实现前改为单一 canonical path。
2. **contract 位置**：本版本已提议 canonical `src/<agent>/development/evaluation-contract.json`；如果 downstream 不希望 contract 随 agent source 走，必须在用户 review 中选择一个替代路径，不能实现时临时双写。
3. **指标与人工评分**：真实产品可能需要人工评分或多次 provider 运行；v1 只固定 schema、identity 和比较规则，不替产品 human 选择领域指标。
4. **自举“改善”定义**：结构/确定性/边界可自动检查，是否更易理解仍需 human；candidate 必须在 base fixture 上声明一个可观察 delta，不能用文本长度或模型偏好替代。
5. **revision discipline**：contract/benchmark/verifier/metric policy 语义变化必须更新 revision 并重新 baseline；脚本可机械检查 identity，但不能替 human 判断 revision 是否诚实。
6. **当前 hewo 的定位**：hewo smoke contract 只能演示 design/infrastructure 状态，不能证明复杂产品优化 Loop 的领域有效性。
7. **后台长任务**：现有文档提到的 registered background mode 仍不是本计划的实现范围；若要实现注册、恢复、清理，应另立计划，不能把本 comparator 当作后台系统。
8. **README 渲染器差异**：GitHub Mermaid 可渲染，其他 Markdown renderer 可能只显示代码；v1 不引入 SVG/PNG 依赖，human review 需接受这一限制。
9. **计划文件冲突**：已有 `PLAN.md` 属于历史 machine-profile 工作；本计划使用 slug 文件，merge 后只删除本计划，不删除旧计划。

## 14. Reviewer dispositions

Panel 使用：

- feasibility 首席 `openai-codex/gpt-6-astra/high` 两次因 provider overload 失败；按 provider table fallback 到 `openai-codex/gpt-5.6-sol/high`，完成 feasibility review。
- risk 首席 `openai-codex/gpt-5.6-sol/xhigh`，完成 risk review。
- 两席均为只读，无文件修改；以下逐条记录全部 findings。

| Finding | Reviewer tag | Severity | Disposition | Rationale |
| --- | --- | --- | --- | --- |
| risk-001 | sol/xhigh | high | adopted | 增加 normative contract v1、字段类型/枚举/错误状态和 validator schema gate。 |
| risk-002 | sol/xhigh | high | adopted | 增加完整 result identity tuple、contract sha、baseline invalidation 状态和 exact-match comparator。 |
| risk-003 | sol/xhigh | high | adopted | 增加 base-snapshot evaluator、protected paths、known-bad mutation 和固定 outcome cases；human review 保留。 |
| risk-004 | sol/xhigh | high | adopted | 将 registry 更新前移至 C1，并要求每个引入 tracked path 的 C 都运行 registry gate。 |
| risk-005 | sol/xhigh | high | adopted | 为 hewo 增加显式 smoke-only contract，并区分 smoke render、design-incomplete 和 performance-ready 状态。 |
| risk-006 | sol/xhigh | high | adopted | 增加最小 result schema/comparator，明确本计划不实现 full optimizer，避免只画图不具备固定比较协议。 |
| risk-007 | sol/xhigh | medium | adopted | 将计划状态更新为 panel-reviewed/revised，并在 alignment log 记录 digest 失效和重新确认要求。 |
| risk-008 | sol/xhigh | medium | adopted | 使用现有 `template-only-or-adapt` 类别，增加 release-readiness/archive verification；不引入不存在的 registry class。 |
| risk-009 | sol/xhigh | medium | adapted | v1 固定 CLI/path precedence，并让完整 fixture 提供真实 runtime tree；不额外引入第二份 architecture manifest，避免 source duplication。 |
| feasibility-001 | sol/high fallback | medium | adopted | 更新 status、C0 和 alignment record，明确 panel findings 后必须重新 user-align。 |
| feasibility-002 | sol/high fallback | high | adopted | 将完整 fixture scaffold 放入 C1，C2 的 gate 不再依赖尚未创建的文件。 |
| feasibility-003 | sol/high fallback | high | adopted | registry patterns/entries 随 C1 提前加入并逐 C 验证，不延迟到末尾。 |
| feasibility-004 | sol/high fallback | medium | adopted | 文件地图增加 root/references/scripts/fixtures/development 各 scoped `AGENTS.md`，并在 release audit 检查排除。 |
| feasibility-005 | sol/high fallback | high | adopted | fixture 增加完整最小 runtime tree；generator 只扫描真实路径，不凭空生成虚拟产品组件。 |
| feasibility-006 | sol/high fallback | high | adopted | 固定 `--repo-root/--agent-root/--contract/--output-dir/--readme/--check` 语义、默认值和相对路径规则。 |
| feasibility-007 | sol/high fallback | high | adopted | 重新排序为 C2 先生成能力、C3 再集成 README，避免 `--check` 在图尚未存在时失败。 |
| feasibility-008 | sol/high fallback | high | adopted | 增加可执行 self-bootstrap protocol、base evaluator 和 accepted/rejected/blocked/invalidated cases；不声称当前 hewo 已完成 skill performance gain。 |
| feasibility-009 | sol/high fallback | high | adopted | evaluator/fixture 从 base detached worktree 读取，candidate 对 protected paths 的 diff 直接 block。 |
| feasibility-010 | sol/high fallback | medium | adopted | 明确 smoke-only、missing contract、invalid contract、missing baseline 的状态和 strict/non-strict 语义。 |
| feasibility-011 | sol/high fallback | medium | adopted | C4 增加 template-release-readiness audit 和 archive inspection，覆盖 development-only 文件边界。 |
| risk-010 | sol/xhigh final | critical | adopted | 将 `subject.definition_revision` 从 exact-match identity 移出；只比较固定 `condition_identity`，允许不同产品 revision 成为 candidate/current best。 |
| risk-011 | sol/xhigh final | high | adopted | 增加 run-status/failure taxonomy、按 samples 重算 aggregation、重复次数校验、evidence kinds/path/hash/producer provenance 和固定 classification precedence。 |
| risk-013 | sol/xhigh final | high | adopted | base evaluator、base comparator、fixture 和 fixed cases 从只读 Git archive 执行；加入 base manifest pre/post hash、protected tracked/untracked path 检查，candidate 不运行自己的 comparator。 |
| feasibility-012 | sol/high fallback final | high | adopted | 将 self-bootstrap CLI 改为 distinct `base-ref`/`candidate-ref`/`candidate-root`，要求 commit refs、祖先关系、clean detached worktree，并把 C2/C3 SHA 写入执行记录。 |
| feasibility-013 | sol/high fallback final | medium | adopted | 增加 base 提交中的 candidate manifest schema，包含 hypothesis、observable-delta kind、expected artifacts、assertions 和 allowlisted candidate paths。 |

## 15. Unit execution log

| Commit | Status |
| --- | --- |
| C0 | plan authored → user aligned → panel reviewed → revised → user re-aligned → final panel reviewed → revised → user re-aligned; closure panel pending |
| C1 | pending closure panel |
| C2 | pending closure panel |
| C3 | pending closure panel |
| C4 | pending closure panel |

## 16. 对齐与评审记录

### Round 0 — 用户提出需求

- **用户输入**：先建立计划供 review；需要两个产品/Loop `.mmd`，由 skill 自动生成并插入 README；Loop 要教会 development coding agent 设计简单固定的产品优化状态机；当前 hewo 很简单；skill 本身也要能够通过 Loop 自举优化。
- **计划变更**：建立初版计划，加入产品/开发身份边界、功能 baseline 与性能优化的阶段分离、状态机、README generated blocks、hewo smoke-only 处理和自举 fixture/validator。

### Round 1 — 用户确认初版对齐

- **用户输入**：`对齐完成`。
- **执行**：记录初始 alignment digest `8acd732f706aa3ffec0efbc2dd8c336c841d109a387de56d567c213e84a21057`，启动 L3 panel。

### Round 2 — Panel findings 与计划修订

- **Panel 输入**：feasibility 和 risk reviewers 均认为方向正确但 `needs-attention`；主要问题是 schema 不够规范、baseline 失效未机械化、自举 evaluator 可被 candidate 修改、registry/fixture/README commit 顺序不可独立执行、hewo 状态不唯一，以及没有最小可执行 comparator。
- **本轮计划变更**：采用第 4.2、6.3、6.4、8 节的补强；把工作拆分为 C1 contract/fixture/registry、C2 generator/validator/comparator、C3 README/开发规范、C4 protected self-bootstrap/final audit；增加所有 scoped `AGENTS.md`、明确 CLI/path precedence、smoke-only 状态语义和 release boundary gate。
- **当前请求**：请 review 本修订版，尤其确认：
  1. 是否接受 canonical contract 路径 `src/<agent>/development/evaluation-contract.json`；
  2. 是否接受增加薄 comparator（不运行 benchmark、不自动修改 best）；
  3. 是否接受根目录两个 `.mmd`；
  4. 是否接受论文写作 fixture 仅作为抽象、自举 fixed evaluator 不使用 provider；
  5. 是否接受 C1–C4 的范围和所有新增 scoped `AGENTS.md`。
- **下一步规则**：本轮属于实质修订。请用户明确回复 `对齐完成`/`aligned` 后，才重新记录 digest、进行必要的最终 panel review，并开始实现；在此之前不修改实现文件。

### Round 5 — Final panel findings与计划修订

- **Panel 输入**：feasibility 发现原 self-bootstrap command 使用相同 `HEAD`/candidate，无法实际测试 candidate delta；risk 发现 `definition_revision` 被错误放入 exact-match identity，且 result 缺少 run/failure/sample/evidence integrity 规范，base comparator 隔离不足。
- **本轮计划变更**：拆分 `subject.definition_revision` 与 `condition_identity`；增加 `EVALUATION_BLOCKED`、run-status/failure taxonomy、sample mean 重算和 evidence manifest；固定 C2 为带 manifest/base evaluator 的 baseline、C3 为 distinct README-sync candidate；要求 immutable base archive、base comparator、clean detached candidate、不同 commit refs、祖先关系、protected tracked/untracked 检查。
### Round 6 — 用户重新确认最终修订版对齐

- **用户输入**：`对齐完成`。
- **执行**：记录本版 alignment digest，启动 closure panel，重点复核 `subject.definition_revision`/`condition_identity` 分离、result evidence taxonomy、C2 base 与 C3 candidate 的 distinct refs，以及 base evaluator 隔离。
- **边界**：closure panel 通过前不修改实现；如仍有实质 finding，则继续 disposition 并重新请求对齐。
