#!/usr/bin/env bash
#
# serve.sh — local development server for the portfolio site.
#
# HOW TO RUN:
#   bash scripts/serve.sh                # serves on http://localhost:8080
#   PORT=8099 bash scripts/serve.sh      # serves on http://localhost:8099
#
# HOW TO STOP:
#   Press Ctrl+C in the terminal where the server is running.
#
# The server always serves the project root (the parent directory of scripts/),
# regardless of the directory you invoke it from.

set -euo pipefail

# Resolve the project root: <repo>/scripts/serve.sh -> <repo>
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

PORT="${PORT:-8080}"

if command -v python >/dev/null 2>&1; then
  PY="python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "error: python was not found in PATH" >&2
  exit 1
fi

echo "Serving ${ROOT_DIR}"
echo "URL:  http://localhost:${PORT}/"
echo "Stop: Ctrl+C"
echo

exec "${PY}" -m http.server "${PORT}"
