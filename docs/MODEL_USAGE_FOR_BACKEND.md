# Model Usage for Backend Developers

## Required local files

```text
seg/capstone_batch_service.py
seg/infer_seg.py
seg/infer_service_visual.py
seg/config/pothole_binary_literace_train.yaml
seg/runs/literace_boundary_degradation/best.pth
```

The checkpoint is private/local and should not be included in the public GitHub release.

## Install

```bash
python -m pip install -r requirements_api.txt
```

The V13 service runner also needs:

```text
torch torchvision opencv-python numpy PyYAML Pillow tqdm
```

## Start server

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Health check

```text
GET /api/v1/health
```

Healthy response means:

- V13 checkpoint exists,
- V13 config exists,
- V13 batch-service script exists.

## Inference request

Use multipart upload:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/road-damage/segment" \
  -F "file=@road_001.jpg" \
  -F "request_id=lrs_demo_001"
```

## Result interpretation

The API returns:

- `mask_path`: predicted binary/class mask output path
- `overlay_path`: visual overlay path for frontend preview
- `evidence_json_path`: service summary JSON path
- `damage_area_ratio`: approximate damaged pixel ratio if available from the service summary

Do not interpret softmax/confidence or damage ratio as an official repair priority or road safety diagnosis.
