#!/usr/bin/env bash
set -euo pipefail
AGENT_NAME="${AGENT_NAME:-example-agent}"
PREFIX="${PREFIX:-$HOME/.local}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$PREFIX/lib/$AGENT_NAME" "$PREFIX/bin"
test -d "$ROOT/src/$AGENT_NAME/runtime"
mkdir -p "$PREFIX/lib/$AGENT_NAME/agent-definition"
tar -C "$ROOT/src/$AGENT_NAME/runtime" --exclude=AGENTS.md -cf - . | tar -C "$PREFIX/lib/$AGENT_NAME/agent-definition" -xf -
sed "s/__AGENT_NAME__/$AGENT_NAME/g" "$ROOT/distribution/launcher" > "$PREFIX/bin/$AGENT_NAME"
chmod +x "$PREFIX/bin/$AGENT_NAME"
