#!/usr/bin/env bash
# Installer for the Agent product. Backend: pi, and only pi.
set -euo pipefail

AGENT_NAME="${AGENT_NAME:-hewo}"
PREFIX="${PREFIX:-$HOME/.local}"
PI_VERSION="${PI_VERSION:-latest}"
PI_PACKAGE="${PI_PACKAGE:-@earendil-works/pi-coding-agent}"
RELEASE_URL="${RELEASE_URL:-${AGENT_RELEASE_URL:-__RELEASE_URL__}}"

[[ "$AGENT_NAME" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]] || {
  echo "invalid agent name: $AGENT_NAME" >&2
  exit 2
}

# The product supports one backend. An explicit request for anything else is an
# error, never a silent fallback.
if [[ -n "${AGENT_BACKENDS:-}" && ! "$AGENT_BACKENDS" =~ ^(pi|pi-coding-agent)$ ]]; then
  echo "invalid AGENT_BACKENDS: $AGENT_BACKENDS (this Agent supports pi only)" >&2
  exit 2
fi

script_path="${BASH_SOURCE[0]:-}"
script_dir=""
if [[ -n "$script_path" && -f "$script_path" ]]; then
  script_dir="$(cd "$(dirname "$script_path")" && pwd)"
fi

source_runtime=""
release_root=""
if [[ -n "$script_dir" && -d "$script_dir/../src/$AGENT_NAME/runtime" ]]; then
  source_runtime="$(cd "$script_dir/../src/$AGENT_NAME/runtime" && pwd)"
elif [[ -n "$script_dir" && -d "$script_dir/runtime-package" ]]; then
  release_root="$script_dir"
fi

# A downloaded installer is intentionally only a bootstrapper. It fetches a
# release archive and then re-enters the archive's self-contained installer;
# it never needs access to the development repository.
if [[ -z "$source_runtime" && -z "$release_root" ]]; then
  if [[ "$RELEASE_URL" == __RELEASE_URL__ || -z "$RELEASE_URL" ]]; then
    cat >&2 <<'USAGE'
This installer is a source checkout or release bootstrapper.
Set RELEASE_URL to a published Agent release archive when piping install.sh
from the network, for example:
  RELEASE_URL=https://example.invalid/releases/hewo-0.1.0.tar.gz bash install.sh
USAGE
    exit 2
  fi
  command -v curl >/dev/null 2>&1 || { echo "curl is required to download the Agent release" >&2; exit 2; }
  download_dir="$(mktemp -d)"
  trap 'rm -rf "$download_dir"' EXIT
  curl --fail --silent --show-error --location "$RELEASE_URL" -o "$download_dir/release.tar.gz"
  tar --extract --gzip --no-same-owner -f "$download_dir/release.tar.gz" -C "$download_dir"
  release_install="$(find "$download_dir" -mindepth 2 -maxdepth 3 -type f -name install.sh -print -quit)"
  [[ -n "$release_install" ]] || { echo "release archive does not contain install.sh" >&2; exit 2; }
  AGENT_NAME="$AGENT_NAME" PREFIX="$PREFIX" PI_VERSION="$PI_VERSION" PI_PACKAGE="$PI_PACKAGE" \
    "$release_install"
  exit 0
fi

# Install the pi-native runtime package as data. This installer deliberately does
# not install a hewo wrapper command: pi, provider, model, and credentials are
# user-owned and selected through pi's native interface/configuration.
mkdir -p "$PREFIX/lib/$AGENT_NAME"
definition_dir="$PREFIX/lib/$AGENT_NAME/runtime-package"
mkdir -p "$definition_dir"

# package.json is the runtime resource manifest and must reach the payload.
# Development instructions and installed dependencies must not.
if [[ -n "$source_runtime" ]]; then
  tar -C "$source_runtime" --exclude=AGENTS.md --exclude=CLAUDE.md --exclude=node_modules --exclude=__pycache__ --exclude='*.egg-info' --exclude=build -cf - . | tar -C "$definition_dir" -xf -
  version="dev"
else
  tar -C "$release_root/runtime-package" --exclude=AGENTS.md --exclude=CLAUDE.md --exclude=node_modules --exclude=__pycache__ --exclude='*.egg-info' --exclude=build -cf - . | tar -C "$definition_dir" -xf -
  version="$(sed -n 's/.*"version":"\([^"]*\)".*/\1/p' "$release_root/release-manifest.json" | head -n 1)"
  version="${version:-unknown}"
fi

[[ -f "$definition_dir/package.json" ]] || {
  echo "Agent resource manifest is missing from the payload: $definition_dir/package.json" >&2
  exit 2
}

# Runtime npm dependencies, when a downstream Agent declares any, are installed
# frozen and with lifecycle scripts disabled. A dependency without a lockfile is
# refused rather than resolved at install time.
declares_dependencies="$(node -e '
const fs = require("node:fs");
const manifest = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const dependencies = Object.keys(manifest.dependencies || {});
if (manifest.scripts && Object.keys(manifest.scripts).length > 0) {
  process.stderr.write("runtime package.json must not declare npm lifecycle scripts\n");
  process.exit(2);
}
process.stdout.write(dependencies.length > 0 ? "yes" : "no");
' "$definition_dir/package.json")"
if [[ "$declares_dependencies" == yes ]]; then
  [[ -f "$definition_dir/package-lock.json" ]] || {
    echo "runtime declares dependencies but ships no package-lock.json; refusing an unpinned install" >&2
    exit 2
  }
  command -v npm >/dev/null 2>&1 || { echo "npm is required to install runtime dependencies" >&2; exit 2; }
  (cd "$definition_dir" && npm ci --ignore-scripts --no-audit --no-fund >/dev/null)
fi

tools_dir="$definition_dir/tools"
if [[ -f "$tools_dir/pyproject.toml" ]]; then
  command -v uv >/dev/null 2>&1 || {
    echo "uv is required to install the Agent runtime tools" >&2
    exit 2
  }
  runtime_env_dir="$PREFIX/lib/$AGENT_NAME/environment"
  uv venv "$runtime_env_dir" --python python3 >/dev/null
  # Build from a throwaway copy so build/, *.egg-info/ and __pycache__ never
  # land in the installed Agent definition.
  tools_build_dir="$(mktemp -d)"
  cp -R "$tools_dir/." "$tools_build_dir/"
  uv pip install --python "$runtime_env_dir/bin/python" "$tools_build_dir" >/dev/null
  rm -rf "$tools_build_dir"
fi

printf '{"agent":"%s","version":"%s","provider":"runtime-injected","backend":"pi"}\n' \
  "$AGENT_NAME" "$version" > "$PREFIX/lib/$AGENT_NAME/release-manifest.json"

# Install pi only as an optional execution dependency when absent; the runtime
# package itself never supplies a product wrapper or provider configuration.
if [[ -z "${SKIP_RUNTIME_INSTALL:-}" ]]; then
  if ! command -v pi >/dev/null 2>&1; then
    command -v npm >/dev/null 2>&1 || {
      echo "Node.js/npm is required to install the pi runtime" >&2
      exit 2
    }
    npm install --prefix "$PREFIX/lib/$AGENT_NAME/runtimes/pi" "$PI_PACKAGE@$PI_VERSION" \
      --ignore-scripts --no-audit --no-fund >/dev/null
  fi
fi
