#!/bin/bash
# create-tag.sh — Create an annotated Git tag and push to origin.
#
# Reads: .env_versions  (APP_VERSION, SKIP_TAG)
#        CI environment variables (git remote credentials from Woodpecker)
#
# Uses existing git credentials from CI (no hardcoded credentials).

set -eu

VERSIONS_FILE=".env_versions"

if [ ! -f "$VERSIONS_FILE" ]; then
  echo "ERROR: $VERSIONS_FILE not found. Run scripts/version.sh first."
  exit 1
fi

# shellcheck source=/dev/null
. "$VERSIONS_FILE"

if [ "${SKIP_TAG:-false}" = "true" ]; then
  echo "Skipping tag creation — commit already tagged ($APP_VERSION)"
  exit 0
fi

if [ -z "${APP_VERSION:-}" ]; then
  echo "ERROR: APP_VERSION is empty in $VERSIONS_FILE"
  exit 1
fi

git config user.email "ci@woodpecker.local"
git config user.name "Woodpecker CI"

git tag -a "$APP_VERSION" -m "Release $APP_VERSION"
git push origin "$APP_VERSION"

echo "Tag $APP_VERSION created and pushed successfully"