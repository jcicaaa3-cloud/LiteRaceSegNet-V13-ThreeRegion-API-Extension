# V11-Compatible JSON Contract Checklist

Use this checklist whenever adding V13 visualization features.

## Required decision

Default integration mode:

```text
방식 B: separate extension JSON / separate endpoint
```

The existing segmentation response remains v11-compatible. V13 three-region visualization is stored in:

```text
runtime_api/requests/<request_id>/v13_visualization.json
```

and can be read through:

```text
GET /api/v1/results/<request_id>/v13-visualization
```

## Baseline file policy

Use this file as the contract lock baseline:

```text
api_contract/v11_response_baseline.json
```

Do **not** use `api_contract/response_success_example.json` as the long-term baseline for breaking-change checks. That file is only a readable example. The checker default now points to `api_contract/v11_response_baseline.json`.

Traceability files:

```text
api_contract/v11_response_baseline_source_note.md
api_contract/v11_service_summary_reference_from_repo.json
```

The public V11 repository exposes the service visualization and service-summary JSON generation path, but the reviewed public snapshot did not include a captured outer HTTP `runtime_api/requests/<request_id>/result.json` response. Therefore this package keeps a dedicated outer API baseline file. If a staging/production V11 response body exists, replace only `api_contract/v11_response_baseline.json` with that captured real response and rerun the checker.

## Contract guard command

For 방식 B, check a saved response body against the locked V11-compatible baseline:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level
```

The same command also works because the checker default baseline is now `api_contract/v11_response_baseline.json`:

```bash
python scripts/check_v11_contract_lock.py \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level
```

Expected result:

```text
Baseline: api_contract/v11_response_baseline.json
Candidate: runtime_api/requests/<request_id>/result.json
OK: v11-compatible JSON paths and field types are preserved.
No append-only response fields were allowed; this matches separate-extension 방식 B.
```
Strictness note: the default command compares nested JSON paths and types conservatively. Use `--dynamic-object-path '$.result.raw_summary'` only when the team has explicitly documented `result.raw_summary` as opaque run-specific evidence and no legacy parser reads nested fields inside it.


For 방식 A, where a client explicitly accepts an append-only namespace:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate api_contract/response_v11_compat_append_only_example.json \
  --allow-append-field v13_visualization \
  --require-exact-top-level
```


## `result.raw_summary` policy

`result.raw_summary` is kept as an existing object field. The default checker command is conservative: it compares nested JSON paths and coarse value types under `$.result.raw_summary` as well as the outer response wrapper.

Only use the explicit dynamic escape hatch when the team has documented `result.raw_summary` as opaque run-specific evidence and no legacy frontend/backend parser reads nested paths inside it:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --dynamic-object-path '$.result.raw_summary' \
  --require-exact-top-level
```

## Local smoke check

```bash
python scripts/test_v11_baseline_contract_smoke.py
```

This creates:

```text
runtime_api/requests/v11_contract_smoke/result.json
```

and runs the exact baseline command against it.

## Breaking-change checklist

Before merging, verify:

- [ ] Existing top-level response fields are still present: `request_id`, `status`, `model`, `input`, `result`, `files`, `runtime`, `warnings`.
- [ ] Existing field names are not renamed.
- [ ] Existing field types are not changed.
- [ ] Existing nesting structure is not changed.
- [ ] Existing JSON paths are still readable by old frontend/backend code.
- [ ] `files.mask_path` still points to the existing binary/service mask path.
- [ ] `files.overlay_path` still points to the existing service overlay path.
- [ ] `files.evidence_json_path` is not replaced with the V13 three-region JSON path unless the backend owner explicitly approves it.
- [ ] `result.damage_area_ratio` is not redefined as a 3-region sum or suspected-region ratio.
- [ ] `result.predicted_classes[].class_id` keeps the binary V13/v11-compatible mapping semantics.
- [ ] V13-only visualization files are stored separately.
- [ ] No production/certified diagnosis wording is introduced.

## Baseline-vs-extension comparison

### Existing response remains

```json
{
  "request_id": "lrs_demo_001",
  "status": "success",
  "model": { "name": "LiteRaceSegNet", "version": "v13" },
  "input": { "original_filename": "road_001.jpg" },
  "result": {
    "damage_detected": true,
    "damage_area_ratio": 0.0342,
    "predicted_classes": [
      { "class_id": 1, "class_name": "pothole_or_road_damage", "area_ratio": 0.0342 }
    ]
  },
  "files": {
    "mask_path": "runtime_api/requests/lrs_demo_001/output/input_service_mask.png",
    "overlay_path": "runtime_api/requests/lrs_demo_001/output/input_service_overlay.png",
    "evidence_json_path": "runtime_api/requests/lrs_demo_001/output/input_service_summary.json"
  },
  "runtime": { "latency_ms": 1450.0 },
  "warnings": ["..."]
}
```

### New extension remains separate

```json
{
  "schema_version": "v13_three_region_visualization_0.1",
  "request_id": "lrs_demo_001",
  "compatibility_mode": "separate_extension_json",
  "files": {
    "crack_mask_path": "runtime_api/requests/lrs_demo_001/output/crack_mask.png",
    "major_damage_mask_path": "runtime_api/requests/lrs_demo_001/output/major_damage_mask.png",
    "suspected_mask_path": "runtime_api/requests/lrs_demo_001/output/suspected_mask.png",
    "three_region_overlay_path": "runtime_api/requests/lrs_demo_001/output/three_region_overlay.png",
    "v13_visualization_json_path": "runtime_api/requests/lrs_demo_001/v13_visualization.json"
  }
}
```

## Current V13-only capability

Possible without retraining:

- binary damage mask visualization,
- crack-like vs major-damage shape split using morphology,
- suspected candidate zone using dilation/removed raw pixels/optional probability maps,
- separate extension JSON and images.

Requires additional labeling/training/evaluation:

- true crack/pothole/uncertain multi-class segmentation,
- calibrated confidence or uncertainty score,
- official maintenance priority decision,
- legal/administrative diagnosis.


## Real baseline note

See `docs/V11_REAL_RESPONSE_BASELINE_CHECK.md` for the `api_contract/v11_response_baseline.json` based check requested for real V11/front-backend baseline validation.
