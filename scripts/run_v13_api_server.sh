#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[LiteRaceSegNet V13 API Server]"
echo "This server must be run from the LiteRaceSegNet-V13-Portal-Clean repository root."

if [ ! -f "seg/capstone_batch_service.py" ]; then
  echo "[ERROR] seg/capstone_batch_service.py not found. Copy this add-on into the V13 repository root first."
  exit 1
fi

python -m pip install -r requirements_api.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
