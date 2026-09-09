#!/usr/bin/env bash
# ty type-check, one invocation per Python service.
#
# Per service, not repo-wide: each has its own venv and its own src on the module
# path, so a single invocation would resolve third-party imports against the
# wrong environment. Shipped source only ([tool.ty.src] in each pyproject);
# tests pass duck-typed doubles where a concrete class is annotated.
#
# `uv run` provisions a missing venv, which is what CI needs on a fresh runner.
# Editors and GUI git clients commonly run hooks with a minimal PATH that lacks
# uv, so look in the usual install locations, then fall back to a venv that has
# already been built.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SERVICES=(api scraper mcp cube ml migrate)

UV="${UV:-$(command -v uv || true)}"
if [[ -z "$UV" ]]; then
  for candidate in \
    "$HOME/.local/bin/uv" \
    "$HOME/.cargo/bin/uv" \
    /usr/local/bin/uv \
    /opt/homebrew/bin/uv
  do
    if [[ -x "$candidate" ]]; then
      UV="$candidate"
      break
    fi
  done
fi

status=0
for service in "${SERVICES[@]}"; do
  echo "-- ty $service"
  if [[ -n "$UV" ]]; then
    "$UV" run --directory "services/$service" ty check || status=1
  elif [[ -x "services/$service/.venv/bin/ty" ]]; then
    (cd "services/$service" && ./.venv/bin/ty check) || status=1
  else
    echo "ty: uv is not on PATH and services/$service/.venv is missing." >&2
    echo "    Install uv, or run 'make sync' to build the service venvs." >&2
    status=1
  fi
done

exit "$status"
