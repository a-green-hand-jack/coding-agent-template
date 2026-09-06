#!/usr/bin/env bash
set -euo pipefail
name="${1:?usage: $0 <agent-name> [version]}"
version="${2:-0.1.0}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/release/$name-$version"
rm -rf "$out"
mkdir -p "$out/agent-definition" "$out/bin"
tar -C "$root/src/$name/runtime" --exclude=AGENTS.md --exclude=node_modules --exclude=package.json --exclude=package-lock.json -cf - . | tar -C "$out/agent-definition" -xf -
cp "$root/distribution/launcher" "$out/launcher"
cp "$root/distribution/install.sh" "$out/install.sh"
cp "$root/distribution/launcher" "$out/bin/$name"
release_url="${RELEASE_URL:-__RELEASE_URL__}"
sed -i '' "s/AGENT_NAME=\"\${AGENT_NAME:-example-agent}\"/AGENT_NAME=\"\${AGENT_NAME:-$name}\"/; s/__AGENT_NAME__/$name/g; s#__RELEASE_URL__#$release_url#g" "$out/install.sh" 2>/dev/null \
  || sed -i "s/AGENT_NAME=\"\${AGENT_NAME:-example-agent}\"/AGENT_NAME=\"\${AGENT_NAME:-$name}\"/; s/__AGENT_NAME__/$name/g; s#__RELEASE_URL__#$release_url#g" "$out/install.sh"
sed -i '' "s/__AGENT_NAME__/$name/g" "$out/launcher" "$out/bin/$name" 2>/dev/null \
  || sed -i "s/__AGENT_NAME__/$name/g" "$out/launcher" "$out/bin/$name"
chmod +x "$out/bin/$name"
chmod +x "$out/install.sh" "$out/launcher"
printf '{"agent":"%s","version":"%s","definition":"src/%s/runtime","provider":"runtime-injected","opencode":"%s","development_resources":"excluded"}\n' \
  "$name" "$version" "$name" "${OPENCODE_VERSION:-latest}" > "$out/release-manifest.json"
tar -C "$root/release" -czf "$root/release/$name-$version.tar.gz" "$name-$version"
echo "built release/$name-$version.tar.gz"
