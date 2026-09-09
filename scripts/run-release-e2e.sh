#!/usr/bin/env bash
set -euo pipefail
name="${1:-hewo}"; version="${2:-0.1.0}"; shift 2
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/hewo-release-e2e.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT
"$root/scripts/build-release.sh" "$name" "$version" >/dev/null
tar -xzf "$root/release/$name-$version.tar.gz" -C "$tmp"
rel="$tmp/$name-$version"
cat >"$tmp/Dockerfile" <<EOF
FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --break-system-packages --no-cache-dir uv
RUN npm install --global @earendil-works/pi-coding-agent@latest --ignore-scripts --no-audit --no-fund
COPY $name-$version /opt/release
RUN PREFIX=/opt/install SKIP_RUNTIME_INSTALL=1 AGENT_NAME=$name /opt/release/install.sh && mkdir -p /workspace /root/.pi/agent
COPY $name-$version/pi-invocation.sh /usr/local/lib/$name/pi-invocation.sh
COPY $name-$version/pi-invocation.sh /usr/local/bin/agent-entrypoint
RUN chmod +x /usr/local/lib/$name/pi-invocation.sh /usr/local/bin/agent-entrypoint
ENV PATH="/opt/install/lib/$name/environment/bin:/opt/install/bin:\$PATH"
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/agent-entrypoint"]
EOF
docker build -q -f "$tmp/Dockerfile" -t "${name}:release-e2e" "$tmp" >/dev/null
exec "$root/docker/run-hewo-e2e.sh" --image "${name}:release-e2e" --no-build "$@"
