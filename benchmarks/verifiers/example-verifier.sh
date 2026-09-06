#!/usr/bin/env bash
set -euo pipefail
test -n "${ARTIFACT_PATH:?ARTIFACT_PATH is required}"
test -s "$ARTIFACT_PATH"
grep -qi 'development' "$ARTIFACT_PATH"
grep -qi 'product' "$ARTIFACT_PATH"
echo "artifact exists and is non-empty"
