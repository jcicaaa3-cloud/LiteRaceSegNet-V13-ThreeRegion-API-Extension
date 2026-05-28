# Three-Region Visualization with Locked JSON

## Goal

Generate a service-style visualization from LiteRaceSegNet V13 while preserving the v11-compatible JSON response shape.

Color meaning:

```text
cyan/turquoise = crack-like thin structure
red            = pothole / major damage blob
yellow         = suspected / uncertain candidate area
```

## Safe integration strategy

### Recommended default

Keep the existing response shape unchanged and put new V13 visualization files in the output folder:

```text
runtime_api/requests/<request_id>/output/crack_mask.png
runtime_api/requests/<request_id>/output/major_damage_mask.png
runtime_api/requests/<request_id>/output/suspected_mask.png
runtime_api/requests/<request_id>/output/three_region_overlay.png
runtime_api/requests/<request_id>/v13_visualization.json
```

The default implementation uses option 2: keep the main response unchanged and expose the extension through:

```text
GET /api/v1/results/{request_id}/v13-visualization
```

Option 1, append-only `v13_visualization`, remains available only when the client explicitly accepts unknown fields.

## Do not do this

```text
Do not replace the old overlay path with a new meaning without warning.
Do not change damage_area_ratio from old binary damage ratio to a new multi-region ratio.
Do not change class_id mapping in the old response.
Do not replace the old response with a new schema unless the backend owner approves.
```

## Recommended V13 extension payload

```json
{
  "schema_version": "v13_three_region_visualization_0.1",
  "request_id": "lrs_demo_001",
  "source_model_version": "v13",
  "compatibility_baseline": "v11_json_contract_locked",
  "files": {
    "crack_mask_path": "runtime_api/requests/lrs_demo_001/output/crack_mask.png",
    "major_damage_mask_path": "runtime_api/requests/lrs_demo_001/output/major_damage_mask.png",
    "suspected_mask_path": "runtime_api/requests/lrs_demo_001/output/suspected_mask.png",
    "three_region_overlay_path": "runtime_api/requests/lrs_demo_001/output/three_region_overlay.png",
    "v13_visualization_json_path": "runtime_api/requests/lrs_demo_001/v13_visualization.json"
  },
  "region_summary": {
    "crack_area_ratio": 0.041,
    "major_damage_area_ratio": 0.214,
    "suspected_area_ratio": 0.062
  },
  "warnings": [
    "Three-region labels are visualization/heuristic outputs unless separately trained and validated as multi-class predictions."
  ]
}
```

## Interpretation note

If V13 is still binary, crack / major-damage / suspected-area separation should be described as post-processing or heuristic visualization.
Do not describe it as fully trained multi-class segmentation unless the dataset, labels, training config, and evaluation results support that claim.

## Implemented files

```text
app/three_region_visualization.py
scripts/generate_v13_three_region_visualization.py
scripts/test_three_region_postprocess_smoke.py
scripts/check_v11_contract_lock.py
docs/V13_THREE_REGION_VISUALIZATION_RUNBOOK.md
docs/V11_JSON_CONTRACT_CHECKLIST.md
```
