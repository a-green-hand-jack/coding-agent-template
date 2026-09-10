# HeWo 开发设计资料

> **Role:** development coding agent 维护 hewo 专属开发设计资料的规则；不是产品行为。

在此维护 `agent-evaluation-loop-design` 使用的 `evaluation-contract.json`。
契约保持 `infrastructure-smoke-only`；不得虚构性能指标或把 smoke 当作性能证据。
产品身份与用户行为仅放在 `src/hewo/runtime/`。
此目录不由产品 runtime 加载，不进入安装、release archive 或最终 Docker image。
