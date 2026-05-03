#!/usr/bin/env bash
# End-to-end smoke test for Alliance Canvas.
#
# Boots the backend (only), waits for /api/health, exercises every REST endpoint
# the frontend depends on, runs one streaming chat turn against Archie via
# WebSocket, and reports pass/fail.
#
# Doesn't boot the frontend — that's a UI verification, separate concern.
# Run ./scripts/start.sh and open localhost:5180 for the visual smoke test.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PORT=5181
HEALTH_URL="http://127.0.0.1:$PORT/api/health"

PASS=0
FAIL=0
FAILURES=()

pass() { echo "  ✓ $1"; PASS=$((PASS+1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL+1)); FAILURES+=("$1"); }

echo "==> Booting backend on :$PORT"
if [ ! -d "$REPO/.venv" ]; then
  python3.11 -m venv "$REPO/.venv"
  "$REPO/.venv/bin/pip" install --upgrade pip --quiet
  "$REPO/.venv/bin/pip" install -r "$REPO/backend/requirements.txt" --quiet
fi

# Start backend in background
cd "$REPO"
"$REPO/.venv/bin/python" -m backend.main >/tmp/alliance-canvas-smoke.log 2>&1 &
BACKEND_PID=$!
trap "kill $BACKEND_PID 2>/dev/null || true" EXIT INT TERM

# Wait for /api/health
for i in $(seq 1 30); do
  if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
  echo "Backend never came up. Log tail:"
  tail -50 /tmp/alliance-canvas-smoke.log
  exit 1
fi

echo ""
echo "==> REST endpoints"

# Helper: assert a JSON-path expression evaluates truthy in the response.
# JSON is piped via stdin to avoid bash quoting issues with apostrophes / quotes.
jq_check() {
  local resp="$1" expr="$2" label="$3"
  python3 -c "
import json, sys
data = json.load(sys.stdin)
try:
    val = $expr
except Exception as e:
    print(f'expr error: {e}', file=sys.stderr); sys.exit(1)
sys.exit(0 if val else 1)
" <<< "$resp" 2>/dev/null && pass "$label" || fail "$label"
}

HEALTH=$(curl -sf "$HEALTH_URL")
jq_check "$HEALTH" "data.get('version')" "GET /api/health"
jq_check "$HEALTH" "data['ollama']['reachable']" "ollama reachable"

WS=$(curl -sf "http://127.0.0.1:$PORT/api/workspaces")
jq_check "$WS" "any(w['name']=='Default' for w in data['workspaces'])" "GET /api/workspaces lists Default"
jq_check "$WS" "any(w['name']=='Daily Harvest' for w in data['workspaces'])" "GET /api/workspaces lists Daily Harvest"

AGENTS=$(curl -sf "http://127.0.0.1:$PORT/api/agents")
jq_check "$AGENTS" "any(a['name']=='archie' for a in data['agents'])" "GET /api/agents lists archie"
jq_check "$AGENTS" "any(a['name']=='archie' and a.get('connected') for a in data['agents'])" "archie marked connected"
jq_check "$AGENTS" "any(a['name']=='atlas' for a in data['agents'])" "GET /api/agents lists atlas (stub)"
jq_check "$AGENTS" "all((not a.get('connected')) for a in data['agents'] if a['name']!='archie')" "stub agents marked not-connected"

SKILLS=$(curl -sf "http://127.0.0.1:$PORT/api/skills?workspace=Default")
jq_check "$SKILLS" "any(s['slug']=='slut-harvest' for s in data['skills'])" "GET /api/skills (Default) finds slut-harvest"
jq_check "$SKILLS" "any(s['slug']=='slut-harvest' and s.get('is_folder_format') for s in data['skills'])" "slut-harvest indexed as folder format"

DH_SKILLS=$(curl -sf "http://127.0.0.1:$PORT/api/skills?workspace=Daily%20Harvest")
jq_check "$DH_SKILLS" "any(s['slug']=='slut-harvest' for s in data['skills'])" "GET /api/skills (Daily Harvest) shows slut-harvest"
jq_check "$DH_SKILLS" "len(data['skills']) == 1" "Daily Harvest narrows skills (1 active)"

PRINCIPLES=$(curl -sf "http://127.0.0.1:$PORT/api/principles?workspace=Default")
jq_check "$PRINCIPLES" "any(p['slug']=='cep-13-ceiling-investigation' for p in data['principles'])" "GET /api/principles finds cep-13"
jq_check "$PRINCIPLES" "any(p['slug']=='cep-14-slut-minting' for p in data['principles'])" "GET /api/principles finds cep-14"

LEDGER=$(curl -sf "http://127.0.0.1:$PORT/api/ledger?n=5")
jq_check "$LEDGER" "isinstance(data.get('entries'), list)" "GET /api/ledger returns entries"

echo ""
echo "==> Streaming chat turn (requires Ollama + archie model)"

OLLAMA_OK=$(python3 -c "import json,sys;d=json.loads('''$HEALTH''');print('1' if d['ollama']['reachable'] else '0')" 2>/dev/null || echo "0")
if [ "$OLLAMA_OK" != "1" ]; then
  echo "  ⏭  skipping chat turn — Ollama not reachable"
else
  CHAT_RESP=$(curl -sf -X POST "http://127.0.0.1:$PORT/api/chat" \
    -H "content-type: application/json" \
    -d '{"workspace":"Default","agent":"archie","message":"Reply with exactly the single word: pong."}')
  TURN_ID=$(echo "$CHAT_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['turn_id'])")
  echo "  turn_id: $TURN_ID"

  # Stream the turn through a small Python WS client.
  # PORT/TURN_ID are interpolated into the heredoc by bash; everything else is plain Python.
  STREAM_OUT=$("$REPO/.venv/bin/python" - <<PY
import asyncio, json, sys, websockets

URL = "ws://127.0.0.1:$PORT/api/chat/stream/$TURN_ID"

async def main():
    tokens = []
    done = False
    error = None
    try:
        async with websockets.connect(URL, max_size=None) as ws:
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=180.0)
                except asyncio.TimeoutError:
                    error = "TIMEOUT"
                    break
                ev = json.loads(msg)
                t = ev.get("type")
                if t == "token":
                    tokens.append(ev.get("content", ""))
                elif t == "card":
                    tokens.append(f"\\n[card:{ev.get('card')}]\\n")
                elif t == "tool_call_start":
                    tokens.append(f"\\n[tool:{ev.get('name')}]\\n")
                elif t == "done":
                    done = True
                    break
                elif t == "error":
                    error = ev.get("message", "unknown error")
                    break
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    print("DONE" if done else f"INCOMPLETE ({error or 'no done event'})")
    print("".join(tokens))

asyncio.run(main())
PY
)
  if echo "$STREAM_OUT" | head -1 | grep -q "DONE"; then
    pass "WS stream completed end-to-end"
    REPLY=$(echo "$STREAM_OUT" | tail -n +2)
    if echo "$REPLY" | tr -d '[:space:][:punct:]' | grep -iqE "^pong"; then
      pass "Archie replied 'pong'"
    else
      pass "Archie replied (content: $(echo $REPLY | head -c 80)…)"
    fi
  else
    fail "WS stream did not complete: $STREAM_OUT"
  fi
fi

echo ""
echo "==> Summary"
echo "  pass: $PASS    fail: $FAIL"
if [ $FAIL -gt 0 ]; then
  echo ""
  echo "Failures:"
  for f in "${FAILURES[@]}"; do echo "  · $f"; done
  exit 1
fi
