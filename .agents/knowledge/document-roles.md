# Document roles: separating a document's role from its content

> **Role of this document**
> - **Audience:** the development coding agent maintaining this repository, and any downstream repository adopting the convention.
> - **Authority:** normative. This is the definition the `check-document-roles.py` gate enforces.
> - **Tone:** imperative and specific; define the contract, not the motivation.
> - **Language:** English.
> - **Contains:** the role-block format, the governed set, the audience vocabulary, and the rules for adding a document.
> - **Excludes:** the content of any individual document (each one carries its own block), product behavior (see `src/<agent>/runtime/`), and the enforcement logic itself (see `scripts/check-document-roles.py`).

## Why a document declares its own role

A repository that hosts three audiences at once — end users, human developers,
and coding agents — accumulates documents whose tone and scope drift because
nobody wrote down who each one is for. The failure is not cosmetic. A rule
written for the development coding agent leaking into a user manual becomes an
instruction the user cannot act on; a product behavior statement leaking into
development instructions becomes behavior the product never ships.

So every governed document declares its **role** separately from its
**content**. The role block answers "who reads this, with what authority, in
what tone, and what belongs here" before the first line of content. Content
answers everything else. When the two disagree, the role block wins and the
content is wrong.

## The role block

Immediately after the H1, as a blockquote, with these fields in this order:

```markdown
# <Document title>

> **Role of this document**
> - **Audience:** <who reads it, in the vocabulary below>
> - **Authority:** normative | informative | record
> - **Tone:** <how it should read>
> - **Language:** English | Chinese | Chinese, with English identifiers
> - **Contains:** <what belongs here>
> - **Excludes:** <what must not leak in, and where it belongs instead>
```

Every field is required and single-line. `Excludes` must name the correct
destination for at least one excluded category, so the block routes content
instead of only forbidding it.

### Audience vocabulary

Use exactly one of these as the leading term, then qualify freely:

- `end user` — someone who installed the product Agent and runs its command.
- `human developer` — a person building or operating an Agent from this template.
- `development coding agent` — the coding agent maintaining a repository.
- `product agent` — the installed Agent itself, at run time.

A document with two audiences is usually two documents. If it genuinely has
two, name both and say which sections belong to which.

### Authority vocabulary

- `normative` — binding. An agent must follow it; a conflict with content is a bug.
- `informative` — explanatory. Helps a reader decide; binds nobody.
- `record` — an observation or decision fixed at a point in time. Never rewritten
  to satisfy a later gate.

## The governed set

Governed, full block required:

- root documents: `README.md`, `DEV.md`, `USER.md`, `AGENTS.md`
- `benchmarks/README.md`
- `.agents/README.md`, `.agents/*/README.md`
- `.agents/knowledge/*.md` except records
- `.agents/workflows/*.md`
- `.agents/skills/*/SKILL.md` and their `references/*.md`

Governed, short form required — a single `> **Role:**` line naming the audience
and the scope — for every scoped `AGENTS.md` below the root, including the ones
inside `src/<agent>/runtime/`. These are numerous and short, and their audience
never varies; a six-field block would be noise. The runtime ones matter most:
they are the files most easily mistaken for product behavior, and a role line
says outright that they are not.

Exempt, and deliberately so:

- **The product runtime payload** — everything under `src/<agent>/runtime/`
  except `AGENTS.md`. These files are loaded into the product Agent's prompt.
  Documentation metadata must never enter a shipped prompt, so the payload
  declares audience through its location and its manifest, never through a role
  block. (`AGENTS.md` is excluded from every payload, which is why it takes the
  short form instead.) This exemption is a boundary, not a shortcut.
- **Records**: `.agents/memory/*.md`, `PLAN.md`, `PLAN-*.md`,
  `DevelopmentMachine.md`. Their authority is `record`; they are generated or
  dated evidence, and adding a block would edit history.
- **Placeholders**: `.agents/downstream-skeleton/**/PLACEHOLDER.md`, and fixtures
  under `.agents/skills/*/fixtures/**`.

## Rules

1. A new governed document is not finished until it has a role block. The gate
   `python3 scripts/check-document-roles.py` fails otherwise, and it runs in CI.
2. Changing what a document is *for* means editing its role block first, then
   moving the content that no longer belongs. Never leave the block describing a
   document the content contradicts.
3. Content that the block excludes gets moved to the destination the block
   names, not deleted silently.
4. `AGENTS.md` is the real file; `CLAUDE.md` is a symlink to it. Never edit
   `CLAUDE.md`, never let the two diverge, and never add a second copy for
   another agent vendor — add a symlink.
5. A downstream repository adopting this convention writes its own role blocks.
   The audience vocabulary is reusable; this repository's specific `Contains` and
   `Excludes` lines are not.
