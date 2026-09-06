#!/usr/bin/env bash
# Remove the docker-container buildx builder used by `make build-multiarch`.
# Idempotent: no-op if Docker is down or the builder does not exist.
set -euo pipefail

BUILDER="${BUILDX_BUILDER:-nba}"

if ! docker buildx inspect "$BUILDER" >/dev/null 2>&1; then
  exit 0
fi

echo "Removing buildx builder ${BUILDER}"
docker buildx rm --force "$BUILDER"
