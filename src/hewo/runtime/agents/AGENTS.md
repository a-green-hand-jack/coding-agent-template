# HeWo Agent Definitions

For the development coding agent only: maintain the sub-agent definitions
this runtime dispatches to. Exclude this development guidance from releases.

These files are read by the runtime's own extension, not by pi itself. pi has
no agent-definition manifest key, so do not add one or expect pi to load this
directory. Frontmatter supports exactly `name`, `description`, `tools`, and
optionally `prompt-file`.

Keep every `tools` list minimal and read-only. A sub-agent must never inherit
write or execute permission.
