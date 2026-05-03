#!/usr/bin/env bash
# Boot Alliance Canvas backend + frontend dev servers in parallel.
# Logs to ~/.alliance-canvas/logs/ ; tails both to stdout.
# Ctrl-C kills both.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOGS="$HOME/.alliance-canvas/logs"
mkdir -p "$LOGS"

if ! pgrep -x ollama >/dev/null 2>&1; then
  echo "warning: 'ollama' process not running. Start the Ollama Mac app first."
fi

# Backend
if [ ! -d "$REPO/.venv" ]; then
  echo "Creating venv…"
  python3.11 -m venv "$REPO/.venv"
  "$REPO/.venv/bin/pip" install --upgrade pip --quiet
  "$REPO/.venv/bin/pip" install -r "$REPO/backend/requirements.txt" --quiet
fi

(
  cd "$REPO"
  PYTHONUNBUFFERED=1 ./.venv/bin/python -m backend.main \
    > >(tee -a "$LOGS/backend.log") \
    2> >(tee -a "$LOGS/backend.stderr.log" >&2)
) &
BACKEND_PID=$!

# Frontend
if [ ! -d "$REPO/frontend/node_modules" ]; then
  echo "Installing frontend deps…"
  (cd "$REPO/frontend" && npm install --silent)
fi

(
  cd "$REPO/frontend"
  npm run dev \
    > >(tee -a "$LOGS/frontend.log") \
    2> >(tee -a "$LOGS/frontend.stderr.log" >&2)
) &
FRONTEND_PID=$!

cleanup() {
  echo "Shutting down…"
  kill -TERM "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "  backend:  http://localhost:5181/api/health"
echo "  frontend: http://localhost:5180"
echo "  logs:     $LOGS"
echo ""

wait
