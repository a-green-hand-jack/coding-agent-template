> **Role:** development-agent instructions for the reusable development knowledge, memory, skills, and workflows in this tree. Not product behavior.

## Development Resources

开发主入口只有 `scripts/setup-dev.sh` 和 `docker/run-hewo-e2e.sh`。
后者的普通路径安装当前冻结构建；`--release`/`--user-path` 只从 release artifact
安装，再运行与用户相同的 pi 原生命令。归档/安装 parity 收进该 E2E，不新增
release wrapper。独立评测、benchmark、冻结快照、trace 和审计保留各自职责，其 coding-agent
内部工具统一放在 `.agents/scripts/`，不可包装成新的 human 主入口。
`scripts/build-release.sh` 与 `scripts/publish-release.sh` 保留为 human 发布入口。
provider/model 必须实际传给 pi CLI；运行与证据均使用解析后的不可变镜像 ID。

You are the development coding agent, not the product agent. Maintain reusable development knowledge, memory, skills, and workflows here. Never ship this tree or private data in product releases. Follow root guidance and record acceptance evidence in GitHub issues.

Before product-behavior testing, run the root `AGENTS.md` operating-identity self-check and inject the host provider through `docker/run-hewo-e2e.sh`; see `.agents/knowledge/provider-e2e.md`. Before tagging the template run the template self-audit (`template-release-readiness`); in a downstream repo run the consistency audit (`agent-consistency-audit`) with that repo's own Agent name. To discover providers, use secret-free enumeration (`pi --list-models`, host audit scripts); never print auth stores or dump a backend's resolved configuration.
