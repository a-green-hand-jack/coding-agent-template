# 产品分发

> **Role:** 开发 coding agent 的 installer 和原生 pi container entrypoint 维护规则；不是产品行为。

安装器只安装 runtime package 和产品工具环境，不安装 pi，不配置 provider/model 或凭据。
用户与容器运行同一条 pi 原生命令，通过 `-e <installed-runtime-package>` 加载产品。
identity/context/tools 的 manifest 消费归 runtime extension，不重建产品参数解析器。
安装和归档必须在每一层排除 AGENTS.md、CLAUDE.md 和开发内容；凭据只在运行时注入。
