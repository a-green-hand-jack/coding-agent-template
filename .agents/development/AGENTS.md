# Agent 开发设计资料

> **Role:** development coding agent 维护各产品开发设计资料的规则；不是产品行为。

按 `<agent_name>/` 隔离产品专属设计资料和 evaluation contract。
遵循根与 `.agents/AGENTS.md`；将可复用方法保留在 `.agents/skills/`。
不得把此目录载入产品 runtime 或放入安装、release archive、最终 Docker image。
每个产品子目录维护 scoped `AGENTS.md`；契约修改须遵循 evaluation-contract 规范。
