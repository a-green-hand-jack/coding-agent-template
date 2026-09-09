# 基础设施冒烟工作流

1. 加载 `runtime-smoke` 技能。
2. 只检查提供的工作区和已安装的产品行为。
3. 写入产物前核验已安装工具的 `hewo-tool --check`。
4. 创建并核验 `artifacts/hewo-smoke.md`。
5. 返回简短结果并指出已核验的产物。

Workflow sentinel: `HEWO_WORKFLOW_OK`.
