# OpenCode Agent Template

Public template for building installable, container-verified agents. The agent definition lives in `src/<agent_name>`; tooling, dependencies, provider configuration, and evaluation stay outside it.

```bash
cp .env.example .env
./scripts/validate-definition.sh example-agent
docker build --build-arg AGENT_NAME=example-agent -t example-agent:dev -f docker/Dockerfile .
docker run --rm -it --env-file .env example-agent:dev "完成这个任务"
```

Never commit provider keys. Credentials are injected at runtime through environment variables or Docker secrets. `docker/run-e2e.sh` automatically forwards provider variables already exported in the development shell and also loads `.env` when present; it does not copy OpenCode, Codex, or Claude Code credential files into the image.

## Layout

`src/<agent_name>/runtime` is the product Agent definition shipped to users. The coding Agent that develops this template uses `AGENTS.md` and `.agents/` for reusable development memory, knowledge, skills, and workflows. `scripts`, `docker`, and `benchmarks` are template infrastructure. `distribution` contains the public installer and launcher.

## Provider contract

The image contains no credentials and does not bake in a provider. Set provider credentials and model settings at `docker run` time (or use Docker secrets). The E2E helper forwards `LLM_*`, `OPENAI_*`, and `ANTHROPIC_*` variables from the host shell. The entrypoint fails closed when the selected provider key is missing. Pin runtime and package versions in releases for reproducibility.

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
