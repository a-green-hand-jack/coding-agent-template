# Coding-Agent Internal Tooling

> **Role:** development-agent instructions for coding-agent-only internal tooling. Not product behavior or human entrypoint documentation.

只在此维护开发 coding agent 使用的定义校验、冻结快照、镜像构建、评测循环、内部 case、trace、provider bundle 与审计工具。保留原有功能与凭据安全边界，不将本目录复制到产品 runtime、release payload 或最终镜像。

脚本自身定位仓库根时从本目录上溯两层；保持 CI、skills、registry、human 入口的调用路径同步。冻结快照必须包含本目录，后台子进程必须执行快照内的脚本，不回读活动工作树。

Human 入口仍为 `scripts/setup-dev.sh`、`scripts/build-release.sh`、`scripts/publish-release.sh` 和 `docker/run-hewo-e2e.sh`。这些入口可以调用本目录内部实现，但不得把内部工具变成产品工具或新的 human 主入口。不得打印凭据；静态校验和 `--help` 只构成 infrastructure-only 证据。
