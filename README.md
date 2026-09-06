# OpenCode Agent Template

Public template for building installable, container-verified agents. The agent definition lives in `src/<agent_name>`; tooling, dependencies, provider configuration, and evaluation stay outside it.

```bash
cp .env.example .env
./scripts/validate-definition.sh example-agent
docker build --build-arg AGENT_NAME=example-agent -t example-agent:dev -f docker/Dockerfile .
docker run --rm -it --env-file .env example-agent:dev "完成这个任务"
```

The CLI E2E helper accepts any OpenCode provider and model without requiring manual exports:

```bash
./docker/run-e2e.sh --provider openai --model gpt-5.6 --api-key-env OPENAI_API_KEY "完成这个任务"
```

For a short-lived read-only provider runtime bundle, create it and pass it to Docker:

```bash
bundle=$(mktemp -d)
./scripts/create-provider-bundle.sh openai gpt-5.6 OPENAI_API_KEY "$bundle"
./docker/run-e2e.sh --provider openai --model gpt-5.6 --bundle "$bundle" "完成这个任务"
rm -rf "$bundle"
```

The bundle is mode `0700`, its credential is mode `0600`, and Docker mounts it read-only at `/run/provider-bundle`. It contains only the selected provider metadata and one credential, never the host `HOME` or any CLI authentication database.

Use `--api-key-stdin` when the key should not appear in shell history, or `--env-file PATH` for a provider-specific environment file. Run `./docker/run-e2e.sh --help` for all options.

Never commit provider keys. Credentials are injected at runtime through environment variables or Docker secrets. `docker/run-e2e.sh` automatically forwards provider variables already exported in the development shell and also loads `.env` when present; it does not copy OpenCode, Codex, or Claude Code credential files into the image.

## Layout

`src/<agent_name>/runtime` is the product Agent definition shipped to users. The coding Agent that develops this template uses `AGENTS.md` and `.agents/` for reusable development memory, knowledge, skills, and workflows. `scripts`, `docker`, and `benchmarks` are template infrastructure. `distribution` contains the public installer and launcher.

## Provider contract

The image contains no credentials and does not bake in a provider. The E2E helper passes the selected provider, model, and provider key at runtime. It supports arbitrary provider names using `<PROVIDER>_API_KEY`, plus explicit key variables and env files. The entrypoint fails closed when the selected provider key is missing. Pin runtime and package versions in releases for reproducibility.

Provider ownership is explicit: OpenCode tests cover the OpenCode-compatible GPT and DeepSeek providers; Codex tests cover the configured Codex profiles; Claude Code owns the Apex Claude integration. `apex-claude` must not be configured or tested through OpenCode.

## Create a new agent

```bash
cp -R src/example-agent src/my-agent
./scripts/validate-definition.sh my-agent
```

Replace `src/example-agent` with the definition for the Agent you are building. Keep this template's own development instructions in `AGENTS.md` and `.agents/`; do not put template workflow instructions inside `src/<agent_name>`.

Use `scripts/build-release.sh` to produce a bundle containing only runtime behavior. Record release and E2E evidence in the relevant GitHub issue and run `scripts/collect-trace.sh` before storing trajectory evidence.

`benchmarks/` contains a benchmark contract and placeholders for representative tasks and verifiers. Replace them with general user tasks, never grader-specific hacks.

## Development environments

The template supports both ecosystems. Python tooling is declared in `pyproject.toml` (with `requirements-dev.txt` for pip users); run `./scripts/setup-dev.sh` to create `.venv` and install development dependencies. TypeScript tooling is declared in `package.json` and `tsconfig.json`; use `npm ci` when a lockfile is present. These environments are for the coding Agent and validation scripts only. They are not copied into `src/<agent_name>/runtime/` or shipped to end users.

The Dockerfile is multi-stage. Its builder may read the repository, but the final runtime image copies only the installed product runtime and launcher. Template development resources, tests, benchmarks, `AGENTS.md`, and `.agents/` cannot be reached from the user container.
