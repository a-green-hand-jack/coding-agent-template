# HeWo distribution boundary

> 本文件是开发 coding agent 规则，不是产品 runtime payload。

- HeWo 发布对象是 pi-native runtime/package；pi 是唯一 backend。
- `install.sh` 负责安装 runtime package，不负责 provider、model、credentials 或 host infrastructure。
- provider/model 选择、凭据注入和宿主机可用性由用户负责，并在运行时提供。
- HeWo wrapper 仅可作为兼容或基础设施 plumbing；不得被描述为产品入口、第二 backend 或产品 API。
- 验证应优先检查 package manifest、pi loader 和运行时边界；无 provider 的检查只能标记为 infrastructure-only。
