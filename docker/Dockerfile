FROM node:20-bookworm-slim AS builder
ARG AGENT_NAME=example-agent
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates git python3 python3-venv python3-pip && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/agent
COPY src /opt/agent/src
COPY distribution /opt/agent/distribution
RUN AGENT_NAME=$AGENT_NAME PREFIX=/opt/install SKIP_OPENCODE_INSTALL=1 /opt/agent/distribution/install.sh

FROM node:20-bookworm-slim AS runtime
ARG AGENT_NAME=example-agent
ARG OPENCODE_VERSION=latest
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates && rm -rf /var/lib/apt/lists/*
RUN npm install --global opencode-ai@${OPENCODE_VERSION} --no-audit --no-fund
COPY --from=builder /opt/install /opt/install
COPY --from=builder /opt/agent/distribution/container-entrypoint.sh /usr/local/bin/agent-entrypoint
RUN chmod +x /usr/local/bin/agent-entrypoint
RUN mkdir -p /workspace
WORKDIR /workspace
ENV AGENT_NAME=$AGENT_NAME
ENV PATH="/opt/install/bin:$PATH"
ENTRYPOINT ["/usr/local/bin/agent-entrypoint"]
