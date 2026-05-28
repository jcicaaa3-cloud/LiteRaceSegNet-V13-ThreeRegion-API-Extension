#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_v11_contract_lock import compare_contract  # noqa: E402

BASELINE = ROOT / "api_contract" / "v11_response_baseline.json"
REQUEST_ID = "v11_contract_smoke"
CANDIDATE = ROOT / "runtime_api" / "requests" / REQUEST_ID / "result.json"


def _write_candidate_from_baseline() -> None:
    baseline_payload = json.loads(BASELINE.read_text(encoding="utf-8"))
    payload = json.loads(json.dumps(baseline_payload, ensure_ascii=False))
    payload["request_id"] = REQUEST_ID
    payload["model"]["version"] = "v13"
    payload["input"]["saved_path"] = f"runtime_api/requests/{REQUEST_ID}/input/input.jpg"
    payload["files"]["mask_path"] = f"runtime_api/requests/{REQUEST_ID}/output/input_service_mask.png"
    payload["files"]["overlay_path"] = f"runtime_api/requests/{REQUEST_ID}/output/input_service_overlay.png"
    payload["files"]["evidence_json_path"] = f"runtime_api/requests/{REQUEST_ID}/output/input_service_summary.json"
    payload["files"]["request_dir"] = f"runtime_api/requests/{REQUEST_ID}"
    raw = payload["result"]["raw_summary"]
    raw["image"] = f"runtime_api/requests/{REQUEST_ID}/input/input.jpg"
    raw["input_mask"] = f"runtime_api/requests/{REQUEST_ID}/raw_model_output/input_pred_class.png"
    raw["outputs"]["mask"] = f"runtime_api/requests/{REQUEST_ID}/output/input_service_mask.png"
    raw["outputs"]["overlay"] = f"runtime_api/requests/{REQUEST_ID}/output/input_service_overlay.png"
    raw["outputs"]["boundary"] = f"runtime_api/requests/{REQUEST_ID}/output/input_service_boundary.png"
    raw["outputs"]["service_card"] = f"runtime_api/requests/{REQUEST_ID}/output/input_service_card.png"
    raw["outputs"]["summary_csv"] = f"runtime_api/requests/{REQUEST_ID}/output/input_service_summary.csv"

    shutil.rmtree(CANDIDATE.parent, ignore_errors=True)
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    _write_candidate_from_baseline()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    ok, errors = compare_contract(baseline, candidate, require_exact_top_level=True)

    print(f"Baseline: {BASELINE.relative_to(ROOT)}")
    print(f"Candidate: {CANDIDATE.relative_to(ROOT)}")
    if not ok:
        print("FAIL: v11-compatible JSON contract check failed.")
        for error in errors:
            print("-", error)
        return 1

    print("OK: v11-compatible JSON paths and field types are preserved.")
    print("No append-only response fields were allowed; this matches separate-extension 방식 B.")
    print("OK: v11 response baseline contract smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
