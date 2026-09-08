---
description: Run the infrastructure smoke task and verify the named artifact.
argument-hint: [artifact-name]
---

Run the infrastructure smoke task for the artifact `$ARGUMENTS`.

Follow the `runtime-smoke` skill. If no artifact name was supplied, use
`hewo-smoke.md`.

Verify the artifact and the `hewo-tool --check` result before claiming
success. Report the checked artifact path and the outcome. Do not include
raw provider output or secret values.
