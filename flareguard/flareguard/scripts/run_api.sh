#!/usr/bin/env bash
# Run the API in the background and log to flareguard.log.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] && . .venv/bin/activate
nohup python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" > flareguard.log 2>&1 &
echo "API started (pid $!). Docs: http://<server-ip>:${PORT:-8000}/docs   Logs: flareguard.log"
