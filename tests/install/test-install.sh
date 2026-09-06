#!/usr/bin/env bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
AGENT_NAME=example-agent PREFIX="$tmp/prefix" ./distribution/install.sh
test -f "$tmp/prefix/lib/example-agent/agent-definition/opencode.json"
test ! -e "$tmp/prefix/lib/example-agent/agent-definition/development"
echo "install smoke passed"
