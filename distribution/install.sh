#!/usr/bin/env bash
set -euo pipefail

AGENT_NAME="${AGENT_NAME:-example-agent}"
PREFIX="${PREFIX:-$HOME/.local}"
OPENCODE_VERSION="${OPENCODE_VERSION:-latest}"
RELEASE_URL="${RELEASE_URL:-${AGENT_RELEASE_URL:-__RELEASE_URL__}}"

[[ "$AGENT_NAME" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]] || {
  echo "invalid agent name: $AGENT_NAME" >&2
  exit 2
}

script_path="${BASH_SOURCE[0]:-}"
script_dir=""
if [[ -n "$script_path" && -f "$script_path" ]]; then
  script_dir="$(cd "$(dirname "$script_path")" && pwd)"
fi

source_runtime=""
release_root=""
if [[ -n "$script_dir" && -d "$script_dir/../src/$AGENT_NAME/runtime" ]]; then
  source_runtime="$(cd "$script_dir/../src/$AGENT_NAME/runtime" && pwd)"
elif [[ -n "$script_dir" && -d "$script_dir/agent-definition" ]]; then
  release_root="$script_dir"
fi

# A downloaded installer is intentionally only a bootstrapper. It fetches a
# release archive and then re-enters the archive's self-contained installer;
# it never needs access to the development repository.
if [[ -z "$source_runtime" && -z "$release_root" ]]; then
  if [[ "$RELEASE_URL" == __RELEASE_URL__ || -z "$RELEASE_URL" ]]; then
    cat >&2 <<'EOF'
This installer is a source checkout or release bootstrapper.
Set RELEASE_URL to a published Agent release archive when piping install.sh
from the network, for example:
  RELEASE_URL=https://example.invalid/releases/hewo-0.1.0.tar.gz bash install.sh
EOF
    exit 2
  fi
  command -v curl >/dev/null 2>&1 || { echo "curl is required to download the Agent release" >&2; exit 2; }
  download_dir="$(mktemp -d)"
  trap 'rm -rf "$download_dir"' EXIT
  curl --fail --silent --show-error --location "$RELEASE_URL" -o "$download_dir/release.tar.gz"
  tar --extract --gzip --no-same-owner -f "$download_dir/release.tar.gz" -C "$download_dir"
  release_install="$(find "$download_dir" -mindepth 2 -maxdepth 3 -type f -name install.sh -print -quit)"
  [[ -n "$release_install" ]] || { echo "release archive does not contain install.sh" >&2; exit 2; }
  AGENT_NAME="$AGENT_NAME" PREFIX="$PREFIX" OPENCODE_VERSION="$OPENCODE_VERSION" \
    "$release_install"
  exit 0
fi

mkdir -p "$PREFIX/lib/$AGENT_NAME" "$PREFIX/bin"
definition_dir="$PREFIX/lib/$AGENT_NAME/agent-definition"
mkdir -p "$definition_dir"
if [[ -n "$source_runtime" ]]; then
  tar -C "$source_runtime" --exclude=AGENTS.md --exclude=node_modules --exclude=package.json --exclude=package-lock.json -cf - . | tar -C "$definition_dir" -xf -
  launcher_source="$script_dir/launcher"
  version="dev"
else
  tar -C "$release_root/agent-definition" --exclude=AGENTS.md --exclude=node_modules --exclude=package.json --exclude=package-lock.json -cf - . | tar -C "$definition_dir" -xf -
  launcher_source="$release_root/launcher"
  version="$(sed -n 's/.*"version":"\([^"]*\)".*/\1/p' "$release_root/release-manifest.json" | head -n 1)"
  version="${version:-unknown}"
fi

sed -e "s/__AGENT_NAME__/$AGENT_NAME/g" "$launcher_source" > "$PREFIX/bin/$AGENT_NAME"
chmod +x "$PREFIX/bin/$AGENT_NAME"
printf '{"agent":"%s","version":"%s","provider":"runtime-injected"}\n' \
  "$AGENT_NAME" "$version" > "$PREFIX/lib/$AGENT_NAME/release-manifest.json"

# Source-mode Docker builds install OpenCode in the final image. A release
# installation uses npm only when the user has no existing OpenCode binary;
# this keeps OpenCode hidden behind the product command without requiring a
# separate manual OpenCode installation step.
if [[ -z "${SKIP_OPENCODE_INSTALL:-}" ]] && ! command -v opencode >/dev/null 2>&1; then
  command -v npm >/dev/null 2>&1 || {
    echo "Node.js/npm is required to install the bundled OpenCode runtime" >&2
    exit 2
  }
  npm install --prefix "$PREFIX/lib/$AGENT_NAME/opencode" "opencode-ai@$OPENCODE_VERSION" \
    --no-audit --no-fund >/dev/null
fi
