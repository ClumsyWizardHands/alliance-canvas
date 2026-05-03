#!/usr/bin/env bash
# Same as start.sh but with backend reload mode for hot iteration.

set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOGS="$HOME/.alliance-canvas/logs"
mkdir -p "$LOGS"

if [ ! -d "$REPO/.venv" ]; then
  python3.11 -m venv "$REPO/.venv"
  "$REPO/.venv/bin/pip" install --upgrade pip --quiet
  "$REPO/.venv/bin/pip" install -r "$REPO/backend/requirements.txt" --quiet
fi

(
  cd "$REPO"
  PYTHONUNBUFFERED=1 ./.venv/bin/uvicorn backend.main:app \
    --host 127.0.0.1 --port 5181 --reload \
    > >(tee -a "$LOGS/backend.log") \
    2> >(tee -a "$LOGS/backend.stderr.log" >&2)
) &
BACKEND_PID=$!

if [ ! -d "$REPO/frontend/node_modules" ]; then
  (cd "$REPO/frontend" && npm install --silent)
fi

(
  cd "$REPO/frontend"
  npm run dev \
    > >(tee -a "$LOGS/frontend.log") \
    2> >(tee -a "$LOGS/frontend.stderr.log" >&2)
) &
FRONTEND_PID=$!

trap "kill -TERM $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM

echo "  dev backend:  http://localhost:5181 (auto-reload)"
echo "  dev frontend: http://localhost:5180"
wait
