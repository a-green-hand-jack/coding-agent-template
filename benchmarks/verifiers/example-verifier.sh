#!/usr/bin/env bash
set -euo pipefail
test -n "${ARTIFACT_PATH:?ARTIFACT_PATH is required}"
test -s "$ARTIFACT_PATH"
grep -Fq 'Product runtime' "$ARTIFACT_PATH"
grep -Fq 'Workspace access' "$ARTIFACT_PATH"
grep -Fq 'Skill loaded' "$ARTIFACT_PATH"
grep -Fq 'runtime-smoke' "$ARTIFACT_PATH"
grep -Fq 'HEWO_KNOWLEDGE_OK' "$ARTIFACT_PATH"
grep -Fq 'HEWO_TOOL_OK' "$ARTIFACT_PATH"
grep -Fq 'HEWO_WORKFLOW_OK' "$ARTIFACT_PATH"
if grep -Eiq 'not installed|not available|unable to load' "$ARTIFACT_PATH"; then
  echo "runtime-smoke skill was not loaded" >&2
  exit 1
fi
echo "hewo smoke artifact exists and contains all required headings"
