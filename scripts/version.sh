#!/bin/bash
# version.sh — Determine the next semantic version based on Git tags.
#
# Reads:   nothing (uses git tag state)
# Writes:  .env_versions  (APP_VERSION, SKIP_TAG)
# Outputs: version info to stdout
#
# SemVer rules:
#   - Only tags matching vX.Y.Z are considered.
#   - On first run (no tags) → v0.1.0
#   - If current commit already has a release tag → idempotent (SKIP_TAG=true)
#   - Otherwise → increment PATCH.

set -eu

VERSIONS_FILE=".env_versions"

fetch_tags() {
  git fetch --tags --force 2>/dev/null || true
}

find_latest_tag() {
  git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n1
}

find_tag_at_head() {
  git tag --points-at HEAD | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n1
}

bump_patch() {
  local tag="$1"
  local version_str="${tag#v}"
  IFS='.' read -r major minor patch <<< "$version_str"
  patch=$((patch + 1))
  echo "v${major}.${minor}.${patch}"
}

write_env() {
  local version="$1"
  local skip="${2:-false}"
  cat > "$VERSIONS_FILE" <<EOF
APP_VERSION=$version
SKIP_TAG=$skip
EOF
}

print_info() {
  local current="$1"
  local next="$2"
  echo "--- Version Info ---"
  echo "Current Version: $current"
  echo "Next Version: $next"
  echo "Git Tag: $next"
}

main() {
  fetch_tags

  local existing_tag
  existing_tag=$(find_tag_at_head)

  if [ -n "$existing_tag" ]; then
    echo "Current commit already tagged: $existing_tag — skipping version bump"
    write_env "$existing_tag" "true"
    print_info "$existing_tag" "$existing_tag"
    exit 0
  fi

  local latest_tag
  latest_tag=$(find_latest_tag)

  if [ -z "$latest_tag" ]; then
    echo "No existing semver tag found — starting at v0.1.0"
    write_env "v0.1.0" "false"
    print_info "(none)" "v0.1.0"
    exit 0
  fi

  local next_version
  next_version=$(bump_patch "$latest_tag")
  write_env "$next_version" "false"
  print_info "$latest_tag" "$next_version"
}

main