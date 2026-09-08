# Time and Weather Skill

For the development coding agent only: maintain the user-facing time and
weather skill. The nested AGENTS file is excluded from release artifacts.

Keep `allowed-tools` limited to the three runtime tools this skill calls.
Frontmatter accepts only `name`, `description`, `license`, `compatibility`,
`metadata`, `allowed-tools`, and `disable-model-invocation`; adding any other
key is invalid.
