# Request / Response Schema

## Request

Multipart endpoint:

```text
POST /api/v1/road-damage/segment
```

Form fields:

```text
file: binary image
request_id: optional string
return_mask: optional boolean
return_overlay: optional boolean
return_evidence_json: optional boolean
min_area_pixels: optional integer
```

## Locked success response baseline

Contract baseline:

```text
api_contract/v11_response_baseline.json
```

Readable V13 example with the same locked shape:

```text
api_contract/response_success_example.json
```

Breaking-change check:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level
```

## Error response

See:

```text
api_contract/response_error_example.json
```

## Class mapping

V13 pothole-binary config uses:

```json
{
  "0": "background",
  "1": "pothole_or_road_damage"
}
```

Keep this synchronized with the training config before handoff.

## V13 three-region visualization extension

The success response schema above is not changed by default. V13-only three-region visualization is written separately:

```text
runtime_api/requests/<request_id>/v13_visualization.json
runtime_api/requests/<request_id>/output/crack_mask.png
runtime_api/requests/<request_id>/output/major_damage_mask.png
runtime_api/requests/<request_id>/output/suspected_mask.png
runtime_api/requests/<request_id>/output/three_region_overlay.png
```

Read it through:

```text
GET /api/v1/results/<request_id>/v13-visualization
```

This keeps strict v11-compatible clients from seeing unknown fields in the main response.
