#!/usr/bin/env bash
set -euo pipefail
name="${1:-hewo}"; version="${2:-0.1.0}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/hewo-release-check.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
"$root/scripts/build-release.sh" "$name" "$version" >/dev/null
archive="$root/release/$name-$version.tar.gz"
tar -xzf "$archive" -C "$tmp"
release="$(find "$tmp" -mindepth 2 -maxdepth 2 -name install.sh -type f -print -quit)"
[[ -n "$release" ]] || { echo 'release installer missing' >&2; exit 2; }
PREFIX="$tmp/prefix" SKIP_RUNTIME_INSTALL=1 AGENT_NAME="$name" "$release" >/dev/null
[[ -x "$tmp/prefix/bin/$name" || -x "$tmp/prefix/lib/$name/pi-invocation.sh" || -f "$tmp/prefix/lib/$name/runtime-package/package.json" ]]
"$root/scripts/check-artifact-parity.sh" "$name"
echo 'release user path: OK'
