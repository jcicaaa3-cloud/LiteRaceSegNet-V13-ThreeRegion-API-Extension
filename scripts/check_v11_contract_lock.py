#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

JsonShape = Dict[str, str]
DEFAULT_BASELINE = "api_contract/v11_response_baseline.json"


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def collect_shape(value: Any, prefix: str = "$") -> JsonShape:
    """Collect stable JSON-path -> JSON-type pairs.

    Array containers are recorded as `array`. Representative element paths use
    a stable `[]` marker instead of numeric indexes. Empty arrays record an
    `empty` element marker so no-damage runtime responses can remain compatible
    with a non-empty baseline unless --strict-array-elements is used.
    """
    shape: JsonShape = {prefix: _type_name(value)}
    if isinstance(value, dict):
        for key, child in value.items():
            shape.update(collect_shape(child, f"{prefix}.{key}"))
    elif isinstance(value, list):
        if value:
            shape.update(collect_shape(value[0], f"{prefix}[]"))
        else:
            shape[f"{prefix}[]"] = "empty"
    return shape


def _under_root_or_child(path: str, roots: Iterable[str]) -> bool:
    for root in roots:
        root = root.rstrip(".")
        if path == root or path.startswith(root + ".") or path.startswith(root + "[]"):
            return True
    return False


def _child_of_root(path: str, roots: Iterable[str]) -> bool:
    for root in roots:
        root = root.rstrip(".")
        if path.startswith(root + ".") or path.startswith(root + "[]"):
            return True
    return False


def under_allowed_append(path: str, allowed_append_fields: Iterable[str]) -> bool:
    for field in allowed_append_fields:
        if path == f"$.{field}" or path.startswith(f"$.{field}.") or path.startswith(f"$.{field}[]"):
            return True
    return False


def _array_marker_prefixes(path: str) -> list[str]:
    """Return candidate array markers that can make a representative item optional.

    Example: $.result.predicted_classes[].class_id -> [$.result.predicted_classes[]]
    """
    markers: list[str] = []
    search_from = 0
    while True:
        idx = path.find("[]", search_from)
        if idx == -1:
            break
        markers.append(path[: idx + 2])
        search_from = idx + 2
    return markers


def _candidate_has_empty_parent_array(path: str, cand_shape: JsonShape) -> bool:
    for marker in _array_marker_prefixes(path):
        if cand_shape.get(marker) == "empty":
            return True
    return False


def _types_compatible(expected_type: str, actual_type: str, allow_empty_arrays: bool) -> bool:
    if expected_type == actual_type:
        return True
    if allow_empty_arrays and (expected_type == "empty" or actual_type == "empty"):
        return True
    return False


def compare_contract(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
    allowed_append_fields: Iterable[str] = (),
    dynamic_object_paths: Iterable[str] = (),
    require_exact_top_level: bool = False,
    allow_empty_arrays: bool = True,
) -> Tuple[bool, list[str]]:
    base_shape = collect_shape(baseline)
    cand_shape = collect_shape(candidate)
    errors: list[str] = []

    for path, expected_type in sorted(base_shape.items()):
        # Optional escape hatch: dynamic objects are checked only at the object
        # boundary. Do not enable this for strict legacy-contract audits unless
        # the subtree is explicitly documented as run-specific evidence.
        if _child_of_root(path, dynamic_object_paths):
            continue
        if path not in cand_shape:
            if allow_empty_arrays and _candidate_has_empty_parent_array(path, cand_shape):
                continue
            errors.append(f"missing path: {path}")
        elif not _types_compatible(expected_type, cand_shape[path], allow_empty_arrays=allow_empty_arrays):
            errors.append(f"type changed at {path}: {expected_type} -> {cand_shape[path]}")

    extra_paths = sorted(path for path in cand_shape if path not in base_shape)
    unexpected_extra = [
        path
        for path in extra_paths
        if not under_allowed_append(path, allowed_append_fields)
        and not _under_root_or_child(path, dynamic_object_paths)
    ]

    if require_exact_top_level:
        base_keys = set(baseline.keys())
        cand_keys = set(candidate.keys())
        extra_top = cand_keys - base_keys
        allowed_top = set(allowed_append_fields)
        if extra_top - allowed_top:
            errors.append(f"unexpected top-level fields: {sorted(extra_top - allowed_top)}")

    if unexpected_extra:
        preview = unexpected_extra[:30]
        suffix = " ..." if len(unexpected_extra) > 30 else ""
        errors.append(f"unexpected extra paths: {preview}{suffix}")

    return len(errors) == 0, errors


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: JSON file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: top-level JSON must be an object: {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that a response preserves the locked v11-compatible JSON contract."
    )
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE,
        help=f"Locked v11 response baseline JSON. Default: {DEFAULT_BASELINE}",
    )
    parser.add_argument("--candidate", required=True, help="JSON response/result file to check")
    parser.add_argument(
        "--allow-append-field",
        action="append",
        default=[],
        help="Optional append-only top-level namespace, e.g. v13_visualization. Omit for 방식 B.",
    )
    parser.add_argument(
        "--dynamic-object-path",
        action="append",
        default=[],
        help=(
            "Optional escape hatch: treat nested fields under this existing object path as run-specific "
            "while still checking the object itself, e.g. $.result.raw_summary. Default is strict."
        ),
    )
    parser.add_argument(
        "--strict-array-elements",
        action="store_true",
        help="Fail when a runtime array is empty but the baseline example contains representative element fields.",
    )
    parser.add_argument("--require-exact-top-level", action="store_true")
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    candidate_path = Path(args.candidate)
    baseline = _load_json(baseline_path)
    candidate = _load_json(candidate_path)

    ok, errors = compare_contract(
        baseline,
        candidate,
        allowed_append_fields=args.allow_append_field,
        dynamic_object_paths=args.dynamic_object_path,
        require_exact_top_level=args.require_exact_top_level,
        allow_empty_arrays=not args.strict_array_elements,
    )

    print(f"Baseline: {baseline_path}")
    print(f"Candidate: {candidate_path}")
    if args.dynamic_object_path:
        print(f"Dynamic object paths checked as opaque: {', '.join(args.dynamic_object_path)}")

    if ok:
        print("OK: v11-compatible JSON paths and field types are preserved.")
        if args.allow_append_field:
            print(f"Allowed append-only namespaces: {', '.join(args.allow_append_field)}")
        else:
            print("No append-only response fields were allowed; this matches separate-extension 방식 B.")
        return 0

    print("FAIL: v11-compatible JSON contract check failed.")
    for error in errors:
        print("-", error)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
