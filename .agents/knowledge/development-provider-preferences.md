# Development provider and model preferences

> **Role of this document**
> - **Audience:** development coding agents choosing a provider/model for this repository's Agent development and validation.
> - **Authority:** repository convention for default choices; runtime availability still wins.
> - **Tone:** practical defaults, not a provider contract.
> - **Language:** 中文（provider/model id 保留英文）。
> - **Contains:** preferred supplier/model choices for development, validation, comparison, and Claude Code use.
> - **Excludes:** credentials, key values, auth payloads, and product-Agent behavior.

这些偏好是为了避免每次开发或测试 hewo / downstream Agent 时重新询问“该用哪个供应商和模型”。它们只约束**开发 coding agent 的验证选择**，不写入产品 runtime，也不代表下游用户必须有同样的供应商。

## 总规则

1. 先加载 `.agents/skills/development-provider-usage/SKILL.md`，主动确认当前机器实际可见的 provider/model。
2. 产品行为证据只走 pi + repository E2E helper；OpenCode、Claude Code、Codex 的 provider 只能作为开发诊断或开发代理自身的执行环境，不替代产品 E2E。
3. 优先用明确的 `provider/model`；不要依赖 CLI 默认值来生成验收证据。
4. 如果首选 provider/model 不可见、限额、维护中或返回 5xx，按下面 fallback 选择；报告里标明实际使用的 provider/model 和 blocker。
5. 不要为了通过一次测试而把偏好写进 `src/hewo/runtime/`。provider/model 是开发与运行时注入层，不是产品行为。

## Product Agent E2E 默认偏好（pi）

用于 `docker/run-hewo-e2e.sh`、`.agents/scripts/run-agent-loop.sh` 和需要声明 `agent-behavior` 的验证。

| 场景 | 首选 | 备选 | 说明 |
| --- | --- | --- | --- |
| 默认产品行为验收 | `apex/gpt-6-astra` | `apex/gpt-5.6-sol` | 优先选择稳定的 pi provider 和强模型；首选不可用时降级到同供应商较稳定模型。 |
| 快速 infrastructure smoke | `apex/gpt-5.6-sol` | `apex/gpt-6-astra` | 只验证管线时优先快和稳；仍需真实 provider 才能超过 infrastructure-only。 |
| DeepSeek 视角复核 | `apex-deepseek/deepseek-v4-pro` | `apex-deepseek/deepseek-v4-flash` | 用于检查 GPT 供应商偏差或中文/代码问题；不要替代默认验收，除非任务明确要求 DeepSeek。 |
| 多模态/图片输入验证 | `apex/gpt-6-astra` | `apex/gpt-5.6-sol` | 先用已声明 image input 的 GPT provider；需要 router 特定模型时再用 GravArc。 |
| Router / 新模型 / 覆盖面验证 | `gravarc-router/<model>` | `opencode-go/<model>` where visible | 只在任务关注 router、新模型或覆盖面时作为首选。若 router live prompt 返回维护/无 key/5xx，报告 `blocked`，不要继续改产品。 |

当前 GravArc Router catalog 会变化；使用前重新枚举。catalog 可见只是 `provider-visible`，不是 `provider-live`。

## 开发代理自身的 CLI 偏好

这些偏好用于开发 coding agent 选择自己的工具供应商，不是产品 E2E 证据：

- OpenCode：保留 OpenCode 配置的默认模型；需要显式 GPT 供应商时优先 `openai-evelyn/gpt-6-astra`，需要无 fallback 的 API-key GPT 时用 `apex/gpt-6-astra`。
- Claude Code：Claude 模型单独走 Claude Code。当前优先使用 GravArc Router 的 Claude catalog；默认 `claude-sonnet-4-6`，复杂 review 用 `claude-opus-4-7`，便宜快速任务用 `claude-haiku-4-5-20251001`。先确认 Claude Code 当前 `ANTHROPIC_BASE_URL` 和 model visibility。
- OpenCode/Claude Code 的成功回答不能标记为 hewo product E2E；需要产品证据时仍回到 pi Docker helper。

## 失败和 fallback 分类

把“provider catalog 可见”与“最小 live 请求可用”分开记录。每次 provider drift 或新模型试跑，都要把不可用/受限模型按下面类别归因；这本身是开发能力的一部分，不能只写“模型失败”。

| 类别 | 常见信号 | 解释 | 处理 |
| --- | --- | --- | --- |
| `auth_or_permission` | `401`、`403`、`not allowed`、`Permission denied`、`No active provider key`、data-policy opt-in | key 无效、账号未授权、模型需显式 opt-in 或当前 key 不允许该模型 | 不改产品 runtime；换已授权模型或修复账号/供应商接线 |
| `quota_or_rate` | `429`、quota/rate/usage limit、余额不足 | 供应商限速、额度或余额问题 | 延迟重试、降低并发或换同等备选；报告限额 |
| `endpoint_or_timeout` | `5xx`、provider maintenance、`No available channel`、timeout | 上游通道维护、无可用 channel、服务端故障或请求卡住 | 标记 `blocked`；可换备选供应商，不能把它当产品失败 |
| `parameter_or_capability` | `400`、unsupported reasoning/thinking、token budget mismatch、modalities 不符 | catalog 元数据或运行参数与模型真实能力不匹配 | 调整测试参数或 catalog capability；重新做最小 live probe |
| `catalog_only` | `pi --list-models` 可见但 live 404/permission denied | listing 不是 entitlement 证明 | 降级为 `provider-visible`，不作为可用模型 |

容器内 E2E 还要单独区分 `injection_error`：host 上可用、容器内失败，常见原因是只挂了 `auth.json`，其中的 `!cat`/路径在容器不可达。此时优先用 `--api-key-env` / `--api-key-stdin` 或 provider bundle 重跑，不要误判模型不可用。

## 更新此文件

当开发者明确调整偏好、某 provider 长期不稳定、或默认模型发生变化时，更新本文件并同步引用处。更新只能记录 provider/model id、非秘密路径类别和选择理由；不要提交 key、auth store、raw provider output 或私人会话。
