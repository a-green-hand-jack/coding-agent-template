# 1. Title and status

- Plan id: `development-machine-profile`
- Review state: **Implemented — pending final user review**
- Scope: add a reusable, self-contained, **generic** `development-machine-profile` skill to this template and use it to generate a `DevelopmentMachine.md` for this machine. The skill captures *everything that could affect product-Agent development* on the machine in one shot — host resources, runtime/toolchain, agent backends, the Harbor interface surface, and any other available services/SDKs (e.g. Lark, Hugging Face, Docker, SSH cluster access) — so a development coding agent stops re-probing the host. No product (hewo) behavior changes.

# 2. Motivation

- The development coding agent repeatedly re-discovers the machine (OS, kernel, storage, environment, CLI versions, Harbor commands, supported agent names, provider wiring, and available external services such as Lark) before it can develop or validate the product Agent.
- The goal is to record these facts once in `DevelopmentMachine.md` and to crystallize the capture procedure into a reusable skill.
- Downstream Agent repositories must be able to invoke the same skill to produce their own `DevelopmentMachine.md`, without depending on any user-level skill or on this template's machine-specific knowledge.
- The capture work is "exploration + reading": probe the host and read each tool's own documented interface (`--help`), never Harbor source code, and **discover** available capabilities rather than assuming a fixed list.

# 3. Verified current state

- Host: `user-PC`, Ubuntu 24.04.4 LTS, kernel `7.0.0-28-generic`, x86_64. This is the Linux development box (`macbook` is a separate machine reachable via Tailscale).
- Agent/task CLIs on PATH (runtime observation, secret-free): `harbor 0.20.0` (`/home/user/.local/bin/harbor`), `codex 0.153.4`, `opencode 1.18.29`, `claude 2.1.263`, `pi 0.85.1`.
- Other development-affecting capabilities present on this machine (probe targets for the generic skill):
  - External services/SDKs: `lark-cli` (`/home/linuxbrew/.linuxbrew/bin/lark-cli`, the Feishu/Lark CLI family — no `lkm` binary exists), `hf` (Hugging Face CLI), `orca` (Orca CLI), `docker`, `git`, `ssh`.
  - Runtimes/tooling: `python3` (Orca system python), `pip3`, `node`/`npm` (Linuxbrew), `go` (Linuxbrew), `uv`.
  - SSH host aliases in `~/.ssh/config` (aliases only, addresses omitted): `github.com`, `macbook`, `ibex`/`ilogin`/`glogin`/`vscode`, `epfl-haas`, `git.gewu-lab.ai`, `ubuntu_box`, `arc-e2e-loopback`, `ubuntu_p2000_e2e`, `ubuntu_p2000_exec_e2e`, `local_p2000`, `ibex-cpu`.
  - Local listening services (port + process binary name only): SSH (22), CUPS (631), Tailscale, DNS (127.0.0.53), several local `python` services on 127.0.0.1 (e.g. 7070, 1455, 8088, 8420, 8436, 42687, 32933, 36261, 39411, 39659).
- Harbor documented interface surface (from `harbor --help` + subcommand help, not source):
  - Top-level commands: `check`, `analyze`, `init`, `run`, `exec`, `publish`, `upload`, `add`, `download`, `remove`, `sync`, `view`, `adapter`, `task`, `dataset`, `job`, `hub`, `trial`, `cache`, `plugins`, `auth`, `agy`.
  - `harbor run --help --agent` enumerates supported agents (aider, antigravity-cli, claude-code, cline-cli, codex, computer-1, copilot-cli, cursor-cli, devin, dspy-rlm, ..., swe-agent, nemo-agent, rovodev-cli, trae-agent, vibe, acp:<agent>, plus custom `module.path:ClassName` import). Full list is captured by the probe at run time.
  - Interface mapping: **workspace** = `--jobs-dir/-o` (default `jobs`); **task** = `harbor task init/download/...` + `task.toml` / `dataset.toml`; **timeout** = the five `--*-timeout-multiplier` flags; **result** = `jobs/<job>/<trial>/` layout + reward + `verifier/test-stdout.txt`; **trajectory** = `harbor analyze` / `harbor view` (per-trial trajectory files).
  - Auth/adapter surface: `harbor auth login` (GitHub OAuth) / `logout` / `status` / `key` / `org`; `harbor adapter init` / `review`; agent kwargs `--ak` / `--ae` with `${VAR}` template expansion; `--env-file`; `--allow-agent-host`.
- Existing overlapping assets that the new skill **must not depend on** (independence requirement): user-level `~/.agents/skills/harbor-apex-provider-private` (and its `references/device-facts.md`), `~/.agents/memory/harbor_benchmark_usage.md`, `ResearchWorld/DevelopmentMachine.md`, and repo-local `.agents/knowledge/provider-e2e.md`.
- Repo conventions: skills live under `.agents/skills/<name>/` and are registered in `.agents/template-content-registry.json` as `selective` with a `destination` and `adapt_required`; `PLAN-*.md` is `template-only`; every tracked path must be registered; `DevelopmentMachine.md` does not exist in this repository yet.

# 4. Pinned decisions and rejected alternatives

## Pinned decisions

- The skill is **self-contained and independent**: it probes the machine and reads each tool's own `--help` documentation only; it must not reference or import any existing skill, especially user-level skills, and must not read Harbor source code.
- The skill is **generic and discovery-driven**, organized into extensible *capability families*, not a fixed enumeration:
  1. `host` — hostname, OS/release, kernel, arch, CPU, RAM, GPU (if any), storage mounts + free space.
  2. `runtime` — `$SHELL`, package managers, language runtimes + versions.
  3. `toolchain` — discovered development-relevant CLIs on PATH with versions (tolerant of missing/failing `--version`).
  4. `agent-backends` — codex, opencode, claude, pi, harbor, orca (versions + roles + top-level command surface).
  5. `external-services` — Lark (`lark-cli`), Hugging Face (`hf`), Docker daemon, git remotes, SSH host aliases (aliases only, addresses omitted), local listening services (port + process binary name only).
  6. `documented-interfaces` — per-tool `--help` command/flag surface, with the Harbor workspace/task/timeout/result/trajectory mapping called out explicitly.
  7. `credential-surface` — secret-free: injection flags, environment-variable **names**, auth-file paths (metadata only), and provider discovery guidance (`opencode models <provider>`, `pi --list-models`).
  8. `evidence-status` — operator-confirmed smoke results per agent × provider × model.
  Adding a new capability = adding one probe section + one schema section; the renderer and doc template stay stable.
- Skill location: `.agents/skills/development-machine-profile/`, registered `selective` so downstream repositories opt in and generate their own machine profile. The skill itself is machine-agnostic.
- `DevelopmentMachine.md` is generated at the repository root by the skill, and is registered `template-only` (this template's own machine facts; downstream repositories generate their own).
- Non-probeable facts (provider endpoints, model-id observations, smoke-evidence status) live in a repo-local, secret-free, operator-maintained facts file `.agents/knowledge/development-machine-facts.md` (`downstream-owned`). The renderer merges probed facts + this file into `DevelopmentMachine.md`.
- Secret safety is a hard rule, baked into the skill, schema, and scripts: no credentials anywhere; the probe runs only `--version` / `--help` / `command -v` / OS, storage, and port queries / environment-variable **existence** checks / SSH **alias** listing; smoke command shapes use `${VAR}` expansion only; never print secret values, never `opencode debug config`, never read key files, never record listening-process command lines (process name only).

## Rejected alternatives

- A fixed, Harbor-only enumeration (too narrow; misses Lark, Docker, HF, cluster access, and future services).
- Importing user-level Harbor skills/memory into the new skill (violates independence).
- Baking machine-specific endpoints/model observations into the skill's `references/` (makes the skill non-generic and non-reusable downstream).
- Reading Harbor implementation source code to learn its interface (forbidden; use documented `--help` surface only).
- Dumping every binary on PATH indiscriminately (noise); the probe curates to development-relevant capability families.
- Recording SSH `HostName` addresses or listening-process command lines (unnecessary and potentially sensitive; aliases and process names suffice).
- Running a live provider-backed smoke during capture by default (spends credits and needs secrets); smoke-evidence status is recorded from the facts file instead, with live runs kept separate from the repository.

# 5. Non-goals

- No Harbor benchmark/trial work and no provider or adapter implementation.
- No change to product (hewo) runtime behavior.
- No credential or live-trial receipt committed to the repository (unless intentionally redacted).
- No modification of any user-level skill or memory.
- Not an exhaustive inventory of every binary or service; only development-affecting capabilities.
- Not a replacement for `.agents/knowledge/provider-e2e.md`; that file stays as-is unless the reviewer asks to consolidate it into the new facts file.

# 6. Work breakdown

## C1 — Scaffold the skill

**Gate:** `bash -n .agents/skills/development-machine-profile/scripts/probe-host.sh && python3 -m py_compile .agents/skills/development-machine-profile/scripts/render-profile.py`

- Create `SKILL.md` (progressive loading: usage, one-shot capture, iteration loop, secret-safety rules).
- Create `references/profile-schema.md` (the eight capability families above: what each section must contain and what is forbidden).
- Create `scripts/probe-host.sh` (read-only, discovery-driven; emits a single machine-profile JSON keyed by capability family).
- Create `scripts/render-profile.py` (JSON + facts file → `DevelopmentMachine.md`, deterministic).

## C2 — Implement and iterate the probe across all capability families

**Gate:** probe JSON validates against the schema; every family is present and non-empty.

- `host`: hostname, OS/release, kernel, arch, CPU (nproc/model), RAM, GPU (`nvidia-smi` if present), storage (`df -h`, `lsblk`).
- `runtime`: `$SHELL`, package managers (apt, brew, uv, pip, npm, go), runtimes + versions.
- `toolchain`: scan `$PATH` for development-relevant commands, record discovered CLIs with versions (tolerant).
- `agent-backends`: codex/opencode/claude/pi/harbor/orca versions + top-level command surface (`--help`).
- `external-services`: `lark-cli`, `hf`, `orca`, `docker`, git remotes, SSH host aliases (names only), listening services (port + process name only).
- `documented-interfaces`: `--help` command surface for primary tools; explicit Harbor workspace/task/timeout/result/trajectory mapping.
- `credential-surface`: injection flag names + env-var **names** + auth-file paths (metadata) + provider-discovery commands.
- `evidence-status`: placeholder section filled from the facts file (C3), not probed.

## C3 — Author the secret-free facts file

**Gate:** secret scan passes (no key values, no `sk-` tokens, no auth.json contents; only variable names, endpoints, and model ids).

- Create `.agents/knowledge/development-machine-facts.md` with operator-confirmed wiring (endpoints, env-var names, model-id observations) and smoke-evidence status (Codex/OpenCode via OpenAI-compatible Apex; Claude Code via Anthropic-compatible Apex).

## C4 — Render and iterate `DevelopmentMachine.md` to one-shot completeness

**Gate:** rendered doc contains every schema section, zero credentials; re-running the skill regenerates it without manual gap-filling.

- Render `DevelopmentMachine.md`, diff against `profile-schema.md`, extend the probe/schema/facts file, and re-render until a single invocation produces the complete document.

## C5 — Register paths and pass the template audit

**Gate:** `python3 scripts/check-template-registry.py`

- Register `.agents/skills/development-machine-profile/` as `selective` (destination same, `adapt_required` empty/minimal).
- Register `DevelopmentMachine.md` as `template-only`; register `.agents/knowledge/development-machine-facts.md` as `downstream-owned`; register `PLAN.md` as `template-only` (the `PLAN-*.md` pattern does not match `PLAN.md`).

## C6 — Final review and evidence report

**Gate:** user review approves the plan result.

- Report which facts came from the probe, which from operator confirmation, and which are smoke-evidence status; confirm the skill has zero references to other skills and user-level paths; confirm every capability family (including Lark and other external services) is captured.

# 7. File map

Add:
- `.agents/skills/development-machine-profile/SKILL.md`
- `.agents/skills/development-machine-profile/references/profile-schema.md`
- `.agents/skills/development-machine-profile/scripts/probe-host.sh`
- `.agents/skills/development-machine-profile/scripts/render-profile.py`
- `.agents/knowledge/development-machine-facts.md`
- `DevelopmentMachine.md` (generated)
- `PLAN.md` (this file; temporary, removed after merge)

Modify:
- `.agents/template-content-registry.json`

# 8. Acceptance criteria

- A single invocation of the skill produces a complete `DevelopmentMachine.md` without the operator re-probing the machine.
- The document records every development-affecting capability: host identity (kernel/storage/environment/GPU), runtime/toolchain and agent CLI versions, the Harbor interface surface (workspace/task/timeout/result/trajectory), supported agent names, external services (Lark, Hugging Face, Docker, SSH cluster access), documented auth patterns, and evidence status — with zero credentials.
- Secret safety holds: no key values, no auth payloads, no listening-process command lines, no SSH addresses, no `opencode debug config`; smoke command shapes use `${VAR}` expansion only.
- The skill is discovery-driven across the capability families, not a fixed list; adding a future service is a localized extension.
- The skill has no dependency on any existing skill, especially user-level skills, and reads only `--help` documentation (no Harbor source).
- Downstream repositories can invoke the skill (registered `selective`) to generate their own `DevelopmentMachine.md`.
- `python3 scripts/check-template-registry.py` passes.

# 9. Verification

- `bash -n .agents/skills/development-machine-profile/scripts/probe-host.sh`
- `python3 -m py_compile .agents/skills/development-machine-profile/scripts/render-profile.py`
- Run the probe and confirm the JSON is well-formed and complete against the schema (all eight families).
- Confirm the probe actually captures this machine's non-Harbor capabilities: `lark-cli`, `hf`, `orca`, `docker`, SSH aliases, listening services.
- Secret scan of `DevelopmentMachine.md` and `.agents/knowledge/development-machine-facts.md`.
- `python3 scripts/check-template-registry.py`
- `git diff --check`
- Grep the skill tree for references to `~/.agents`, `harbor-apex-provider-private`, and other skill names to confirm independence.

# 10. Risks and open items

- Non-probeable facts (endpoints, model observations, evidence status) depend on the operator-maintained facts file; if it goes stale, the document goes stale. Mitigation: date-stamp the file and include re-run guidance.
- Harbor's `--agent` enum and flag surface, and other tools' `--help` surfaces, may change across versions; the probe records them as runtime observations, so the document reflects the installed version.
- Over-capture: a naive PATH scan could dump hundreds of binaries. Mitigation: curate to development-relevant capability families and record only discovered, relevant CLIs.
- Sensitivity leaks: listening-process command lines and SSH `HostName` addresses can contain secrets; the probe records only port + process name and SSH aliases.
- "lkm" was not found as a binary; the Feishu/Lark family is exposed as `lark-cli`. If the user means a different service, the reviewer should correct the example in section 3.
- `PLAN.md` is not covered by the existing `PLAN-*.md` registry pattern; C5 adds an explicit `template-only` entry for it (or the file is removed after merge).
- Independence must be enforced, not assumed: the verification grep guards against accidental imports of user-level paths.

# 11. Reviewer dispositions

| Finding | Reviewer(s) | Disposition | Rationale |
| --- | --- | --- | --- |
| Pending user review | user | deferred | The plan is intentionally presented for user review before implementation. |

# 12. Unit execution log

| Commit | Status |
| --- | --- |
| C0 | plan authored / approved by user |
| C1 | implemented / gate-passed (`bash -n`, `py_compile`) |
| C2 | implemented / probe covers all eight capability families (host, runtime, toolchain, agent-backends, external-services, documented-interfaces, credential-surface) |
| C3 | implemented / facts file secret-free, secret scan clean |
| C4 | implemented / `DevelopmentMachine.md` rendered complete, one-shot re-run reproduces |
| C5 | implemented / registry entries added, `check-template-registry.py` passes |
| C6 | report delivered / awaiting user review |
