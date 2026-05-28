# V11 Real Response Baseline Contract Check

## Purpose

This note records the contract-check mode requested for the JSON-locked V13 three-region visualization extension.

The checker no longer relies on `api_contract/response_success_example.json` as the default baseline. The default and recommended baseline is now:

```text
api_contract/v11_response_baseline.json
```

Run the main API response check as:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level
```

For the bundled/generated runtime-path smoke candidate:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/v11_contract_smoke/result.json \
  --require-exact-top-level
```

Expected result:

```text
OK: v11-compatible JSON paths and field types are preserved.
No append-only response fields were allowed; this matches separate-extension 방식 B.
```


For an exact local runtime-path check, run the smoke script first; it creates `runtime_api/requests/v11_contract_smoke/result.json` and then runs the same checker command:

```bash
python scripts/test_v11_baseline_contract_smoke.py
```

## What was available from the public V11 repo

The public V11 repository exposes the segmentation/evidence service flow and the generated service-summary JSON shape. It does not expose a separate FastAPI/HTTP response wrapper fixture in the visible repository files checked for this update.

Therefore this package keeps two baselines:

```text
api_contract/v11_response_baseline.json
api_contract/v11_repo_service_summary_baseline.json
```

Use `v11_response_baseline.json` for `runtime_api/requests/<request_id>/result.json`.

Use `v11_repo_service_summary_baseline.json` only for the evidence/service-summary JSON pointed to by `files.evidence_json_path`, not for the main API wrapper.

## Replacing with a captured frontend/backend sample

When a real response body captured from the old frontend/backend integration is available, replace the contents of:

```text
api_contract/v11_response_baseline.json
```

Do not change the filename. Then rerun the same command above. This makes the contract check compare V13 output against the captured legacy API response sample rather than against a package-local example.

## Breaking-change interpretation

A passing check means:

- existing top-level fields are still present,
- existing JSON paths from the baseline still exist,
- existing field types are preserved,
- no new top-level field was added unless explicitly allowed,
- `v13_visualization.json` remains separate under 방식 B.

A failing check should be treated as a possible breaking change until the baseline sample and candidate output are reviewed.
