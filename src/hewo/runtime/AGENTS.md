# HeWo Runtime Definition

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
- `hewo` — everything pi has no primitive for: the system-prompt files, the
  context files injected with per-file provenance, the agent definitions read
  by this runtime's own extension, the leaf tools, the tool allowlist, and the
  default capability/network posture.

Rules:

- Every path is a normalized relative path under this directory. Absolute
  paths, `..` traversal, empty names and shell metacharacters are rejected by
  the launcher, not merely discouraged.
- `default_tools` is a strict allowlist that pi applies to built-in **and**
  extension tools, so a new extension tool must be added there or it will be
  silently unavailable.
- No npm lifecycle scripts. The runtime declares no dependencies; if a
  downstream Agent adds any, install them frozen and with scripts disabled.
- `capabilities` is empty and `network` is `deny` by default. Widening either
  is a product decision that needs review, not a convenience.
