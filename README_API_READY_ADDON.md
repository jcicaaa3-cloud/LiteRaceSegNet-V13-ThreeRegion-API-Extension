# LiteRaceSegNet V13 API Ready Add-on

This package is an **API-server integration add-on** for the public `LiteRaceSegNet-V13-Portal-Clean` repository.
It does not replace the V13 research/evidence package. It adds a backend-facing interface layer:

- FastAPI upload endpoint
- request/response schema examples
- batch inference bridge to the existing V13 service runner
- model usage guide for backend developers
- safety/limitation note
- v11 legacy JSON reuse policy

## Integration principle

- **Actual model/evidence baseline:** LiteRaceSegNet V13
- **Reusable legacy material:** v11-style JSON shape and backend integration flow only
- **Not reused from v11:** model architecture, checkpoint, metrics, claims, old README wording

## Expected target repository

Copy or unzip this add-on into the root of:

```text
LiteRaceSegNet-V13-Portal-Clean/
```

The add-on expects the V13 repository to already contain:

```text
seg/capstone_batch_service.py
seg/config/pothole_binary_literace_train.yaml
seg/runs/literace_boundary_degradation/best.pth      # local/private checkpoint, not public bundle
```

The public static portal should remain safe. This API server is for local/team/backend integration, not browser-side inference.

## Quick start

### Windows

```bat
scripts\RUN_V13_API_SERVER.bat
```

### Linux/macOS

```bash
bash scripts/run_v13_api_server.sh
```

Then open:

```text
GET  http://127.0.0.1:8000/api/v1/health
POST http://127.0.0.1:8000/api/v1/road-damage/segment
```

## Main endpoint

```text
POST /api/v1/road-damage/segment
```

Upload a road image as multipart field `file`.

Optional form fields:

```text
request_id
return_mask=true
return_overlay=true
return_evidence_json=true
min_area_pixels=80
```

The server saves one request under:

```text
runtime_api/requests/<request_id>/
```

and calls the existing V13 batch-service pipeline in model-checkpoint mode.



## Locked V11 response baseline

The contract checker now uses a dedicated baseline file:

```text
api_contract/v11_response_baseline.json
```

Check a real saved response body with:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level
```

The package also includes `api_contract/v11_response_baseline_source_note.md` and `api_contract/v11_service_summary_reference_from_repo.json` for traceability. If the team has a captured response from the existing V11-connected frontend/backend, replace only `api_contract/v11_response_baseline.json` with that exact sample.

## V13 three-region visualization extension

The default integration uses **separate extension JSON** so the v11-compatible response body is not reshaped.

After `POST /api/v1/road-damage/segment`, the server stores:

```text
runtime_api/requests/<request_id>/result.json
runtime_api/requests/<request_id>/v13_visualization.json
runtime_api/requests/<request_id>/output/crack_mask.png
runtime_api/requests/<request_id>/output/major_damage_mask.png
runtime_api/requests/<request_id>/output/suspected_mask.png
runtime_api/requests/<request_id>/output/three_region_overlay.png
```

Fetch the extension through:

```text
GET /api/v1/results/<request_id>/v13-visualization
```

The returned segmentation response still keeps the existing fields and JSON paths.
See:

```text
docs/V13_THREE_REGION_VISUALIZATION_RUNBOOK.md
docs/V11_JSON_CONTRACT_CHECKLIST.md
docs/V11_REAL_RESPONSE_BASELINE_CHECK.md
```

## Important limitation

This add-on does not ship private datasets, checkpoints, credentials, `.pem`, `.env`, or cloud files.
It assumes a trained V13 checkpoint exists locally.

## JSON contract lock addendum

If a backend/frontend already consumes the v11-style JSON response, do **not** replace or reshape that response.
Keep the existing contract locked and expose V13 three-region visualization as either:

1. an append-only namespaced field such as `v13_visualization`, or
2. a separate endpoint / separate evidence JSON file if the client rejects unknown fields.

See:

```text
docs/V11_JSON_CONTRACT_LOCK_POLICY.md
docs/THREE_REGION_VISUALIZATION_WITH_LOCKED_JSON.md
```
