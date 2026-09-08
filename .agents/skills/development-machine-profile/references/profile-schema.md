# Profile schema

> **Role of this document**
> - **Audience:** the development coding agent extending the host probe or checking a rendered profile for completeness.
> - **Authority:** normative. It is the source of truth for what each capability family must contain and what is forbidden.
> - **Tone:** specification-style; field tables naming the source command and whether the field is required.
> - **Language:** English.
> - **Contains:** the eight capability families and their fields, the forbidden-content rules, the operator facts file schema, and the output section order.
> - **Excludes:** when and how to run the capture (see `.agents/skills/development-machine-profile/SKILL.md`), and any actual machine values (see `.agents/knowledge/development-machine-facts.md` and `DevelopmentMachine.md`).

Source of truth for the `development-machine-profile` skill. The probe emits
machine-profile JSON keyed by the eight capability families below; the renderer
writes `DevelopmentMachine.md` from that JSON plus the operator facts file.

Every field is **secret-free**. A field that cannot be captured without a
credential value must be left out, not approximated.

## Capability families

### 1. `host`

| Field | Source | Required |
| --- | --- | --- |
| `hostname` | `hostname` | yes |
| `os` | `/etc/os-release` PRETTY_NAME | yes |
| `kernel` | `uname -r` | yes |
| `arch` | `uname -m` | yes |
| `cpu_model` | `/proc/cpuinfo` model name (first) | yes |
| `cpu_cores` | `nproc` | yes |
| `ram_total` | `/proc/meminfo` MemTotal | yes |
| `gpu` | `nvidia-smi --query-gpu=name,memory.total` or `"none"` | yes |
| `storage` | `df -h` (exclude tmpfs/devtmpfs/squashfs) → list of `{filesystem, size, avail, use%, mount}` | yes |

### 2. `runtime`

| Field | Source | Required |
| --- | --- | --- |
| `shell` | `$SHELL` | yes |
| `package_managers` | presence of `apt brew uv pip3 pip npm go cargo` | yes |
| `runtimes` | `python3 node npm go uv` versions | yes |

### 3. `toolchain`

List of `{name, path, version}` for every **present** command in a curated,
development-relevant set (git, docker, ssh, make, gcc, g++, clang, cmake,
curl, wget, jq, rsync, tar, unzip, zip, tmux, htop, tailscale, python3, pip3,
node, npm, go, uv, cargo, rustc, hf, orca, codex, opencode, claude, pi,
harbor, lark-cli). Missing commands are omitted, not fabricated.

### 4. `agent_backends`

- `codex`, `opencode`, `claude`, `pi`, `harbor`, `orca`: `{path, version, role}`.
- `harbor.supported_agents`: the `--agent` enumeration from
  `harbor run --help` (captured verbatim as a runtime observation).

### 5. `external_services`

- `lark_cli` `{path, version}` — Feishu/Lark CLI.
- `hf` `{path, version}` — Hugging Face CLI.
- `orca` `{path, version}` — Orca CLI.
- `docker` `{path, version, daemon}` — daemon reachability (running / not-accessible).
- `ssh_hosts`: `Host` aliases from `~/.ssh/config` (names only; omit wildcard
  entries and `HostName` addresses).
- `listening_services`: `{addr, port, proc}` from `ss -tlnp` — process binary
  name only, never command-line arguments.
- `cloud_services`: `{name, endpoint, env, env_present, http_status}` — a
  secret-free reachability probe (GET, HTTP status only, no body, no auth) of
  a curated list of documented public services, plus existence of their
  documented credential env-var name.

### 6. `documented_interfaces`

`--help` text (truncated) captured from the primary tools: `harbor` and its
subcommands `run auth adapter task job trial dataset analyze view`, plus
`lark-cli`, `hf`, and `docker`. These are runtime observations and may change
with the installed versions.

### 7. `credential_surface`

Probed part: existence (`set` / `unset`) of curated secret environment-variable
**names** only (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
`OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL`, `CODEX_AUTH_JSON_PATH`, `HF_TOKEN`,
`HUGGING_FACE_HUB_TOKEN`, `DOCKER_HOST`, `GITHUB_TOKEN`). Never the values.

Operator part (facts file): per tool/family — `env_vars`, `endpoint`,
`auth_files` (metadata paths only), `discovery_commands`, `notes`.

### 8. `evidence_status`

Never probed. Operator-confirmed from the facts file: a list of
`{agent, auth_mode, model, status, note}`. `status` is one of
`smoke-verified`, `provider-reached-not-satisfied`, `not-yet-verified`.
Live trial receipts stay out of the repository unless intentionally redacted.

## Forbidden content (hard rules)

- Key values, tokens, passwords, `.env` contents, auth.json contents, account
  key contents, `sk-*`, `ghp_*`, `xox*`, or any `-----BEGIN ... PRIVATE KEY-----`.
- Listening-process command lines (arguments may contain secrets).
- SSH `HostName` addresses; store the alias only.
- Cloud-service reachability must be a bare GET recording only the HTTP status
  (no body, no `Authorization` header, no credentials).
- `opencode debug config` output or any resolved secret substitution.

## Operator facts file schema

`.agents/knowledge/development-machine-facts.md` is Markdown whose body
contains a fenced ```` ```json ```` block:

```json
{
  "credential_surface": {
    "<family>": {
      "env_vars": ["OPENAI_API_KEY"],
      "endpoint": "https://api.apexin.ai/v1",
      "auth_files": ["~/.codex/auth.json"],
      "discovery_commands": ["opencode models <provider>", "pi --list-models"],
      "notes": "human note"
    }
  },
  "evidence_status": [
    {"agent": "codex", "auth_mode": "OpenAI-compatible Apex",
     "model": "openai/gpt-5.6-sol", "status": "smoke-verified", "note": "..."}
  ],
  "services": {
    "<service>": {
      "endpoint": "https://...",
      "env_vars": ["BOHR_ACCESS_KEY"],
      "auth_header": "Authorization: Bearer <key>",
      "documented_endpoints": ["POST /search"],
      "notes": "human note"
    }
  },
  "notes": "free text"
}
```

The renderer extracts the first ```json fence and merges it; prose outside the
fence documents each field for the operator. If the file or fence is absent,
the renderer emits a clearly-marked `TODO(operator)` placeholder instead.

## Output section order

`DevelopmentMachine.md` must contain, in order: Scope (secret-safety banner +
regenerate command), Host identity, Storage, Runtime environment, Toolchain
versions, Agent backends & task executors, External services, Harbor interface
surface (workspace/task/timeout/result/trajectory), Documented provider wiring
(secret-free), Safe preflight & smoke command shapes, Evidence status,
Regeneration & maintenance.
