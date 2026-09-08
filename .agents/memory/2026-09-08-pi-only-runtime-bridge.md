# Pi-only Runtime Bridge and Evaluation Loop

Date: 2026-09-08 (Ubuntu 24.04, pi 0.85.1 `@earendil-works/pi-coding-agent`,
Node 26.5.0). Secret-free: no credential was read and no provider request was
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

## Not done

No provider-backed Docker E2E was run: no credential source was injected, so
every run here is `infrastructure-only`, never agent-behavior. The first real
E2E must report `backend=pi`, the actual provider and model, and the
credential-source flag.
