#!/usr/bin/env bash
# Build (or reuse) the image for a frozen run snapshot, and resolve it to an ID.
#
# The tag is a cache key, never an identity. The Dockerfile installs
# ${PI_PACKAGE}@${PI_VERSION} with PI_VERSION defaulting to "latest", refreshes
# the model catalog, and runs apt-get update twice, so the same frozen context
# built on two different days produces two different images. Only the image ID
# identifies what actually ran, which is why callers receive one and run the
# container by ID rather than by tag.
set -euo pipefail

context=""
usage() {
  cat <<'EOF'
Usage: ./.agents/scripts/build-agent-image.sh --context DIR

Build the image for a frozen snapshot unless it already exists, then resolve it.
DIR must be a snapshot produced by ./.agents/scripts/freeze-agent-run.sh.

Prints KEY=VALUE lines on stdout:
  AGENT_IMAGE     the content-addressed tag
  AGENT_IMAGE_ID  the resolved image ID; run containers by this, not the tag
EOF
}

while (($#)); do
  case "$1" in
    --context) context="${2:?missing value for --context}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$context" ]] || { usage >&2; exit 2; }
[[ -d "$context" ]] || { printf 'snapshot directory does not exist: %s\n' "$context" >&2; exit 2; }
context="$(cd "$context" && pwd)"

# .frozen.json is written last by the freeze script, so its presence is the
# completion marker: a half-copied snapshot is never built.
marker="$context/.frozen.json"
[[ -f "$marker" ]] || {
  printf 'not a completed run snapshot (no .frozen.json): %s\n' "$context" >&2
  exit 2
}

read -r agent image < <(python3 -c '
import json, re, sys
record = json.load(open(sys.argv[1], encoding="utf-8"))
agent = record.get("agent", "")
image = record.get("image", "")
# The tag comes from a generated file, but it reaches a shell command line, so
# it is re-validated here rather than trusted.
if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", agent):
    sys.exit("invalid agent name in snapshot record")
if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*:def-[0-9a-f]{12}", image):
    sys.exit("invalid image reference in snapshot record")
print(agent, image)
' "$marker")

[[ -f "$context/docker/Dockerfile" ]] || {
  printf 'snapshot has no docker/Dockerfile: %s\n' "$context" >&2
  exit 2
}

if ! docker image inspect "$image" >/dev/null 2>&1; then
  docker build --build-arg "AGENT_NAME=$agent" \
    ${PI_VERSION:+--build-arg "PI_VERSION=$PI_VERSION"} \
    ${PI_PACKAGE:+--build-arg "PI_PACKAGE=$PI_PACKAGE"} \
    -t "$image" -f "$context/docker/Dockerfile" "$context" >&2
fi

image_id="$(docker image inspect --format '{{.Id}}' "$image" 2>/dev/null || true)"
[[ -n "$image_id" ]] || { printf 'image did not resolve after build: %s\n' "$image" >&2; exit 2; }

printf 'AGENT_IMAGE=%s\n' "$image"
printf 'AGENT_IMAGE_ID=%s\n' "$image_id"
