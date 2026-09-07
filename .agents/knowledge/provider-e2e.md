# Provider-backed E2E injection cheat-sheet

For the **development coding agent** only. Secret-free: flags and paths only,
never key contents. Re-verify device facts before relying on them.

## The rule

`docker/run-hewo-e2e.sh` fails closed: a task run with no injected provider
credential exits with an error and prints the injection options. Pass
`--allow-unauthenticated` only for infrastructure-only smokes (build, `--help`,
version checks). Product-behavior evidence always requires a real injected
provider.

## Backend -> flag -> host credential source

| Backend | Injection flag(s) | Host credential source (read-only mount) |
| --- | --- | --- |
| opencode | `--auth-file` or `--api-key-env <ENV>` | `~/.local/share/opencode/auth.json` |
| codex | `--codex-auth-file` or `--api-key-env` (`OPENAI_API_KEY`) | `~/.codex/auth.json` |
| claude | `--claude-api-key-file` or `--claude-credentials-file` or `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` | key file or env; this host has no `~/.claude/.credentials.json` |
| pi | `--pi-auth-file` | `~/.pi/agent/auth.json` (+ auto-discovered `~/.pi/agent/models.json`) |

## Discover providers without exposing credentials

When you need to know which providers/models actually exist on this machine,
use secret-free enumeration only — never print credential files:

- OpenCode: `opencode models <provider>` (add `--verbose` for metadata/variants).
  Never run `opencode debug config`: it resolves `{file:...}` and prints keys.
- pi: `pi --list-models` and filter for the intended provider. Never cat
  `~/.pi/agent/auth.json`.
- Host private skills expose read-only, allowlisted audits:
  `opencode-providers-private` -> `audit-opencode-providers.sh` and
  `provider-health.sh`; `pi-providers-private` -> `verify-pi-providers.sh`.

These are secret-bearing and must never be printed or read into a transcript:
`~/.local/share/opencode/auth.json`, `~/.codex/auth.json`,
`~/.claude/.credentials.json`, `~/.pi/agent/auth.json`,
`~/.config/opencode/account-keys/*`, any `*-key` file, any `.env`, and any
provider-bundle `credential` file. Do not rely on "a governed form only holds
`!cat` references" as a safety argument: a drifted host has already inlined
real keys. If one is accidentally printed, stop, do not repeat the value, name
the credential class, and recommend rotation.

## Host provider facts (pointers, not secrets)

- OpenCode providers on this development machine are governed by the host-level
  private skill `opencode-providers-private`; the governed default model is
  `openai-evelyn/gpt-6-astra`. Read that skill for the current allowlist and
  device facts before choosing a provider/model.
- pi providers are governed by `pi-providers-private`: `apex`,
  `apex-deepseek`, `opencode-go`. Read that skill for current device facts.
- Do not hardcode a provider/model that is not currently available on the host.
  Check availability first, then record the exact `backend/provider/model`
  actually used in the E2E memory entry.

## Do not

- Bake a key, `.env`, auth store, or credential bundle into the Docker image,
  Git, release archive, or `src/hewo/runtime/`.
- Print, `cat`, or read into a transcript any auth store, `*-key` file, `.env`,
  or `opencode debug config` output (all can contain resolved key material).
