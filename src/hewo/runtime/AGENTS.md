# HeWo Runtime Definition

> **Role:** development-agent instructions for the hewo runtime definition, the payload installed and released to users. Not product behavior, and excluded from every payload.

For the **development coding agent** only. This directory is the hewo product
Agent definition: the payload installed and released to users. Do not act as
hewo while editing it, and never put development instructions in a file other
than an `AGENTS.md` (every `AGENTS.md` here is excluded from the payload).

`package.json` is the **single source of truth** for what the runtime loads.
`agent.yaml` carries scaffold metadata only and must never declare a second
resource list. When you add a resource, declare it in `package.json` and
nowhere else.

Two sections, with different meanings:

- `pi` — resources pi loads natively: `skills`, `prompts`, `themes`,
  `extensions`. These are the only keys pi recognises; there is no `pi.agents`.
- `agent` — everything pi has no primitive for: the system-prompt files, the
  context files injected with per-file provenance, the agent definitions read
  by this runtime's own extension, the leaf tools, the tool allowlist, and the
  default capability/network posture.

Rules:

- Every path is a normalized relative path under this directory. Absolute
  paths, `..` traversal, empty names and shell metacharacters are rejected by
  definition validation 与 runtime extension，不能只依赖文档约定。
- runtime extension 从 manifest 消费 identity/context 和 `default_tools`，并通过
  pi API 对内建及 extension tools 应用严格白名单。新增工具必须同时声明；用户和
  容器均用 pi 原生 `-e <installed-runtime-package>` 加载，不维护独立产品命令。
- No npm lifecycle scripts. The runtime declares no dependencies; if a
  downstream Agent adds any, install them frozen and with scripts disabled.
- `capabilities` is empty and `network` is `deny` by default. Widening either
  is a product decision that needs review, not a convenience.
