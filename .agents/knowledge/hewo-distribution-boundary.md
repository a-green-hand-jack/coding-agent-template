# HeWo distribution boundary

> **Role of this document**
> - **Audience:** development coding agent，维护分发边界。
> - **Authority:** normative。
> - **Tone:** 明确职责与禁止事项。
> - **Language:** 中文，保留英文标识。
> - **Contains:** pi-native 分发、安装和开发验证边界。
> - **Excludes:** 用户操作见 `USER.md`，产品行为见 `src/hewo/runtime/`。

- HeWo 发布对象是 pi-native runtime/package；pi 是唯一 backend。
- `install.sh` 负责安装 runtime package，不负责 provider、model、credentials 或 host infrastructure。
- provider/model 选择、凭据注入和宿主机可用性由用户负责，并在运行时提供。
- 不提供 HeWo wrapper；用户和开发 E2E 使用相同的 pi 原生包加载命令，产品资源由 runtime manifest 和 extension 定义。
- human 入口和产品内容留在各自目录；仅供开发 coding agent 使用的脚本、知识和流程放在 `.agents/`。
- 验证应优先检查 package manifest、pi loader 和运行时边界；无 provider 的检查只能标记为 infrastructure-only。
