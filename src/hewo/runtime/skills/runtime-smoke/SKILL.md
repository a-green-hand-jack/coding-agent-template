---
name: runtime-smoke
description: Validate an installed HeWo runtime by inspecting the workspace and writing a checked smoke artifact.
---

# Runtime Smoke

Use this skill when the user asks for an infrastructure or installation smoke
test.

1. Inspect the current workspace without reading credentials or environment
   files.
2. Confirm that the workspace is separate from the Agent definition directory.
3. Write `artifacts/hewo-smoke.md` containing the exact headings
   `Product runtime`, `Workspace access`, and `Skill loaded`.
4. Re-read the artifact and verify all three headings are present.
5. Include `HEWO_KNOWLEDGE_OK` under the Product runtime section and
   `HEWO_WORKFLOW_OK` under the Workspace access section.
6. Report only the checked artifact path and outcome; do not include raw
   provider output or secret values.
