FROM node:20-bookworm-slim
ARG AGENT_NAME=example-agent
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates git && rm -rf /var/lib/apt/lists/*
RUN npm install --global opencode-ai@latest
WORKDIR /opt/agent
COPY . /opt/agent
RUN AGENT_NAME=$AGENT_NAME PREFIX=/opt/install /opt/agent/distribution/install.sh
ENV PATH="/opt/install/bin:$PATH"
COPY distribution/container-entrypoint.sh /opt/agent/distribution/container-entrypoint.sh
RUN chmod +x /opt/agent/distribution/container-entrypoint.sh
ENTRYPOINT ["/opt/agent/distribution/container-entrypoint.sh"]
