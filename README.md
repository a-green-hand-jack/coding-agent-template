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

`src/<agent_name>` is the single source of behavior shipped to users. `scripts`, `docker`, `tests`, and `benchmarks` are developer infrastructure. `distribution` contains the public installer and launcher.

## Provider contract

The image contains no credentials and does not bake in a provider. Set `OPENAI_API_KEY` and model settings at `docker run` time. Pin runtime and package versions in releases for reproducibility.
