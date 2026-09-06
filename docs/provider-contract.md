# LLM Provider Contract

Provider access is an environment concern, not part of the Agent definition.

| Provider | Required variable |
| --- | --- |
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |

Pass credentials with `--env-file` or Docker secrets. Never use Docker `ARG`, source files, or build logs for secrets. Record the model, OpenCode version, base image digest, dependency lockfile, and Agent Definition revision together for reproducible runs.
