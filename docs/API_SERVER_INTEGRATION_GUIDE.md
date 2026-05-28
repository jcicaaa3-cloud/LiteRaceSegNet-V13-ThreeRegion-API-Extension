# LiteRaceSegNet V13 API Server Integration Guide

## Purpose

This guide defines how a backend server should call LiteRaceSegNet V13 after receiving a road image.
The API layer automates the flow from uploaded image to mask/overlay/JSON result.

## Version boundary

- Use **LiteRaceSegNet V13** for actual inference, model interpretation, class mapping, and reported results.
- Reuse **v11 only as a legacy reference** for JSON/request-response flow if needed.
- Do not mix v11 metrics, checkpoints, or old model claims into V13 API responses.

## Runtime flow

```text
backend request
→ request_id 생성/정리
→ image 저장
→ image validation
→ V13 batch-service runner 호출
→ LiteRaceSegNet checkpoint inference
→ predicted class mask 생성
→ service overlay/mask/summary 생성
→ V13 three-region extension files 생성
→ v11-compatible result.json 저장
→ 기존 JSON response 반환
```

## Existing V13 bridge used by this add-on

The add-on calls the existing V13 service runner:

```text
seg/capstone_batch_service.py
```

with:

```text
--mode model
--config seg/config/pothole_binary_literace_train.yaml
--ckpt seg/runs/literace_boundary_degradation/best.pth
```

This keeps the public V13 research portal separate from the backend API layer.

## Endpoint

```text
POST /api/v1/road-damage/segment
```

Multipart fields:

| Field | Required | Default | Meaning |
|---|---:|---:|---|
| file | yes | - | JPG/PNG road image |
| request_id | no | auto | Backend request id |
| return_mask | no | true | Include mask path |
| return_overlay | no | true | Include overlay path |
| return_evidence_json | no | true | Include summary JSON path |
| min_area_pixels | no | 80 | Minimum postprocess damage area |

## Output folder

Each request is isolated:

```text
runtime_api/requests/<request_id>/
├─ input/
│  └─ input.jpg
├─ raw_model_output/
└─ output/
   ├─ *_service_overlay.png
   ├─ *_service_mask.png
   ├─ *_service_summary.json
   ├─ service_batch_summary.csv/json
   ├─ crack_mask.png
   ├─ major_damage_mask.png
   ├─ suspected_mask.png
   ├─ three_region_overlay.png
   └─ _CAPSTONE_SERVICE_MODE.json
├─ result.json
└─ v13_visualization.json
```

## Why subprocess bridge?

The public V13 package already has a batch service runner. For team integration, the lowest-risk approach is:

1. keep the V13 inference scripts unchanged,
2. wrap them with an API endpoint,
3. return the same service artifacts as JSON paths.

This avoids rewriting the model-loading path before the backend contract is stable.


## V13 visualization extension endpoint

```text
GET /api/v1/results/{request_id}/v13-visualization
```

This endpoint returns the separate `v13_visualization.json` file. It is intentionally separate from `POST /api/v1/road-damage/segment` so older consumers can keep parsing the original response shape.

## Production hardening checklist

Before live deployment:

- replace local file paths with signed/static URLs if frontend needs direct access,
- add authentication between backend and model server,
- restrict CORS origins,
- add upload type sniffing and image decode validation,
- add request timeout control,
- add GPU queue control if concurrent requests are expected,
- log request id, checkpoint hash, config path, and runtime device,
- do not commit checkpoints, datasets, `.env`, `.pem`, or credentials.
