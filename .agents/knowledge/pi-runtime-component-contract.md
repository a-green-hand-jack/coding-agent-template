# Pi runtime component contract

> **架构决策（已确认）**：HeWo 是 pi-native runtime/package，pi 是唯一 backend。`install.sh` 只安装 runtime package；provider、model、credentials 与 host infrastructure 由用户负责。HeWo wrapper 不是产品入口，开发规则不得把 wrapper 当作第二 backend 或产品 API。

> **Role of this document**
> - **Audience:** the development coding agent composing a product Agent on the pi backend in this repository.
> - **Authority:** normative. The decision tree, the script boundary and the discovery guards bind every component choice.
> - **Tone:** imperative and specific; a decision tree, per-component tables, and exact flag spellings with what each one does not do.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** the component decision tree, the per-component pi loader contract, the leaf-script boundary, the pi capability matrix, the `.agents/` discovery hazard and its required guards, and dated provenance.
> - **Excludes:** product payload of any kind (see `src/hewo/runtime/`), and this machine's credential and provider selection facts (see `.agents/knowledge/provider-e2e.md`).

For the **development coding agent** only. Development-side knowledge: it governs
how this repository composes a product Agent. It is never product payload and must
never be copied into `src/*/runtime/`. Backend in scope: pi `0.85.1`
(`@earendil-works/pi-coding-agent`) and nothing else. Secret-free: flags, keys,
and documented `~/.pi/...` paths only, never credential contents.

## The failure mode this prevents

A product Agent is a **composed runtime**, not a bag of scripts. The recurring
degradation is: a requirement arrives, the coding agent writes a Python or shell
script that re-implements a loop the backend already owns, and the product's
behavior moves out of declarative resources into imperative glue nobody can load,
inspect, or version as an Agent capability. Scripts are legitimate **only** as
stateless leaf adapters at the very bottom of the stack. Every component above
that line already exists in pi and must be expressed with pi's loaders.

## Component decision tree

Descend one level at a time. **You may descend only after writing down, in the
task report or the plan, why the previous level cannot express the requirement.**
Jumping straight to a leaf script requires a recorded *backend-capability gap*:
the exact pi primitive that would have covered it and the exact reason it does
not. "Faster to script" is not a gap.

1. **Declarative resource.** Can the requirement be stated as text the model
   reads? Identity/system prompt, knowledge file, skill, prompt template, theme.
   Most product requirements stop here. Prefer this level always.
2. **Pi-native configuration.** Can it be a startup decision? Tool allowlist
   (`--tools`), denylist (`--exclude-tools`), session mode (`--session*`,
   `--no-session`, `--fork`), provider/model (`--provider`, `--model`,
   `--thinking`), context-file policy (`--no-context-files`), project trust
   (`--approve` / `--no-approve`).
3. **Thin TypeScript extension.** Only if the requirement needs a *typed tool*,
   a *lifecycle hook*, or in-process state. Default-export factory receiving
   `ExtensionAPI`, loaded through `--extension` / `-e`. Loaded via jiti, so
   TypeScript needs no build step. Keep it thin: an extension wires and types,
   it does not implement domain logic.
4. **Leaf tool / script.** A stateless adapter invoked *by* a tool or extension,
   with an explicit I/O contract (see the script boundary below).
5. **External CLI or service.** Only when the capability genuinely lives outside
   this process. Wrap it at level 4; never let the product identity depend on it
   being present without a documented failure mode.

Anti-pattern to reject on sight: a script that spawns a coding agent, manages a
session directory, calls a provider, loops on approvals, or orchestrates several
components. Those are levels 1-3 by definition.

## Per-component contract

| Component | Responsibility | Enters model context? | Pi loader (exact flag / manifest key) | Lifecycle & state | When NOT to use it |
| --- | --- | --- | --- | --- | --- |
| Identity / system prompt | Who the agent is; non-negotiable rules | Yes, always | `--system-prompt <text>` replaces; `--append-system-prompt <text>` appends and accepts literal text **or** a file path, repeatable. Files: `.pi/SYSTEM.md`, `~/.pi/agent/SYSTEM.md` replace; `APPEND_SYSTEM.md` appends (`.pi/` copies trust-gated) | Fixed for the process | For task-specific or conditional instructions — those are skills |
| Knowledge | Stable reference facts with provenance | Only when a skill or prompt points at it, or via context files | No dedicated loader. Ship as files the agent reads; `AGENTS.md`/`CLAUDE.md` discovery is the context-file path and is disabled by `--no-context-files` / `-nc` | Static, versioned with the runtime | As a dumping ground for procedures — a procedure is a skill |
| Memory policy | Rules for what to persist and where | Yes, as prompt or skill text | Same as identity or skill; pi has no memory primitive | Policy is static; the store is product-defined | Do not invent a memory subsystem in a script |
| Skill | A procedure the model may invoke on demand | On demand (name + description always; body when invoked) | `--skill <path>` (repeatable, **additive even with `--no-skills`**). Discovery: `~/.pi/agent/skills/`, `~/.agents/skills/`, and after project trust `.pi/skills/` and `.agents/skills/` in cwd and ancestors up to the git root. Packages: `skills/` dirs or `pi.skills`. Settings: `skills` array. Disable: `--no-skills` / `-ns` | Unit = a directory containing `SKILL.md`; stateless per invocation | For something the *user* triggers by name — that is a prompt template |
| Prompt template / command | A user-triggered `/<name>` entry point | Only when invoked | `--prompt-template <path>` (repeatable). Discovery: `~/.pi/agent/prompts/*.md`, `.pi/prompts/*.md` (trust-gated), packages `prompts/` or `pi.prompts`, settings key `prompts`. `<name>.md` -> `/<name>`. Disable: `--no-prompt-templates` / `-np` | Stateless expansion | For model-initiated behavior — that is a skill |
| Theme | Terminal presentation only | No | `--theme <path>` (repeatable) to load, `--use-theme <name>` to select. Manifest `pi.themes`; convention `themes/` (`.json`). Disable: `--no-themes` (no short form) | Process-lifetime | For anything behavioral; a theme cannot carry product meaning |
| Tool allowlist | Bound the agent's capability surface | No (affects available tools) | `--tools` / `-t <comma,list>` — strict allowlist over built-in **and** extension **and** custom tools; **one comma-separated argument, NOT repeatable**. `--exclude-tools` / `-xt` denylist filters the result. `--no-tools` / `-nt`, `--no-builtin-tools` / `-nbt`. Settings `defaultTools` constrains built-ins only. Built-ins: `read`, `bash`, `powershell`, `edit`, `write`, `grep`, `find`, `ls` (`grep`/`find`/`ls` read-only, off by default) | Fixed at startup | As a security boundary against a hostile prompt; it is a capability bound, and there is no permission system behind it |
| Typed tool (extension) | Give the model a structured, validated action | Yes, as a tool schema | `--extension <path>` / `-e` (repeatable). Discovery: `~/.pi/agent/extensions/*.ts`, `~/.pi/agent/extensions/*/index.ts`, `.pi/extensions/*.ts`, `.pi/extensions/*/index.ts`. Manifest `pi.extensions`; convention `extensions/` (`.ts`/`.js`). Default-export factory receiving `ExtensionAPI`, sync or async. Disable `--no-extensions` / `-ne` (explicit `-e` still loads) | Per-call; may hold in-process state | When `bash` plus a documented leaf script already expresses it |
| Lifecycle hook (extension) | React to run/turn/tool events | No, unless it injects text | Same loader as typed tools (`-e`) | In-process, dies with the process | For durable side effects; nothing here survives the process |
| Session / state | Conversation continuity | Yes, replayed history | `--session <path\|id>`, `--session-id <id>`, `--session-dir <dir>`, `--fork`, `--no-session`, `-c` / `--continue`, `-r` / `--resume`, `-n` / `--name`. Auto-save to `~/.pi/agent/sessions/` organized by cwd. Dir precedence: `--session-dir`, then `PI_CODING_AGENT_SESSION_DIR`, then `sessionDir` in `settings.json` | Persisted by pi | As a product database; it is a transcript, not a schema |
| Sub-agent | Delegate an isolated unit of work | Definition text enters the sub-agent's context | **Not pi core.** `@tintinweb/pi-subagents` v0.19.0. Definition files discovered from global `getAgentDir()/agents`, then `<cwd>/.agents/agents`, then `<cwd>/.pi/agents`, loaded in that order into a Map so **last load wins**. 24 frontmatter keys plus aliases `inherit_extensions` (= `extensions`) and `inherit_skills` (= `skills`). `isolation: "off"` vetoes a caller's `isolation: "worktree"`; `thinking` is an unvalidated cast | Per-delegation; settings in `~/.pi/agent/subagents.json` (global) and `<cwd>/.pi/subagents.json` (project), shallow-spread with project overriding | When the work is a single procedure — that is a skill. Never assume it exists without the package installed |
| Workflow | Orchestrate phases of sub-agent work | No (the script is not prompt text) | **Not pi core.** `@tintinweb/pi-subagents` only, via `--subagents-workflow-file=<path>` — use the `=` form; the space form swallows the next argument | Scripts are **not** ES modules: `export const meta = {...}` is a regex-scanned text marker and the remainder runs as an **async function body** inside `node:vm`, so top-level `await` and a bare top-level `return` are legal and the file is not valid standalone JavaScript. Sandbox blocks `eval`, wasm, `Date.now()`, `new Date()`, `Math.random()`. Bare globals (no context object): `agent`, `parallel`, `pipeline`, `phase`, `log`, `workflow`, `budget`, `console`, `meta`, `args` | For anything a single agent run can do; and never as the product's main entry point, since workflows cannot be started or steered over RPC |
| Provider / model | Which backend serves the run | No | `--provider <name>` (default `google`), `--model <pattern>` (supports `provider/id` and optional `:<thinking>`), `--api-key`, `--models <patterns>`, `--thinking <off\|minimal\|low\|medium\|high\|xhigh\|max>`, `--list-models [search]`. Credential order: CLI `--api-key`, then `auth.json`, then env var, then custom provider keys in `models.json` | Fixed per process | Do not hardcode a provider/model that is not available on the host; enumerate first |
| Project trust | Whether cwd-local resources load | Indirectly, by gating resources | `--approve` / `-a`, `--no-approve` / `-na`. Config `defaultProjectTrust` in `~/.pi/agent/settings.json` = `ask` (default) \| `always` \| `never`, global-only key. Persisted decisions in `~/.pi/agent/trust.json` | Persisted per absolute directory | As a sandbox. It gates discovery of project resources, not what tools can do |
| Package / manifest | Distribute resources as a unit | Indirectly, by contributing resources | `package.json` top-level `pi` key. Sub-keys: `extensions`, `skills`, `prompts`, `themes` (plus gallery-only `video`, `image`). **There is no `pi.agents` key.** Arrays are package-root-relative and support globs and `!exclusions`. With no `pi` key, convention fallback: `extensions/` (`.ts`/`.js`), `skills/` (recursive `SKILL.md` + top-level `.md`), `prompts/` (`.md`), `themes/` (`.json`). Keyword `pi-package`; dir override `PI_PACKAGE_DIR` | Install-time | To ship agent definitions — the manifest cannot express them |
| External adapter | Reach a CLI or network service | No | No pi loader. Invoked from a typed tool or from `bash` | Owned by the callee | When the capability is already a pi primitive |
| Leaf script | One stateless transformation or probe | No | No pi loader; invoked by `bash` or a typed tool | Stateless by contract | For anything in the rows above |

## Script boundary contract

A leaf script is a stateless adapter. It **may** parse input, transform data,
probe the environment, call one external CLI or endpoint, and print a result.

It may **never** own:

- the agent loop or turn management
- session creation, selection, or persistence
- model or provider calls
- approval, retry, or confirmation loops
- sub-agent spawning or orchestration
- product identity, persona, or policy text
- long-lived state, caches that outlive the call, or a private datastore
- orchestration of more than one component

Every leaf script must satisfy all of the following, and the contract must be
written in the script's own header:

- **Input/output contract.** Named arguments or stdin in, one documented format
  out (prefer a single JSON object on stdout). Diagnostics to stderr only.
- **Idempotency.** Running it twice with the same input yields the same result
  and no additional side effects.
- **Error codes.** `0` success; distinct non-zero codes for usage error,
  missing dependency, upstream failure, and timeout. Never exit `0` on failure.
- **Timeout and cancellation.** A bounded default timeout; terminates cleanly on
  `SIGTERM`/`SIGINT` without orphaning children.
- **Output truncation.** Bound stdout to a documented size so a large upstream
  response cannot flood the model context; state the truncation marker.
- **Statelessness.** No writes outside paths given as arguments; no hidden
  temp-state reused across runs.
- **Secret safety.** Reads credentials only from an environment variable or a
  path passed in; never prints, logs, or echoes credential contents; never
  embeds a key or endpoint token.
- **Standalone verification.** A documented command that proves the script works
  and **needs no credentials** — typically `--help`, `--dry-run`, or a fixture
  input. If it cannot be verified without a credential, the script is doing too
  much.

## Pi capability matrix

### (a) Pi core primitives

| Capability | Exact loader | Verification entry point (secret-free) |
| --- | --- | --- |
| Skills | `--skill <path>`, `pi.skills`, settings `skills`; off with `--no-skills` / `-ns` | `pi --help` and grep for `--skill` |
| Prompt templates / slash commands | `--prompt-template <path>`, `pi.prompts`, settings `prompts`, dir `prompts/`; off with `--no-prompt-templates` / `-np` | `pi --help` and grep for `--prompt-template` |
| Extensions (typed tools, hooks) | `--extension <path>` / `-e`, `pi.extensions`, dir `extensions/`; off with `--no-extensions` / `-ne` | `pi --help` and grep for `--extension` |
| Themes | `--theme <path>` + `--use-theme <name>`, `pi.themes`, dir `themes/`; off with `--no-themes` | `pi --help` and grep for `--use-theme` |
| System prompt control | `--system-prompt`, `--append-system-prompt`; `SYSTEM.md` / `APPEND_SYSTEM.md` | `pi --help` and grep for `system-prompt` |
| Tool gating | `--tools` / `-t`, `--exclude-tools` / `-xt`, `--no-tools` / `-nt`, `--no-builtin-tools` / `-nbt`; settings `defaultTools` | `pi --help` and grep for `exclude-tools` |
| Sessions | `--session`, `--session-id`, `--session-dir`, `--fork`, `--no-session`, `-c`, `-r`, `-n` | `pi --help` and grep for `--session` |
| Modes | `--print` / `-p`; `--mode <text\|json\|rpc>` | `pi --help` and grep for `--mode` |
| Provider / model selection | `--provider`, `--model`, `--models`, `--thinking`, `--api-key`, `--list-models` | `pi --list-models` (auth-filtered, prints no secrets) |
| Project trust | `--approve` / `-a`, `--no-approve` / `-na`; `defaultProjectTrust` | `pi --help` and grep for `approve` |
| Context files | `AGENTS.md` / `CLAUDE.md` discovery; off with `--no-context-files` / `-nc` | `pi --help` and grep for `context-files` |
| Offline / env controls | `--offline`; `PI_CODING_AGENT_DIR`, `PI_CODING_AGENT_SESSION_DIR`, `PI_PACKAGE_DIR`, `PI_OFFLINE`, `PI_TELEMETRY` | `pi --help` and grep for `--offline` |
| Package manifest | `package.json` top-level `pi` key (`extensions`, `skills`, `prompts`, `themes`); keyword `pi-package` | inspect a package's `package.json` for the `pi` key |

Note the naming asymmetry for templates: settings key `prompts`, CLI flag
`--prompt-template`, directory `prompts/`. Discovery inside `prompts/` is
**non-recursive**.

### (b) Only via an installed package or bundled extension

| Capability | Source | Verification entry point (secret-free) |
| --- | --- | --- |
| Sub-agents (agent definition files, isolation, effort) | `@tintinweb/pi-subagents` v0.19.0 (installed package) | `pi --help` and confirm `--subagents-workflow-file` appears; absent means the package is not active |
| Workflows (`meta`, phases, `agent()`, `parallel`, `pipeline`) | `@tintinweb/pi-subagents` | run a no-op workflow file via `--subagents-workflow-file=<path>` |
| Plan mode (`--plan`) | bundled `examples/extensions/plan-mode/` extension only | `pi --help` and confirm `--plan` appears only when that extension is loaded |

Sub-agent details that constrain design:

- `agent()` accepted keys: `label`, `phase`, `model`, `agentType`, `isolation`,
  `gate`, `resume`, `effort`, `schema`. Effort: `minimal|low|medium|high|xhigh|max`
  (no `off`).
- `meta` schema: `{ name: string; description: string; whenToUse?: string;
  phases?: { title: string; detail?: string; model?: string }[] }`.
- Subagent settings defaults include `maxConcurrent` 10, `maxSubagentDepth` 2,
  `defaultMaxTurns` 0, `graceTurns` 5, `backgroundByDefault` true,
  `fallbackSubagent` `general-purpose`.
- The `pi.events` RPC bus is **in-process only** — the bundled docs say "none of
  this survives a real process boundary". Workflows cannot be started or steered
  over RPC and emit no lifecycle events. A headless host's only doors are
  `--subagents-workflow-file=<path>` and the in-process global registry
  `globalThis[Symbol.for("pi-subagents:manager")]` (`waitForAll()`,
  `hasRunning()`, `spawn(...)`, `getRecord(id)`).
- RPC option keys are **not validated**: snake_case spellings
  (`run_in_background`, `max_turns`, `thinking`, `inherit_context`, `memory`)
  silently no-op. The real names are `isBackground`, `maxTurns`,
  `thinkingLevel`, `inheritContext`, `cwd`.

### (c) Capabilities pi does not have

| Missing capability | Consequence for design | Verification entry point (secret-free) |
| --- | --- | --- |
| MCP | No MCP servers, no MCP tools. `README.md` states "No MCP." Integrations are extensions or leaf adapters | `pi --help` shows no MCP flag; bundled `README.md` says "No MCP." |
| Permission system / approval popups | No `permissions` key in `settings.json`. The **only** tool gating is `--tools` / `--exclude-tools` / `--no-tools` / `--no-builtin-tools` | `pi --help` shows no permission flag |
| Core agent definitions | No `--agent`, `--subagent`, or `--agent-file`, and no `pi.agents` manifest key. Agent definitions exist only through `@tintinweb/pi-subagents` | `pi --help` and grep for `agent` — no definition flag |
| Built-in todo / task list | Do not assume a task-tracking tool exists; if the product needs one, it is a typed tool in an extension | `pi --help` and the built-in tool list (`read`, `bash`, `powershell`, `edit`, `write`, `grep`, `find`, `ls`) |
| `--max-turns` | Turn bounding is not a core flag; `defaultMaxTurns` exists only in subagent settings | `pi --help` and grep for `max-turns` |
| `--output-format`, `--cwd`, `--timeout`, `--prompt-file` | None exist. Use `--mode` for output shape; process cwd for cwd; the caller for timeouts; `--append-system-prompt <path>` for file-borne prompt text | `pi --help` and grep for each |

## Hazard: the `.agents/` collision

This is the most likely way a product Agent silently inherits this repository's
development identity.

Two independent discovery paths collide with this repository's layout:

1. Pi's **project skill discovery** includes `.agents/skills/` in cwd **and
   ancestor directories** up to the git root (after project trust).
2. `@tintinweb/pi-subagents` reads `<cwd>/.agents/agents` for agent definitions.

This repository uses `.agents/` for **development** skills, memory, and
knowledge. Therefore running `pi` inside this repository — or inside a
downstream repository built from it — can load the *development* skills and
`AGENTS.md` into the *product* agent's context. That is exactly the identity
leak this repository's root `AGENTS.md` forbids.

Required guards when launching a product runtime:

- `--no-skills` / `-ns` **plus** explicit `--skill <path>` for each product
  skill. Explicit `--skill` is additive even with `--no-skills`, so this yields
  the product's skills and nothing discovered.
- `--no-context-files` / `-nc` so `AGENTS.md` and `CLAUDE.md` are never
  discovered or loaded.
- `--no-extensions` / `-ne` **plus** explicit `-e <path>` for each product
  extension (explicit `-e` still loads).
- `--no-prompt-templates` / `-np` **plus** explicit `--prompt-template <path>`
  for each product command.
- `--no-approve` / `-na`, or `defaultProjectTrust: "never"` in
  `~/.pi/agent/settings.json`, when the product must not pick up project-local
  resources at all.

Additional rules:

- Agent definitions must **not** be placed in this repository's `.agents/agents`.
  Last load wins across global -> `<cwd>/.agents/agents` -> `<cwd>/.pi/agents`,
  so a development-side definition there would override a product definition.
- Non-interactive modes (`-p`, `--mode json`, `--mode rpc`) show **no** trust
  prompt. Without a saved decision in `~/.pi/agent/trust.json`, `ask` and `never`
  ignore project resources and `always` trusts them. Never rely on the absence of
  a prompt as evidence that project resources were skipped — set the guards
  explicitly.

## Provenance

- Backend: pi `0.85.1`, package `@earendil-works/pi-coding-agent`.
- Facts were read from local `pi --help` and the bundled `docs/*.md` on this
  development machine on **2026-09-08**.
- Sub-agent facts are from the installed package `@tintinweb/pi-subagents`
  v0.19.0, which is **not** pi core.
- **No credentials were read and no provider request was made.** No auth store,
  `*-key` file, or `.env` was opened; `--list-models` was not invoked for this
  document.

Observed rather than documented:

- The shape of `~/.pi/agent/trust.json`, `{"<abs dir>": boolean}`, was observed
  on this machine; it is not stated in the bundled documentation and may change.

Not documented / unknown:

- Whether `--mode json` composes with `-p` is **not documented**, although the
  bundled subagent example passes both. Do not depend on the combination without
  re-verifying it.
- Whether the `pi.events` in-process limitation has any supported workaround for
  a cross-process host is **not documented** beyond the two doors named above.
- The full `ExtensionAPI` surface is not enumerated here; read the bundled
  extension docs before designing an extension, and state what you verified.

## Verified in practice (2026-09-08)

This contract was exercised end to end by converging `hewo` to a pi-only,
manifest-driven runtime. What the exercise confirmed or corrected:

- The decision tree held: identity, knowledge, memory policy, skills, prompt
  templates, workflows and the theme all stayed declarative. Exactly one thin
  TypeScript extension was needed, for typed tools, lifecycle hooks, the
  capability/path gate and sub-agent spawning. One leaf Python tool remained a
  leaf. No new agent loop, model client, session manager or approval loop was
  written.
- `--tools` constrains **extension** tools too. An extension tool absent from
  `runtime.default_tools` is silently unavailable; this is the most likely
  cause of "my new tool does nothing".
- `--append-system-prompt` being repeatable means context injection keeps
  per-file provenance. Never concatenate resources into a single blob again.
- Globs are supported by pi in package manifests but are **deliberately
  refused** by this template's launcher and validator: an explicit path list is
  auditable, a glob is not.
- Sub-agent budgets that are actually enforceable here are wall-clock timeout,
  concurrency, retries and output truncation. A turn budget is not, because pi
  0.85.1 has no `--max-turns`. State the gap; do not simulate the flag.

## Deferred, with the trigger that would revive each

| Capability | Status | Revive when |
| --- | --- | --- |
| plan mode | deferred | a product requirement needs staged planning; it is a bundled example extension, not core |
| MCP | not available | pi gains MCP, or an external adapter is justified as a leaf tool |
| built-in todos | not available | never as pi core; model it as skill or extension state |
| RPC/SDK host | verification entry only | a headless host is actually built; note `pi.events` is in-process only |
| provider registration | verification entry only | the product must ship its own provider adapter |
| complete theme | partial | pi's 53 colour token names are verified from a real source |
| durable user memory | disabled by design | a product decision authorises cross-session user memory, with a privacy boundary |
| turn budget for sub-agents | unenforceable | pi grows `--max-turns` or an equivalent |

Nothing in this table is implemented. Do not report a deferred capability as
present because a file mentions it.

## Ambient discovery: which `--no-*` flags are safe to pass

Measured on pi 0.85.1 with `--mode rpc` + `get_commands` (which reports each
command's source and path), not assumed from the docs:

- `--no-skills` + explicit `--skill` -> additive. Required: without it, this
  machine's 54 global skills load into the product agent.
- `--no-prompt-templates` + explicit `--prompt-template` -> additive. Pass it.
- `--no-extensions` + explicit `--extension` -> additive per pi's own help.
- `--no-context-files` -> always pass it, so no `AGENTS.md` reaches the product.
- `--no-themes` -> **unverified**. Themes are TUI-only and invisible to
  `get_commands`, and `--use-theme` does not error on a missing theme. Do not
  pass an unverified `--no-*` flag: silently dropping a declared resource is
  worse than leaving discovery open.

Use `get_commands` as the provenance check after adding any command-shaped
resource. It catches two failure modes that produce no error: an `AGENTS.md`
picked up as a prompt template, and two sources claiming one slash name (which
makes the invocation return nothing at all).
