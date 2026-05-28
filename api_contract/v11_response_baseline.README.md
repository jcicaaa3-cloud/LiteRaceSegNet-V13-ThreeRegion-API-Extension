# v11_response_baseline.json

This file is the lock-file baseline used by `scripts/check_v11_contract_lock.py`.

Important source note:

- The public `LiteRaceSegNet-V11` repository is a segmentation/evidence repository and does not expose the FastAPI response wrapper used by the current API add-on.
- The public V11 code path writes service visualization artifacts such as `*_service_mask.png`, `*_service_overlay.png`, `*_service_summary.json`, and batch summary JSON/CSV.
- Therefore this baseline is a V11-compatible API response baseline for contract locking, not a model metric/result claim and not a replacement for a private production response sample.

Recommended team usage:

1. If you have a real response body captured from the existing V11-connected frontend/backend, replace the contents of `api_contract/v11_response_baseline.json` with that exact JSON body.
2. Keep the file name fixed.
3. Run:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level
```

The checker compares JSON paths and value types, not request-specific values such as IDs, file paths, latency, or model version strings.
