---
name: runtime-smoke
description: Validate an installed HeWo runtime by inspecting the workspace and writing a checked smoke artifact.
---

# 运行时冒烟

用户要求进行基础设施或安装冒烟测试时使用本技能。

1. 检查当前工作区，不读取凭据或环境文件。
2. 确认工作区与智能体定义目录分离。
3. 运行 `hewo-tool --check`，核验精确输出 `HEWO_TOOL_OK`。
4. 写入 `artifacts/hewo-smoke.md`，包含标题 `Product runtime`、`Workspace access` 和 `Skill loaded`。
5. 重新读取产物，确认三个标题都存在。
6. 在 Product runtime 下写入 `HEWO_KNOWLEDGE_OK`、`HEWO_TOOL_OK`，在 Workspace access 下写入 `HEWO_WORKFLOW_OK`。
7. 只报告已核验的产物路径和结果，不包含原始提供商输出或秘密值。
