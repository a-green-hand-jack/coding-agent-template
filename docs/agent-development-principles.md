# Agent Template 启动文档

本文件是模板的启动规范。它规定 Agent 应通过行为定义、Skills、Knowledge、Workflow、Memory 和权限配置表达，而不是重写 runtime；用户应只接触 Agent 产品命令；开发和评测必须从干净 Docker 容器走真实安装路径；Provider 凭证只能在运行时注入；benchmark 只用于通用能力回归。

完整原则、验收门槛和流程记录在 GitHub Issue 1 的启动文档评论中。
