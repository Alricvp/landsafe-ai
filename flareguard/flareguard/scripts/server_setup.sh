#!/usr/bin/env bash
# Bare-metal setup for a shared Linux server (no Docker). Run from the repo root.
set -euo pipefail
echo "Architecture: $(uname -m)   (s390x = IBM LinuxONE)"

if command -v apt-get >/dev/null; then
  sudo apt-get update
  # System packages are prebuilt for s390x; pip would try to compile these from source.
  sudo apt-get install -y python3 python3-venv python3-pip python3-numpy python3-pandas \
    python3-scipy python3-sklearn python3-joblib python3-pytest python3-httpx
fi

python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn pydantic          # pure-Python or wheels available
[ -f .env ] || cp .env.example .env
python3 -m src.bootstrap
echo "Ready. Start the API with: scripts/run_api.sh"
