#!/bin/bash
# version.sh — Determine the next semantic version based on Git tags
#               and conventional commit messages.
#
# Reads:   CI_COMMIT_MESSAGE (Woodpecker env) or last commit message
# Writes:  .env_versions  (APP_VERSION, SKIP_TAG)
# Outputs: version info to stdout
#
# SemVer rules:
#   - Only tags matching vX.Y.Z are considered.
#   - On first run (no tags) → v0.1.0
#   - If current commit already has a release tag → idempotent (SKIP_TAG=true)
#   - Bump rules (conventional commits):
#       * "BREAKING CHANGE" or trailing "!"    → MAJOR bump (vX+1.0.0)
#       * "feat:"                              → MINOR bump (vX.Y+1.0)
#       * anything else                        → PATCH bump (vX.Y.Z+1)

set -eu

VERSIONS_FILE=".env_versions"

# ── helpers ────────────────────────────────────────────────────────

fetch_tags() {
  git fetch --tags --force 2>/dev/null || true
}

find_latest_tag() {
  git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n1
}

find_tag_at_head() {
  git tag --points-at HEAD | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n1
}

get_commit_message() {
  # Woodpecker exposes CI_COMMIT_MESSAGE; fall back to git log
  if [ -n "${CI_COMMIT_MESSAGE:-}" ]; then
    echo "$CI_COMMIT_MESSAGE"
  else
    git log -1 --pretty=%B
  fi
}

classify_bump() {
  local msg="$1"

  # Conventional Commits: "!" or "BREAKING CHANGE" → major
  if echo "$msg" | grep -qiE 'BREAKING[_-]CHANGE|!:' ; then
    echo "major"
    return
  fi

  # Extract the commit type (scope is optional): type(scope):
  local type
  type=$(echo "$msg" | sed -nE 's/^([a-zA-Z]+)(\([^)]*\))?!?:.*/\1/p')

  case "$type" in
    feat) echo "minor" ;;
    *)    echo "patch" ;;
  esac
}

bump_version() {
  local current_tag="$1"
  local bump_type="$2"

  local version_str="${current_tag#v}"
  IFS='.' read -r major minor patch <<< "$version_str"

  case "$bump_type" in
    major)
      major=$((major + 1))
      minor=0
      patch=0
      ;;
    minor)
      minor=$((minor + 1))
      patch=0
      ;;
    patch)
      patch=$((patch + 1))
      ;;
  esac

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

# ── main ───────────────────────────────────────────────────────────

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

  local commit_msg
  commit_msg=$(get_commit_message)

  local bump_type
  bump_type=$(classify_bump "$commit_msg")
  echo "Commit classification: $bump_type bump"

  local latest_tag
  latest_tag=$(find_latest_tag)

  if [ -z "$latest_tag" ]; then
    # No tags exist — start from v0.1.0, but obey the commit type
    case "$bump_type" in
      major) latest_tag="v0.0.0" ;;
      minor) latest_tag="v0.0.0" ;;
      patch) latest_tag="v0.0.0" ;;
    esac
    local next_version
    next_version=$(bump_version "$latest_tag" "$bump_type")
    echo "No existing semver tag found — starting at $next_version"
    write_env "$next_version" "false"
    print_info "(none)" "$next_version"
    exit 0
  fi

  local next_version
  next_version=$(bump_version "$latest_tag" "$bump_type")
  write_env "$next_version" "false"
  print_info "$latest_tag" "$next_version"
}

main