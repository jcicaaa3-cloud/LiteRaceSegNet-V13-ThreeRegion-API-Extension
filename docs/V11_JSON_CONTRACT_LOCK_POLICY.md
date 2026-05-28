# V11 JSON Contract Lock Policy

## Purpose

This add-on must not break the existing backend/frontend integration that already depends on the v11 JSON response shape.

The V13 API-ready layer may call the V13 model and may generate additional files, but the existing v11-compatible response contract must be treated as locked.

## Rules

### 1. Do not rename existing fields

Do not rename fields that the backend/frontend already consumes.

Examples:

```text
request_id     -> keep
status         -> keep
result         -> keep
files          -> keep
warnings       -> keep
mask/overlay paths -> keep the existing naming style if already used
```

### 2. Do not change existing field types

If a field was a string, keep it a string.
If a field was a number, keep it a number.
If a field was an object, keep it an object.
If a field was a list, keep it a list.

### 3. Do not remove existing fields

Even if V13 no longer uses a value internally, keep the field if the frontend/backend expects it.
Use `null`, an empty list, or the previous safe default only when the original system already accepted it.

### 4. Add V13-only information in a namespace

New 3-region visualization data should be added under a clearly namespaced field, for example:

```json
"v13_visualization": {
  "three_region_overlay": true,
  "crack_mask_path": "...",
  "major_damage_mask_path": "...",
  "suspected_mask_path": "..."
}
```

Do not scatter new fields across the old top-level contract unless the backend owner approves it.

### 5. Strict-client option

If the existing frontend/backend is strict and rejects unknown fields, do not append new fields to the old response.
Instead, keep the old endpoint unchanged and expose one of the following:

```text
GET /api/v1/results/{request_id}/v13-visualization
GET /api/v1/results/{request_id}/three-region
```

or return the extra information only through the evidence JSON file path.

## Recommended wording

```text
The v11 JSON response contract is preserved as the compatibility baseline.
V13 is used for inference and additional visualization outputs only.
New crack / major-damage / suspected-area results must be append-only or served through a separate V13 extension endpoint.
```
