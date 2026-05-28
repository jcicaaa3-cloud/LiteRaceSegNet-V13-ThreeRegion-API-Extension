# V11 Baseline Contract Check Results

This check was run after adding the dedicated V11-compatible baseline lock file:

```text
api_contract/v11_response_baseline.json
```

## 방식 B: separate extension JSON, no append-only field in main response

Command:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/v11_contract_smoke/result.json \
  --require-exact-top-level
```

Result:

```text
Baseline: api_contract/v11_response_baseline.json
Candidate: runtime_api/requests/v11_contract_smoke/result.json
OK: v11-compatible JSON paths and field types are preserved.
No append-only response fields were allowed; this matches separate-extension 방식 B.
```

## 방식 A optional append-only namespace check

Command:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate api_contract/response_v11_compat_append_only_example.json \
  --allow-append-field v13_visualization \
  --require-exact-top-level
```

Result:

```text
Baseline: api_contract/v11_response_baseline.json
Candidate: api_contract/response_v11_compat_append_only_example.json
OK: v11-compatible JSON paths and field types are preserved.
Allowed append-only namespaces: v13_visualization
```

## Optional dynamic raw-summary variant

Use this only when the legacy frontend/backend is confirmed not to parse nested paths inside `result.raw_summary`:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate runtime_api/requests/<request_id>/result.json \
  --require-exact-top-level \
  --dynamic-object-path $.result.raw_summary
```


## Strict no-append negative check

This verifies that 방식 B remains strict by default. The same append-only example must fail when `--allow-append-field v13_visualization` is omitted:

```bash
python scripts/check_v11_contract_lock.py \
  --baseline api_contract/v11_response_baseline.json \
  --candidate api_contract/response_v11_compat_append_only_example.json \
  --require-exact-top-level
```

Expected result:

```text
FAIL: v11-compatible JSON contract check failed.
- unexpected top-level fields: ['v13_visualization']
```

This is intentional: the default runtime response should remain the locked V11-compatible response, and the V13 visualization should stay in `v13_visualization.json` unless append-only mode is explicitly enabled.
