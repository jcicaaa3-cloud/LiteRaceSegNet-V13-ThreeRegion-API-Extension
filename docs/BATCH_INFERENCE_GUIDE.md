# Batch Inference Guide

This add-on keeps the existing V13 batch-service workflow and exposes it through FastAPI.

## Original V13 batch command shape

```bash
python seg/capstone_batch_service.py \
  --input_dir assets/service_demo/input_batch \
  --outdir seg/runs/literace_service \
  --model_output_dir seg/runs/literace_service_raw_output \
  --config seg/config/pothole_binary_literace_train.yaml \
  --ckpt seg/runs/literace_boundary_degradation/best.pth \
  --mode model \
  --min_area_pixels 80
```

## API request equivalent

The API creates a unique request folder and calls the same script with per-request paths:

```text
runtime_api/requests/<request_id>/input
runtime_api/requests/<request_id>/raw_model_output
runtime_api/requests/<request_id>/output
```

## Expected batch artifacts

```text
*_service_overlay.png
*_service_mask.png
*_service_card.png
*_service_summary.json
service_batch_summary.csv
service_batch_summary.json
_CAPSTONE_SERVICE_MODE.json
```

## Research-integrity setting

The API uses `--mode model` by default.
It does **not** enable demo fallback. Demo fallback may be useful for UI tests, but it should not be used for research/evidence claims.
