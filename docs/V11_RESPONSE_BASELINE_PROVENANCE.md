# V11 Response Baseline Provenance

`api_contract/v11_response_baseline.json` is now the default baseline for `scripts/check_v11_contract_lock.py`.

## Why this file exists

The public `LiteRaceSegNet-V11` repository exposes the legacy segmentation/service flow, not a public HTTP API response fixture. In that repo, `seg/capstone_batch_service.py` runs the model/service pipeline and prints that the main artifacts include `*_service_overlay.png`, `*_service_mask.png`, and `*_service_summary.json/csv`. The JSON actually emitted by the V11 service visualization layer is the service-summary JSON shape, represented here as:

```text
api_contract/v11_service_summary_reference_from_repo.json
```

The current backend/frontend integration, however, parses an API response wrapper with stable paths such as:

```text
$.request_id
$.status
$.model
$.input
$.result.damage_detected
$.result.damage_area_ratio
$.result.predicted_classes
$.files.mask_path
$.files.overlay_path
$.files.evidence_json_path
$.runtime
$.warnings
```

Therefore `v11_response_baseline.json` stores the locked API response wrapper shape while embedding a V11-style service summary under `result.raw_summary`. It should be treated as the contract baseline for checking `runtime_api/requests/<request_id>/result.json`.

## Replacing this with a real production/frontend sample

If you have a real response body captured from the old frontend/backend integration, replace only this file:

```text
api_contract/v11_response_baseline.json
```

Then run:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level
```

Do not use `v11_service_summary_reference_from_repo.json` as the direct baseline for the API response wrapper; it is the legacy evidence JSON shape, not the top-level API response body.
