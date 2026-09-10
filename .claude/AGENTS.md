# Claude Code 开发适配

> **Role:** development coding agent 的 Claude Code 发现适配规则；不是产品行为。

- `skills` 必须是指向 `../.agents/skills` 的相对符号链接，不复制或单独维护技能。
- 技能内容只在 `.agents/skills/` 修改；memory、knowledge、workflow 仍由根 `CLAUDE.md`（指向 `AGENTS.md`）引导按需读取。
- 本目录仅用于开发 coding agent，不得进入产品 release 或 runtime。
