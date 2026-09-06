# OpenCode Agent Template

Public template for building installable, container-verified agents. The agent definition lives in `src/<agent_name>`; tooling, dependencies, provider configuration, and evaluation stay outside it.

```bash
cp .env.example .env
./scripts/validate-definition.sh example-agent
docker build --build-arg AGENT_NAME=example-agent -t example-agent:dev -f docker/Dockerfile .
docker run --rm -it --env-file .env example-agent:dev "完成这个任务"
```

Never commit provider keys. Credentials are injected at runtime through environment variables or Docker secrets.

## Layout

`src/<agent_name>` is the complete product Agent workspace. Its `runtime/` directory is shipped to users; `development/` holds Agent-specific design material. The coding Agent that develops this product uses `AGENTS.md` and `.agents/` for reusable development memory, knowledge, and skills. `scripts`, `docker`, `tests`, and `benchmarks` are developer infrastructure. `distribution` contains the public installer and launcher.

## Provider contract

The image contains no credentials and does not bake in a provider. Set `OPENAI_API_KEY` and model settings at `docker run` time (or use Docker secrets). The entrypoint fails closed when the selected provider key is missing. Pin runtime and package versions in releases for reproducibility.

## Create a new agent

```bash
cp -R src/example-agent src/my-agent
./scripts/validate-definition.sh my-agent
```

Edit both `runtime/` (the shipped product) and `development/` (design notes, working memory, reference knowledge, and development-only skills). Build and test only through Docker.

Use `scripts/build-release.sh` to produce a bundle containing only runtime behavior. Follow `docs/release-checklist.md` and run `scripts/collect-trace.sh` before storing trajectory evidence.

`benchmarks/` contains a benchmark contract and placeholders for representative tasks and verifiers. Replace them with general user tasks, never grader-specific hacks.
