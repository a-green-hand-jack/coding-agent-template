#!/usr/bin/env bash
set -euo pipefail

# HeWo is a pi-native runtime package. The container invokes pi directly;
# there is no product-specific launcher or wrapper.
root="/opt/install/lib/${AGENT_NAME:-hewo}/runtime-package"
[[ -f "$root/package.json" ]] || { echo "runtime package is missing: $root" >&2; exit 2; }

args=(--no-context-files --no-skills --no-extensions --no-prompt-templates)
args+=(--skill "$root/skills" --prompt-template "$root/prompts" --theme "$root/themes")
args+=(--extension "$root/extensions/hewo/index.ts")
args+=(--append-system-prompt "$root/identity.md" --append-system-prompt "$root/memory-policy.md")
for file in "$root"/knowledge/*.md "$root"/workflows/*.md; do
  [[ -f "$file" ]] && args+=(--append-system-prompt "$file")
done
args+=(--tools "read,write,edit,bash,hewo_time,hewo_weather,hewo_report,hewo_subagent")

exec pi "${args[@]}" "$@"
