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
- Print key contents, auth.json, or run `opencode debug config` (it resolves
  `{file:...}` substitutions and can leak keys).
