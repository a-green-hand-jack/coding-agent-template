FROM node:22-bookworm-slim AS builder
ARG AGENT_NAME=hewo
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates git python3 python3-venv python3-pip && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --break-system-packages --no-cache-dir uv
WORKDIR /opt/agent
COPY src /opt/agent/src
COPY distribution /opt/agent/distribution
RUN AGENT_NAME=$AGENT_NAME PREFIX=/opt/install SKIP_RUNTIME_INSTALL=1 /opt/agent/distribution/install.sh

FROM node:22-bookworm-slim AS runtime
ARG AGENT_NAME=hewo
ARG OPENCODE_VERSION=latest
ARG CODEX_VERSION=latest
ARG CLAUDE_CODE_VERSION=latest
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates python3 && rm -rf /var/lib/apt/lists/*
RUN npm install --global \
  opencode-ai@${OPENCODE_VERSION} \
  @openai/codex@${CODEX_VERSION} \
  @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} \
  --no-audit --no-fund
COPY --from=builder /opt/install /opt/install
COPY --from=builder /opt/agent/distribution/container-entrypoint.sh /usr/local/bin/agent-entrypoint
RUN chmod +x /usr/local/bin/agent-entrypoint && mkdir -p /root/.codex /root/.claude /root/.local/share/opencode /run/secrets
RUN mkdir -p /workspace
WORKDIR /workspace
ENV AGENT_NAME=$AGENT_NAME
ENV PATH="/opt/install/lib/${AGENT_NAME}/environment/bin:/opt/install/bin:$PATH"
ENTRYPOINT ["/usr/local/bin/agent-entrypoint"]
