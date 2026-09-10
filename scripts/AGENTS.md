# Human Development and Release Entrypoints

> **Role:** development-agent instructions for maintaining human-facing setup and release scripts. Not product behavior.

在此只维护 human 入口 `setup-dev.sh`、`build-release.sh` 和 `publish-release.sh`；human Docker E2E 入口保留在 `docker/run-hewo-e2e.sh`。这些入口可以调用 `.agents/scripts/` 的内部实现，但不得把 coding-agent 专用工具重新放回本目录。

产品定义留在 `src/`，开发 coding agent 专用工具放在 `.agents/scripts/`。所有 release payload 排除 `AGENTS.md` 和 `.agents/`；保持凭据不打印、不入库，生成产物不入版本控制。不得以语法或结构校验替代真实 provider-backed Docker E2E 证据。
