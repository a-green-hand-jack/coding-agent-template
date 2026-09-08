# HeWo Prompt Templates

For the development coding agent only: maintain the shipped slash commands.
Exclude this development guidance from releases.

Each `<name>.md` here becomes `/<name>`. Discovery is non-recursive, so a
template in a subdirectory is never loaded; keep every template flat in this
directory. Frontmatter supports exactly `description` and `argument-hint`.

Never place credentials or host-specific configuration here.
