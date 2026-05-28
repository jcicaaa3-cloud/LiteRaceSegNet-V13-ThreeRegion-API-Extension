# V13 Three-Region Visualization Runbook

## Goal

Use LiteRaceSegNet V13 inference output to create extra visualization artifacts while keeping the existing v11-compatible JSON response unchanged.

This runbook uses **방식 B: separate extension JSON** as the default.

```text
runtime_api/requests/<request_id>/
├─ input/
│  └─ input.jpg
├─ output/
│  ├─ *_service_mask.png                 # existing V13 service artifact
│  ├─ *_service_overlay.png              # existing V13 service artifact
│  ├─ crack_mask.png                     # new extension artifact
│  ├─ major_damage_mask.png              # new extension artifact
│  ├─ suspected_mask.png                 # new extension artifact
│  └─ three_region_overlay.png           # new extension artifact
├─ raw_model_output/
│  └─ *_pred_class.png                   # optional V13 raw class mask
├─ result.json                           # saved v11-compatible response body
└─ v13_visualization.json                # separate V13 extension JSON
```

## Existing response contract rule

`POST /api/v1/road-damage/segment` still returns the same `SegmentResponse` shape:

```text
request_id
status
model
input
result
files
runtime
warnings
```

The new 3-region result is **not** inserted into this response by default.
Strict existing frontend/backend clients can continue reading the same JSON paths, such as:

```text
$.files.mask_path
$.files.overlay_path
$.files.evidence_json_path
$.result.damage_detected
$.result.damage_area_ratio
```

## API flow

1. Upload image to the existing endpoint.
2. Server saves input and calls `seg/capstone_batch_service.py` in V13 model mode.
3. Existing service mask/overlay/summary are generated.
4. `app.three_region_visualization.generate_three_region_visualization()` reads the V13 binary/service mask.
5. The extension writes PNG masks and `v13_visualization.json` separately.
6. The endpoint returns the v11-compatible response unchanged.

## Fetch the extension JSON

```text
GET /api/v1/results/<request_id>/v13-visualization
```

This returns the content of:

```text
runtime_api/requests/<request_id>/v13_visualization.json
```

## CLI generation from an existing mask

When you already have a request folder and a V13 binary/service mask, run:

```bash
python scripts/generate_v13_three_region_visualization.py \
  --request_id lrs_demo_001 \
  --image runtime_api/requests/lrs_demo_001/input/input.jpg \
  --mask runtime_api/requests/lrs_demo_001/output/input_service_mask.png \
  --request_dir runtime_api/requests/lrs_demo_001 \
  --raw_model_output_dir runtime_api/requests/lrs_demo_001/raw_model_output
```

Expected outputs:

```text
runtime_api/requests/lrs_demo_001/v13_visualization.json
runtime_api/requests/lrs_demo_001/output/crack_mask.png
runtime_api/requests/lrs_demo_001/output/major_damage_mask.png
runtime_api/requests/lrs_demo_001/output/suspected_mask.png
runtime_api/requests/lrs_demo_001/output/three_region_overlay.png
```

## Smoke test

```bash
python scripts/test_three_region_postprocess_smoke.py
```

The smoke test creates a synthetic request under:

```text
runtime_api/requests/smoke_three_region/
```

It checks that crack, major-damage, and suspected masks are all generated.

## Post-processing logic

### Cyan: crack-like thin structure

Derived from V13 foreground components that look thin and elongated:

- connected component analysis,
- skeleton-based mean-width estimate,
- bounding-box aspect ratio,
- component area limit to avoid calling large blobs cracks.

If a crack touches a blob and becomes one connected component, the code attempts a conservative split:

- thick core / non-thin residual → red major-damage candidate,
- elongated thin residual → cyan crack-like candidate,
- tiny uncertain residual → yellow suspected candidate.

### Red: pothole or major damage blob

Derived from V13 foreground components that are relatively large or blob-like:

- component area threshold,
- fill ratio inside bounding box,
- compactness/perimeter estimate,
- distance-transform width estimate.

### Yellow: suspected or uncertain candidate zone

Derived from areas that should not be presented as confirmed classes:

- dilation ring around V13 foreground,
- tiny or ambiguous foreground components,
- raw foreground pixels removed by service post-processing, when `raw_model_output/*_pred_class.png` exists,
- optional near-threshold probability/logit pixels if a future V13 runner saves probability maps.

Do not call the yellow area a real class or calibrated confidence output.

## Important limitation

The current V13 public inference flow is binary road-damage segmentation. Therefore the 3-region output is a visualization heuristic unless a separately trained/evaluated multi-class model is added.

Use wording such as:

```text
Three-region visualization is generated as a research/capstone prototype extension from the V13 binary mask.
```

Avoid wording such as:

```text
The model diagnoses exact crack/pothole/suspected classes with certified confidence.
```


## Contract baseline

Use this file as the baseline for JSON contract checks:

```text
api_contract/v11_response_baseline.json
```

After a real request, run:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level
```

Replace `api_contract/v11_response_baseline.json` with a captured staging/production V11 frontend/backend response body when available. Keep the filename stable so CI and docs continue to use the real baseline.
