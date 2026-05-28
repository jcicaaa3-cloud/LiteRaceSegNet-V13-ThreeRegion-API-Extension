#!/usr/bin/env bash
set -euo pipefail
IMAGE_PATH="${1:-sample.jpg}"
REQ_ID="${2:-lrs_manual_test_001}"

curl -X POST "http://127.0.0.1:8000/api/v1/road-damage/segment" \
  -F "file=@${IMAGE_PATH}" \
  -F "request_id=${REQ_ID}" \
  -F "return_mask=true" \
  -F "return_overlay=true" \
  -F "return_evidence_json=true" \
  -F "min_area_pixels=80"
