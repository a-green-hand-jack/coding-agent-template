#!/usr/bin/env bash
set -euo pipefail
name="${1:?usage: $0 <agent-name> [version]}"
version="${2:-0.1.0}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/release/$name-$version"
release_url="${RELEASE_URL:-__RELEASE_URL__}"
# Validate before touching the filesystem: a rejected invocation must not leave
# a half-created release directory behind.
if [[ -n "${AGENT_BACKENDS:-}" && ! "$AGENT_BACKENDS" =~ ^(pi|pi-coding-agent)$ ]]; then
  echo "invalid AGENT_BACKENDS: $AGENT_BACKENDS (this Agent supports pi only)" >&2
  exit 2
fi
test -f "$root/src/$name/runtime/package.json" || {
  echo "no runtime resource manifest for $name: src/$name/runtime/package.json" >&2
  exit 2
}
rm -rf "$out"
mkdir -p "$out/runtime-package"
# package.json is the runtime resource manifest and must ship. Only
# development instructions and installed dependencies are excluded.
tar -C "$root/src/$name/runtime" --exclude=AGENTS.md --exclude=CLAUDE.md --exclude=node_modules --exclude=__pycache__ --exclude='*.egg-info' --exclude=build -cf - . | tar -C "$out/runtime-package" -xf -
cp "$root/distribution/install.sh" "$out/install.sh"
test -f "$out/runtime-package/package.json" || {
  echo "release payload is missing the runtime resource manifest package.json" >&2
  exit 2
}
sed -i.bak "s/AGENT_NAME=\"\${AGENT_NAME:-hewo}\"/AGENT_NAME=\"\${AGENT_NAME:-$name}\"/; s/__AGENT_NAME__/$name/g; s#__RELEASE_URL__#$release_url#g" "$out/install.sh"
rm -f "$out/install.sh.bak"
chmod +x "$out/install.sh"
printf '{"agent":"%s","version":"%s","definition":"src/%s/runtime","provider":"runtime-injected","backend":"pi","pi":"%s","development_resources":"excluded"}\n' \
  "$name" "$version" "$name" "${PI_VERSION:-latest}" > "$out/release-manifest.json"
tar -C "$root/release" -czf "$root/release/$name-$version.tar.gz" "$name-$version"
echo "built release/$name-$version.tar.gz"
