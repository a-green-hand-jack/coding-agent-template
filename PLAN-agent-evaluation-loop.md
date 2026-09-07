# 1. Title and status
- Plan id: `agent-evaluation-loop`
- Review state: **Approved**
- Scope: add a project-internal, product-external evaluation loop to the template so downstream developer repos can copy the pattern without inheriting product behavior, and update the developer-facing guidance (`AGENTS.md`, `DEV.md`, and related docs) so the loop is discoverable and safe to run for long tasks.

# 2. Motivation
现在仓库已经有验证、E2E、benchmark 和 smoke 的零散能力，但缺少一个明确的“外层 loop”：
- 先验证定义和边界，
- 再跑真实 provider-backed 任务，
- 再收集 benchmark / trace / artifact，
- 最后把失败结果带回修改产品定义。

这个 loop 必须留在项目内、产品外，作为 downstream dev repo 的可复用参考。目标不是再造一个 coding-agent runtime，而是把现有检查编成一个可重复的迭代闭环，让开发者能快速判断“这次改动是否真的更接近正确的产品 agent”。
同时，这个 loop 需要把长程验证当成常态：验证步骤应尽量后台化、可登记、可恢复、可清理，避免长任务阻塞 human 和 dev-coding-agent 的交互，也避免任务意外中断后丢失状态。

# 3. Verified current state
- `DEV.md:15-18, 28-58, 92-143, 216-220` 已明确 development agent / product agent 分离，Phase 0 禁止修改执行循环，并要求验证、审计和基础设施检查。
- `.agents/workflows/agent-development.md:1-13` 只有线性的开发流程，没有显式的闭环编排。
- `benchmarks/README.md:1-7` 已定义 benchmark 只测 capability/regression，不定义产品行为。
- `scripts/run-benchmark.sh:1-53` 已经把 provider-backed E2E、artifact verifier、trace scrub 和结果摘要串成一次运行。
- `docker/run-hewo-e2e.sh:22-257` 已经支持 backend/provider/model/credential 注入，并且无凭据时 fail-closed。
- `scripts/validate-definition.sh:1-25` 已有定义结构检查。
- `src/hewo/runtime/workflows/infrastructure-smoke.md:1-9` 与 `src/hewo/runtime/skills/runtime-smoke/SKILL.md:8-21` 已有最小安装 smoke 路径。

# 4. Pinned decisions and rejected alternatives
## Pinned decisions
- Loop 必须位于 `scripts/` 和 `.agents/`，不进入 `src/hewo/runtime/`。
- Loop 以“验证定义 -> 审计 -> 基础设施检查 -> provider-backed E2E -> benchmark/verifier -> scrubbed evidence -> 回写结论”为固定骨架；`scripts/run-benchmark.sh` 仍保持 provider-backed E2E / verifier / trace scrub 的单一实现，loop runner 只负责前置校验、调度和生命周期管理。
- Loop 输出必须显式记录 backend / provider / model / credential-source / artifact path / scrubbed trace path。
- 长程验证默认通过后台任务执行；必须有可查询的登记、状态更新和完成后清理机制。
- Loop 复用现有 backend 能力，不重新实现 model client、session manager、approval loop 或 tool loop。

## Rejected alternatives
- 把 loop 写进产品 runtime：会变成产品行为，违背边界。
- 只做 benchmark loop：会漏掉 definition validation、registry/consistency 和 clean-container gate。
- 新造一套模型调用或审批循环：重复 backend 能力，也不符合 reuse-first。
- 用无凭据 build/CLI startup 充当 E2E：只能算 infrastructure-only。

# 5. Non-goals
- 不修改 hewo 的产品 identity、skills、knowledge 或 workflows 语义。
- 不把 benchmark 变成产品 solver 或 grader hack。
- 不新增秘密、auth store、session dump、.env 或 raw provider output 到 Git。
- 不创建独立的 Agent 单元测试套件来替代真实 Docker E2E。
- 不把 template 的 development loop 强制写成唯一 downstream workflow；只提供可参考、可改写的范式。

# 6. Work breakdown
## C1 — 定义并文档化外层 loop
**Gate:** `python3 scripts/check-template-registry.py && git diff --check`
- 更新根 `AGENTS.md`，把开发 coding agent 的职责、loop 入口、边界和证据要求指向本次新增/修订的 workflow 与脚本。
- 更新 `DEV.md`，把“产品外的项目内 loop”单独写成一节，说明它的顺序、输入、输出、失败回流方式，并提醒何时该看 `AGENTS.md`、何时该看产品 runtime。
- 更新 `.agents/workflows/agent-development.md`，把现有线性流程提升为“闭环循环”：定义/验证/执行/度量/记录/回改；避免再引入第二份平行 loop 说明。
- 如有必要，轻微修订 `benchmarks/README.md`，明确 benchmark 是 loop 的一个 stage，不是整个 loop。
- 视需要同步修订 `README.md` / `USER.md` 中与验证、安装或 evidence 相关的段落，避免它们与新的 loop 叙述冲突。

## C2 — 实现可执行的 loop runner
**Gate:** `bash -n scripts/run-agent-loop.sh && ./scripts/run-agent-loop.sh --help`
- 新增 `scripts/run-agent-loop.sh`，作为项目内的外层编排入口。
- 该脚本按固定顺序调用现有能力，并使用其明确脚本入口：`./scripts/validate-definition.sh <agent>`、`python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent <agent> --strict`、`python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py --agent <agent>`、`./scripts/run-benchmark.sh <agent>`。
- 参数化 `agent/backend/provider/model/credential-source/workspace/task-file`，显式把 credential-source 映射到允许的安全注入方式；`--allow-unauthenticated` 必须作为独立模式存在，只能跳过 provider-backed 阶段并返回明确的 infrastructure-only 结果码。
- 需维护一张 backend/provider credential matrix：`opencode` 仅接受 `--auth-file` / `--api-key-env`，`codex` 仅接受 `--codex-auth-file` / `--api-key-env OPENAI_API_KEY`，`claude` 仅接受 `--claude-credentials-file` / `--claude-api-key-file`，`pi` 仅接受 `--pi-auth-file`；不匹配的组合必须在 spawn 前拒绝。
- 输出 machine-readable summary，至少包含 stage 结果、backend/provider/model、凭据来源、artifact 路径、trajectory/scrubbed 路径和最终判定；其中 provider-backed E2E、verifier 和 trace scrub 由 benchmark stage 负责，且 loop runner 只做前置校验、调度和生命周期管理。
- 如果缺少真实凭据注入或只跑到了 build/CLI startup，脚本必须失败退出，不允许伪装成 E2E 成功。

## C3 — 把长程验证改成后台登记式执行
**Gate:** `bash -n scripts/run-agent-loop.sh && git diff --check`
- 为 loop 增加后台执行约定：当验证预计耗时较长时，runner 不应阻塞前台交互，而应把验证任务提交为后台作业；前台模式仍保留短检查和发起入口。
- 新增一个轻量登记/追踪机制，状态根必须位于工作区内的非 Git 目录（mode 0700），用于记录：任务 id、stage、backend/provider/model、credential-source、开始时间、当前状态、结果摘要、artifact 路径、pid/owner、锁信息、命令摘要和清理状态。
- 登记/追踪必须使用原子写入与状态转换（queued -> running -> succeeded/failed/canceled/cleaned），并在恢复时校验 pid、启动时间和进程组，防止 PID reuse 误杀或覆盖并发运行。
- 提供配套的查询/收尾能力：能列出在跑任务、查询完成结果、在结果被消费后清除登记，并在崩溃、重复启动或中断后识别可恢复/可清理项，避免积压和遗忘；完成后要同时处理 registry 与 benchmark 产物引用，不得提前删除仍在使用的 artifact。
- 文档中明确说明哪些验证适合后台执行，哪些短检查仍保留前台同步执行；后台任务需说明其状态码、心跳/超时语义和何时算完成。
- 失败、超时、取消、中断重试都要在登记里可见，并且能被下次 loop 运行安全接续或清理；并定义原子状态转换，避免并发覆盖。

# 7. File map
- `AGENTS.md`
- `DEV.md`
- `.agents/workflows/agent-development.md`
- `README.md` / `USER.md`（only if validation or user-facing guidance needs alignment）
- `scripts/run-agent-loop.sh`（new）
- `benchmarks/README.md`（only if loop terminology needs one-line clarification）
- `.gitignore`（only if the background-job state root or run artifacts need explicit exclusion）

# 8. Acceptance criteria
- 仓库里存在一个清晰的、项目内但产品外的 loop 说明，且读者无需对话上下文就能理解其用途；开发者入口文档（`AGENTS.md`、`DEV.md`）会明确指向它。
- 存在一个可执行的 loop helper，能在一次调用里串起定义验证、审计、基础设施检查、provider-backed E2E、benchmark/verifier 和 trace scrub，并在长程验证时切换到可查询的后台作业模式。
- helper 的输出明确标注 backend / provider / model / credential-source，并给出 artifact 与 scrubbed trace 路径。
- helper 对无凭据运行保持 fail-closed；`--allow-unauthenticated` 只允许 infrastructure-only，并且不能产出 provider-backed E2E 的成功状态。
- 后台验证任务可被登记、查询、完成后清理，不会长期悬挂在状态里；崩溃恢复、并发启动和重复清理都能安全处理，并且不会误删仍被消费的 benchmark 产物。
- loop 文档不泄露产品 runtime 行为，也不把 benchmark 描述成产品定义；用户文档和开发文档之间的职责边界保持一致。

# 9. Verification
- `python3 scripts/check-template-registry.py`
- `./scripts/validate-definition.sh hewo`
- `python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent hewo --strict`
- `python3 .agents/skills/agent-infrastructure-health/scripts/check_infrastructure.py --agent hewo`
- `./scripts/run-agent-loop.sh --agent hewo --backend opencode --provider <real-provider> --model <real-model> --auth-file <read-only-auth> "..."`
- `./scripts/run-agent-loop.sh --allow-unauthenticated --agent hewo --backend opencode "..."` must return the explicit infrastructure-only path and skip provider-backed stages
- `./scripts/run-benchmark.sh hewo` with real injected provider credentials
- `./scripts/run-agent-loop.sh --status` / `--cleanup` or equivalent registry operations for background jobs, as defined by the implementation
- interrupt/restart/cleanup test commands defined by the implementation, covering atomic state transitions, PID reuse checks, and orphan recovery
- `git diff --check`

# 10. Risks and open items
- 不同 downstream repo 的 backend/provider matrix 可能不同，loop helper 需要保持参数化而不是写死默认值。
- Codex / Claude / pi 在某些主机上的 sandbox 限制可能影响完整 E2E，脚本应把这类失败清晰归类为 infrastructure-only 或 blocked。
- 长程后台验证如果没有统一登记/清理约定，容易形成“看不见的未完成任务”；需要把状态文件格式、锁语义、心跳/超时、进程组检查和清理语义设计得极其简单。
- 如果 loop helper 过度依赖 benchmark 例子，容易把 template smoke 误当成产品语义；文档需要持续强调边界。
- 需要决定是否在 helper 中直接调用 benchmark，还是只把 benchmark 作为可选 stage；当前计划默认把 benchmark 纳入 loop，但仍保持可重用，并避免复制 `scripts/run-benchmark.sh` 的内部 stage 逻辑。

# 11. Reviewer dispositions

| Finding | Reviewer(s) | Disposition | Rationale |
| --- | --- | --- | --- |
| feasibility-001 | astra | adopted | The plan now pins the exact Python script entrypoints and their exit-code contract. |
| feasibility-002 | astra | adapted | The plan now distinguishes foreground/background modes and ties registry output to benchmark artifacts; implementation still needs the process model. |
| feasibility-003 | astra | adopted | The plan now includes a backend/provider credential matrix and mismatch rejection. |
| risk-001 | sol | adopted | The plan now requires a non-Git 0700 state root, redaction boundary, and secret-bearing-output tests. |
| risk-002 | sol | adopted | The plan now specifies lease/process-group/start-time checks to avoid PID reuse and stale-lock damage. |
| risk-003 | sol | adopted | The plan now includes an allowlisted credential matrix and pre-spawn mismatch rejection. |
| alternatives-001 | 5.5 | rejected | The separate workflow file was removed; the existing workflow doc remains the single source of truth. |
| alternatives-002 | 5.5 | adopted | The plan now defines a single state-root/registry contract and explicit sync rules with benchmark outputs. |

# 12. Unit execution log
| Commit | Status |
| --- | --- |
| C0 | plan authored |
| C1 | implemented / gate-passed (`python3 scripts/check-template-registry.py && git diff --check`) / committed (a51d090) / pushed / acceptance-checked (pending) |
| C2 | implemented / gate-passed (`bash -n scripts/run-agent-loop.sh && bash -n scripts/run-benchmark.sh && ./scripts/run-agent-loop.sh --help`) / committed (ec6ae83) / pushed / acceptance-checked (pending) |
| C3 | pending |
