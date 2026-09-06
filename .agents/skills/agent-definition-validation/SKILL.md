# Agent Definition Validation

## Trigger
Use when changing any file under `src/<agent_name>` or before a release.

## Steps
1. Run `./scripts/validate-definition.sh <agent_name>`.
2. Run `./tests/install/test-install.sh`.
3. Build and run the Docker smoke path with credentials supplied only at runtime.
4. Inspect the resulting artifact and record evidence in `.agents/memory/`.

## Rules
Never copy `.agents/`, raw sessions, or secrets into a release image. Never bypass the public installation path.

## Exit condition
Validation passes and the evidence is recorded without credentials.
