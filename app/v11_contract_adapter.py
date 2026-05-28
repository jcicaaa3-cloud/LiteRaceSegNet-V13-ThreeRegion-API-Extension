from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def attach_v13_visualization_append_only(
    base_v11_response: Dict[str, Any],
    v13_visualization_payload: Dict[str, Any],
    field_name: str = "v13_visualization",
) -> Dict[str, Any]:
    """Attach V13-only visualization data without modifying existing response fields.

    Use this only when the consuming backend/frontend tolerates unknown extra fields.
    If the client is strict, serve `v13_visualization_payload` through a separate endpoint
    or as a file referenced by the existing evidence JSON path.
    """
    response = deepcopy(base_v11_response)
    if field_name in response:
        raise ValueError(f"Refusing to overwrite existing response field: {field_name}")
    response[field_name] = deepcopy(v13_visualization_payload)
    return response


def assert_existing_fields_unchanged(before: Dict[str, Any], after: Dict[str, Any], allowed_new_field: str = "v13_visualization") -> None:
    """Fail if the V11-compatible fields were removed or changed.

    This is a lightweight contract guard for integration tests.
    """
    before_keys = set(before.keys())
    after_keys = set(after.keys())
    missing = before_keys - after_keys
    if missing:
        raise AssertionError(f"V11 contract fields removed: {sorted(missing)}")
    changed = []
    for key in before_keys:
        if before[key] != after[key]:
            changed.append(key)
    if changed:
        raise AssertionError(f"V11 contract fields changed: {sorted(changed)}")
    extra = after_keys - before_keys
    if extra - {allowed_new_field}:
        raise AssertionError(f"Unexpected new fields added: {sorted(extra - {allowed_new_field})}")
