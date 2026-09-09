#!/usr/bin/env bash
set -euo pipefail

# Publish a product Agent release: validate the definition, build the release
# archive with the correct download URL, then create a git tag and a GitHub
# release. Run this only after the real provider-backed Docker E2E and the
# consistency audit have passed; it is the mechanical final step, not behavior
# evidence.

name="${1:?usage: $0 <agent-name> <version> [--dry-run]}"
version="${2:?usage: $0 <agent-name> <version> [--dry-run]}"
shift 2 || true
dry_run=false
if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=true
  shift
fi
[[ $# -eq 0 ]] || { echo "unknown argument: $1" >&2; exit 2; }

[[ "$version" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]] || {
  echo "invalid version '$version'; use semantic versioning (X.Y.Z or X.Y.Z-pre)" >&2
  exit 2
}
tag="v${version#v}"
archive="release/$name-$version.tar.gz"
installer_asset="release/$name-$version/install.sh"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

command -v gh >/dev/null 2>&1 || { echo "gh CLI is required to publish a release" >&2; exit 2; }

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "error: worktree has uncommitted tracked changes; commit them before releasing" >&2
  exit 2
fi
if git rev-parse -q --verify "refs/tags/$tag" >/dev/null 2>&1; then
  echo "error: tag $tag already exists" >&2
  exit 2
fi

repo_slug="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
release_url="https://github.com/$repo_slug/releases/download/$tag/$name-$version.tar.gz"

if [[ "$dry_run" == true ]]; then
  echo "dry-run: RELEASE_URL=$release_url"
  echo "dry-run: ./scripts/build-release.sh $name $version"
  echo "dry-run: git tag $tag && git push origin $tag"
  echo "dry-run: gh release create $tag $archive $installer_asset --title \"$name $version\" --generate-notes"
  exit 0
fi

./scripts/validate-definition.sh "$name"
RELEASE_URL="$release_url" ./scripts/build-release.sh "$name" "$version"
[[ -f "$archive" ]] || { echo "error: expected archive $archive was not produced" >&2; exit 2; }

git tag "$tag"
git push origin "$tag"
# The baked installer is published alongside the archive so users can install
# with a single line via releases/latest/download/install.sh. It already has
# AGENT_NAME and RELEASE_URL substituted, so no environment is required.
[[ -f "$installer_asset" ]] || { echo "error: expected installer $installer_asset was not produced" >&2; exit 2; }
gh release create "$tag" "$archive" "$installer_asset" \
  --title "$name $version" \
  --generate-notes
