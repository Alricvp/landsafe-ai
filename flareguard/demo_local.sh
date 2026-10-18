#!/usr/bin/env bash
# One-command local demo of the static dashboard against the real API.
# Requires the FlareGuard API running at the API_URL below.
set -euo pipefail
cd "$(dirname "$0")"
API_URL="${API_URL:-http://localhost:8000}"
PORT="${PORT:-8080}"
echo "API_URL=$API_URL"
if ! curl -s -m 4 -o /dev/null -w "%{http_code}" "$API_URL/health" | grep -qE "^(2|3|4)"; then
  echo "API seems unreachable at $API_URL/health."
  echo "Start it:  make api          (or: bash scripts/server_setup.sh && bash scripts/run_api.sh)"
  echo "Or edit this file or set API_URL=http://<server-ip>:8000"
  echo "Then:     python3 -m http.server $PORT  (this serves index.html)"
  exit 2
fi
echo "API OK. Serving index.html on http://localhost:$PORT"
python3 -m http.server "$PORT" --bind 127.0.0.1
