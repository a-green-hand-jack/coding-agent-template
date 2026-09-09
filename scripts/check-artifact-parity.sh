#!/usr/bin/env bash
set -euo pipefail
name="${1:-hewo}"; root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
archive="$(find "$root/release" -maxdepth 1 -name "$name-*.tar.gz" -type f | sort | tail -1)"
[[ -n "$archive" ]] || { echo 'release archive missing' >&2; exit 2; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/artifact-parity.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT
tar -xzf "$archive" -C "$tmp"
release="$(find "$tmp" -type d -name runtime-package -print -quit)"
[[ -n "$release" ]] || { echo 'release runtime-package missing' >&2; exit 2; }
( cd "$root/src/$name/runtime"; find . -type f ! -name AGENTS.md ! -name CLAUDE.md -print0 | sort -z | xargs -0 sha256sum ) > "$tmp/source"
( cd "$release"; find . -type f -print0 | sort -z | xargs -0 sha256sum ) > "$tmp/release"
diff -u "$tmp/source" "$tmp/release"
echo 'artifact parity: OK'
