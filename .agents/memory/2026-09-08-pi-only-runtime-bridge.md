# [SUPERSEDED] Pi-only Runtime Bridge and Evaluation Loop

> 本记录已被确认的 pi-native runtime/package 分发边界取代；仅保留历史证据，不作为当前规则。
>
> 路径迁移说明：下文原始证据保持不变；当前 backend 收敛 gate 位于 `.agents/scripts/check-pi-only-backend.py`，不是历史的 `scripts/` 路径。

Date: 2026-09-08 (pi 0.85.1 `@earendil-works/pi-coding-agent`). Secret-free: no credential was read and no provider request was
made while producing any of this.

## What changed

The product Agent converged to **pi and only pi**, and stopped being flattened
into one system prompt. `src/hewo/runtime/package.json` is now the single
source of truth for what the runtime loads; the launcher hands each resource to
pi's own loader. A development-only `agent-evaluation-loop-design` skill now
carries the contract, diagrams, comparator and self-bootstrap protocol.

## Verified pi facts worth not re-deriving

- Loaders: `--skill`, `--prompt-template`, `--theme`, `--extension` (all
  repeatable); `--tools` is a **single comma-separated argument, not
  repeatable**, and it constrains extension and custom tools too — a new
  extension tool that is missing from the allowlist is silently unavailable.
- `--append-system-prompt` is repeatable, so per-file provenance survives.
  There is no reason to concatenate resources into one blob.
- The manifest key is `package.json` → `pi`, with exactly `extensions`,
  `skills`, `prompts`, `themes` (plus gallery-only `video`/`image`). **There is
  no `pi.agents`**, so agent definitions are read by our own extension.
- `--no-skills` is documented as additive with explicit `--skill`, and
  `--no-extensions` explicitly keeps `-e` working. We rely on both.
  `--no-prompt-templates` and `--no-themes` are **not** documented as additive,
  so the launcher does not combine them with explicit loads.
- Extensions load through jiti, so `.ts` ships with no build step.
- Non-interactive modes (`-p`, `--mode json`, `--mode rpc`) show no trust
  prompt, which is why the launcher passes `--no-approve` explicitly.

## Capability gaps recorded rather than faked

- **No `--max-turns`.** A sub-agent turn budget is not enforceable through the
  pi CLI. We enforce wall-clock timeout, concurrency, retry and output
  truncation instead. Do not claim a turn budget.
- **No sandbox or permission-mode flag.** The retired per-run container sandbox
  setting has no pi equivalent; `--approve`/`--no-approve` are trust prompts,
  not a sandbox. Do not map one onto the other.
- **No MCP, no permission popups, no built-in todos, no core sub-agents.**
  Sub-agents and plan mode exist only through an installed package or bundled
  example. We deliberately did not depend on the machine's global
  `@tintinweb/pi-subagents`; the release must be reproducible and decoupled
  from this development machine.
- **`pi.events` RPC is in-process only.** A headless host cannot drive
  workflows over it. Do not design an external orchestrator around it.
- **The shipped theme is partial.** pi wants 53 colour tokens and the token
  names were not verifiable here, so the theme sets a name and vars and says so
  in the file. A partially-guessed `colors` map would be worse than none.

## The `.agents/` collision — the most dangerous finding

Pi discovers project skills from `.agents/skills/` in the working directory
**and its ancestors**, and pi-subagents reads `<cwd>/.agents/agents`. This
repository uses `.agents/` for *development* resources. Running pi inside this
repository, or a downstream repository built from it, can therefore load
development skills into the product agent's context — exactly the identity leak
`AGENTS.md` forbids.

Guards now in the launcher: `--no-context-files` (no `AGENTS.md`/`CLAUDE.md`
discovery), `--no-skills` and `--no-extensions` plus explicit loads,
`--no-approve`. Never place agent definitions in this repository's
`.agents/agents`.

## Defects that only appeared under verification

Each of these passed review and failed a test:

1. `node -e` consumes `--`, so the resolver got `undefined` as its root.
2. `uv pip install` in place wrote `build/`, `*.egg-info/` and `__pycache__`
   into the installed payload.
3. The definition directory contained `..`, so prefix-stripping failed and
   absolute install paths leaked into the system prompt.
4. Raw NUL bytes inside string literals made a payload source file binary and
   defeated grep/diff review. `validate-definition` now refuses that.
5. `listAgentDefinitions()` loaded `AGENTS.md` as a sub-agent definition.
6. The base self-bootstrap evaluator checked required states by substring, so a
   deleted state declaration still "matched" via its transition lines.

Lesson: a review pass would not have caught any of 1, 3, 4 or 6. Build the
adversarial check, then run it.

## Boundaries that must not drift

- `agent.yaml` is scaffold metadata. A second resource list there is a
  validation error, not a style preference.
- Manifest paths are normalized relative paths inside the definition root.
  Absolute paths, `..`, globs, shell metacharacters and symlinks are refused.
  Globs are deliberately unsupported even though pi allows them in packages.
- Capabilities and outbound network are deny-by-default; widening either is a
  product decision.
- `scripts/check-pi-only-backend.py` is the convergence gate. Its
  development-side allowlist is the review surface: entries there are files
  that may legitimately name another CLI because the machine really has one.
  Adding an entry is a decision, not a fix.
- hewo's evaluation contract is `infrastructure-smoke-only`. Its honest state
  is `SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`. Do not invent a metric for it.

## Provider-backed E2E: PASSED

Five runs through `docker/run-hewo-e2e.sh`, all reporting
`backend=pi provider=<provider> model=<model>
credential_source=--env-file <path> exit=0 mode=agent-behavior`:

1. **Greeting** - "Say hi to Ada in one short sentence." -> `Hi, Ada!`
   Identity honored (brief, includes the supplied name).
2. **Typed tools** - time + weather for Kyoto. The model called `hewo_time`
   and `hewo_weather`, reported `fixture` mode and, correctly, that Kyoto is
   `unknown-location`. It did not invent an observation.
3. **Happy path** - default location: `beijing`, 21C clear, "Data mode:
   fixture". Data-mode disclosure works as the skill requires.
4. **Sub-agents** - `hewo_subagent shape=parallel` ran `time-reporter` and
   `weather-reporter` as independent processes; both records `ok=true
   exitCode=0`.
5. **Default deny** - the same sub-agent call with `HEWO_CAPABILITIES` unset
   was refused with `capability-denied`, `invocations: 0`, no process spawned.

### How the credential actually has to be injected

A host-side credential helper produces an env file that exports the API-key
variable plus base URL for the selected provider. For a
**custom** pi provider that is not enough on its own: pi needs the provider
definition too, and it will not read the key from a mounted `auth.json` nor
from a bare environment variable. The working recipe is a **containerized
catalog** - a copy of the provider entry from `~/.pi/agent/models.json` with
`"apiKey": "$<PROVIDER>_API_KEY"` added - mounted with `--pi-models-file`,
plus the env file. That catalog contains only a variable reference, never a
key, so it is safe to generate into a temp path.

`--pi-models-file` used to be mountable only alongside `--pi-auth-file`; it is
now standalone, because a catalog is a provider definition and not a
credential.

Model availability is per-account: one listed model returned
`404 ... or Permission denied` while another worked, and a third provider
returned `402 Insufficient Balance`. Probe before assuming a listed model is
usable.

## Four defects the E2E exposed that unit tests could not

1. **False pass in our own helper.** `run-hewo-e2e.sh` printed
   `mode=agent-behavior` *before* the run, judged only by a credential flag
   being present, so two failing runs were labelled agent-behavior. The mode
   now follows the outcome: `infrastructure-only`, `agent-behavior` only on
   exit 0, otherwise `blocked`; the helper also propagates the exit code.
2. **The tool API was wrong.** We registered `{inputSchema, handler}`; pi
   0.85.1 wants `{parameters, execute(toolCallId, params, signal, ...)}`
   returning `{content, details}`. Every tool call failed with
   `Cannot read properties of undefined (reading 'properties')` - pi reading
   `parameters.properties`. `registerCommand` likewise takes the name as its
   first argument, not inside the spec.
3. **The sub-agent runner was unreachable.** `subagent.ts` was implemented and
   unit-tested but no tool exposed it, so the model could never call it. It is
   now registered as `hewo_subagent` and declared in the manifest's
   `default_tools` - required, because `--tools` is a strict allowlist that
   also governs extension tools.
4. **Agent definitions did not resolve in the container.** `agentsDirectory()`
   derived its path from the module's own location, which does not survive the
   backend's TypeScript loader. It now honors the manifest-declared
   `HEWO_AGENT_DEFINITIONS` that the launcher exports, falling back to the
   relative guess.

Every one of these passed unit tests and static gates. Only a real
provider-backed run found them.

## Secret-free facts worth keeping

- `pi --list-models` is **auth-filtered**. A clean image with no resolvable key
  prints "No models available", which looks exactly like a missing model
  catalog and is not one. `pi update --models` reports success and still
  leaves an empty store. Check the credential before chasing catalogs.
- `PI_CODING_AGENT_DIR` is honored for provider definitions.
- The custom endpoints are reachable from the container; Docker networking was
  never the blocker.

## Ambient-discovery flag matrix, measured

Settled empirically with `pi --mode rpc` + `{"type":"get_commands"}`, which
reports each command's `source` and `path`. Undocumented additivity is now
measured rather than assumed:

| Flags | Result |
| --- | --- |
| `--prompt-template <dir>` alone | templates load |
| `--no-prompt-templates` + explicit | **templates still load** - additive |
| `--no-prompt-templates` alone | none |
| `--skill <dir>` alone | 56 commands: 54 ambient host skills **plus** our 2 |
| `--no-skills` + explicit | **exactly our 2** - additive, ambient dropped |
| `--no-skills` alone | none |

So the launcher now passes `--no-prompt-templates` as well. Confirmed in the
container with the real flag set: `hewo-report` (prompt), `hewo-smoke`
(prompt), `skill:runtime-smoke`, `skill:time-and-weather` and the extension
command - six commands total, no ambient leakage.

**The `.agents/` collision is not theoretical.** Loading skills without
`--no-skills` on this development machine pulled in 54 unrelated host skills.
`--no-skills` plus explicit `--skill` reduces that to the two the runtime
declares. That flag is load-bearing, not defensive decoration.

`--no-themes` remains **unverified**: themes are TUI-only, do not appear in
`get_commands`, and `--use-theme` does not error on a missing theme, so no
non-TUI observation was possible. The launcher therefore does NOT pass it - an
unverified flag must not risk silently dropping a declared resource.

## Two more leaks the provenance check caught

1. **`prompts/AGENTS.md` became a `/AGENTS` slash command.** Prompt-template
   discovery does not skip `AGENTS.md`, so a development instruction file was
   exposed as a product command - with its heading as the description. The
   installed payload excludes every `AGENTS.md`, so the shipped product is
   clean and the container shows no `/AGENTS`; but running from a source
   checkout does expose it. Keep relying on the payload exclusion, and never
   assume a directory convention is safe just because the backend ignores it
   elsewhere.
2. **A command name collision silently produced nothing.** `hewo-report`
   existed twice - once from `registerCommand` and once as a prompt template.
   Invoking `/hewo-report` returned empty output with no error. The extension
   command is now `hewo-report-direct`, and `/hewo-report` returns the full
   report. Two sources answering one slash name is ambiguous; check
   `get_commands` for duplicates after adding either kind.
