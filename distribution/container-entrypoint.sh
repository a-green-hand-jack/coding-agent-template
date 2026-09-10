#!/usr/bin/env bash
set -euo pipefail

root="${AGENT_RUNTIME_PACKAGE:-/opt/install/lib/${AGENT_NAME:-hewo}/runtime-package}"
exec pi --no-session --no-context-files --no-extensions --no-skills --no-prompt-templates --no-themes -e "$root" "$@"
