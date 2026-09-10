# Provider-backed E2E injection cheat-sheet

> **Role of this document**
> - **Audience:** the development coding agent injecting a provider credential into a Docker E2E run; the document scopes itself to that agent alone.
> - **Authority:** normative. The fail-closed rule, the injection flags and the do-not list bind every provider-backed run.
> - **Tone:** terse and operational; flags, host paths and named gotchas, never credential contents.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** the injection-flag to host-credential mapping, secret-free provider discovery, the secret-bearing paths that must never be printed, and the pi "No models available" gotcha.
> - **Excludes:** key values and auth payloads; this machine's confirmed provider facts (see `.agents/knowledge/development-machine-facts.md`), and the validation procedure that consumes these flags (see `.agents/skills/agent-definition-validation/SKILL.md`).

For the **development coding agent** only. Secret-free: flags and paths only,
never key contents. Re-verify device facts before relying on them.

## The rule

`docker/run-hewo-e2e.sh` fails closed: a task run with no injected provider
credential exits with an error and prints the injection options. Pass
`--allow-unauthenticated` only for infrastructure-only smokes (build, `--help`,
version checks). Product-behavior evidence always requires a real injected
provider.

## Injection flag -> host credential source

The helper supports pi and only pi, so these are the only credential flags it
accepts. Anything else exits 2 as an unknown option; run
`./docker/run-hewo-e2e.sh --help` for the authoritative list.

| Injection flag | Host credential source (read-only mount) |
| --- | --- |
| `--api-key-env <PROVIDER>_API_KEY` (preferred) | the named host variable, never a file |
| `--api-key-stdin` | stdin, so the key stays out of shell history |
| `--pi-auth-file PATH` | `~/.pi/agent/auth.json`; was **not** sufficient on its own for a custom provider in prior testing |
| `--pi-models-file PATH` | `~/.pi/agent/models.json`, for a custom provider catalog |
| `--bundle PATH` | a short-lived bundle from `.agents/scripts/create-provider-bundle.sh` |

## The host catalogue is not the container catalogue

Observed on a development box: `pi --list-models` on the host resolved several
configured providers while the identical command inside the clean container —
with `~/.pi/agent/auth.json` and `models.json` mounted read-only and
`PI_CODING_AGENT_DIR=/root/.pi/agent` — resolved a different subset. A run
against a host-only provider therefore failed with
`No API key found for <provider>` and was correctly classified `mode=blocked`,
while a provider resolvable inside the image succeeded
as `mode=agent-behavior`.

Enumerate inside the image you are about to run, not on the host:

```bash
docker run --rm --entrypoint bash \
  -e PI_CODING_AGENT_DIR=/root/.pi/agent \
  --mount "type=bind,src=$HOME/.pi/agent/auth.json,dst=/root/.pi/agent/auth.json,readonly" \
  --mount "type=bind,src=$HOME/.pi/agent/models.json,dst=/root/.pi/agent/models.json,readonly" \
  <image> -c 'pi --list-models'
```

## Discover providers without exposing credentials

When you need to know which providers/models actually exist on this machine,
use secret-free enumeration only — never print credential files:

- pi: `pi --list-models` and filter for the intended provider. It is
  auth-filtered, so it is a readiness probe rather than a catalog: "No models
  available" is a credential condition. Never cat `~/.pi/agent/auth.json`.
- Host private skills expose read-only, allowlisted audits:
  `pi-providers-private` -> `verify-pi-providers.sh`.
- Other coding-agent CLIs installed on this machine are development tools. Their
  provider catalogues say nothing about what the product can reach, because the
  product resolves providers through pi alone.

These are secret-bearing and must never be printed or read into a transcript:
`~/.local/share/opencode/auth.json`, `~/.codex/auth.json`,
`~/.claude/.credentials.json`, `~/.pi/agent/auth.json`,
`~/.config/opencode/account-keys/*`, any `*-key` file, any `.env`, and any
provider-bundle `credential` file. Do not rely on "a governed form only holds
`!cat` references" as a safety argument: a drifted host has already inlined
real keys. If one is accidentally printed, stop, do not repeat the value, name
the credential class, and recommend rotation.

## Host provider facts (pointers, not secrets)

- pi providers are governed by the host-level private skill
  `pi-providers-private`; read that skill for current device facts before
  choosing a provider/model. Device facts stay in that private skill, not in
  this public repository.
- Do not hardcode a provider/model that is not currently available on the host.
  Check availability first, then record the exact `backend/provider/model`
  actually used in the E2E memory entry.

## Do not

- Bake a key, `.env`, auth store, or credential bundle into the Docker image,
  Git, release archive, or `src/hewo/runtime/`.
- Print, `cat`, or read into a transcript any auth store, `*-key` file, `.env`,
  or any coding-agent CLI's resolved-configuration dump (all can contain
  resolved key material).

## pi gotcha: "No models available" is usually a credential condition

`pi --list-models` is auth-filtered. A clean container with no resolvable
provider key prints "No models available", which reads like a missing model
catalog and is not one. `pi update --models` will report success and still
leave an empty store. Check the credential before touching catalogs.

A custom provider defined in `~/.pi/agent/models.json` loads fine from a
read-only mount — pi will name the provider in its errors — but a mounted
`auth.json` did not supply its key. Use `--api-key-env` for custom providers
and treat `--pi-auth-file` as unverified for them.
