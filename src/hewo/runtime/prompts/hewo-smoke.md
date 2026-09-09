---
description: Run the infrastructure smoke task and verify the named artifact.
argument-hint: [artifact-name]
---

为产物 `$ARGUMENTS` 运行基础设施冒烟任务。

遵循 `runtime-smoke` 技能。未提供产物名称时使用 `hewo-smoke.md`。

宣称成功前核验产物和 `hewo-tool --check` 结果。报告已核验的产物路径和结果，不包含原始提供商输出或秘密值。
