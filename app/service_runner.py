from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .settings import settings

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


class ServiceRunnerError(RuntimeError):
    def __init__(self, code: str, message: str, detail: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def safe_request_id(request_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in request_id.strip())
    return cleaned[:96] or f"lrs_{int(time.time())}"


def make_request_id() -> str:
    return f"lrs_{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 100000:05d}"


def prepare_request_dirs(request_id: str) -> Dict[str, Path]:
    request_dir = settings.runtime_root / safe_request_id(request_id)
    input_dir = request_dir / "input"
    output_dir = request_dir / "output"
    raw_dir = request_dir / "raw_model_output"
    for path in (input_dir, output_dir, raw_dir):
        path.mkdir(parents=True, exist_ok=True)
    return {"request_dir": request_dir, "input_dir": input_dir, "output_dir": output_dir, "raw_dir": raw_dir}


def validate_static_paths() -> None:
    missing = []
    if not settings.batch_service_script.exists():
        missing.append(f"batch service script not found: {settings.batch_service_script}")
    if not settings.config_path.exists():
        missing.append(f"config not found: {settings.config_path}")
    if not settings.checkpoint_path.exists():
        missing.append(f"checkpoint not found: {settings.checkpoint_path}")
    if missing:
        raise ServiceRunnerError("MODEL_RUNTIME_NOT_READY", "V13 runtime files are missing.", " | ".join(missing))


def save_upload_bytes(data: bytes, original_filename: str, input_dir: Path) -> Path:
    suffix = Path(original_filename or "input.jpg").suffix.lower()
    if suffix not in IMAGE_EXTS:
        suffix = ".jpg"
    target = input_dir / f"input{suffix}"
    target.write_bytes(data)
    return target


def run_v13_batch_service(input_dir: Path, output_dir: Path, raw_dir: Path, min_area_pixels: int) -> Dict[str, Any]:
    validate_static_paths()
    command = [
        sys.executable,
        str(settings.batch_service_script),
        "--input_dir",
        str(input_dir.relative_to(settings.repo_root)) if input_dir.is_relative_to(settings.repo_root) else str(input_dir),
        "--outdir",
        str(output_dir.relative_to(settings.repo_root)) if output_dir.is_relative_to(settings.repo_root) else str(output_dir),
        "--model_output_dir",
        str(raw_dir.relative_to(settings.repo_root)) if raw_dir.is_relative_to(settings.repo_root) else str(raw_dir),
        "--config",
        str(settings.config_path.relative_to(settings.repo_root)) if settings.config_path.is_relative_to(settings.repo_root) else str(settings.config_path),
        "--ckpt",
        str(settings.checkpoint_path.relative_to(settings.repo_root)) if settings.checkpoint_path.is_relative_to(settings.repo_root) else str(settings.checkpoint_path),
        "--mode",
        "model",
        "--min_area_pixels",
        str(int(min_area_pixels)),
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(settings.repo_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if completed.returncode != 0:
        raise ServiceRunnerError(
            "V13_BATCH_SERVICE_FAILED",
            "LiteRaceSegNet V13 batch-service runner failed.",
            completed.stderr[-4000:] or completed.stdout[-4000:],
        )
    return {"elapsed_ms": elapsed_ms, "stdout": completed.stdout, "stderr": completed.stderr, "command": command}


def find_first(paths: list[Path]) -> Optional[Path]:
    for path in paths:
        matches = sorted(path.parent.glob(path.name))
        if matches:
            return matches[0]
    return None


def load_json_if_exists(path: Optional[Path]) -> Dict[str, Any]:
    if path and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"_parse_warning": f"Could not parse JSON: {path}"}
    return {}


def summarize_outputs(output_dir: Path, request_dir: Path) -> Dict[str, Any]:
    overlay = find_first([output_dir / "*_service_overlay.png", output_dir / "*overlay*.png"])
    mask = find_first([output_dir / "*_service_mask.png", output_dir / "*mask*.png"])
    summary = find_first([output_dir / "*_service_summary.json", output_dir / "service_batch_summary.json"])
    mode_json = output_dir / "_CAPSTONE_SERVICE_MODE.json"
    raw_summary = load_json_if_exists(summary)
    mode_note = load_json_if_exists(mode_json)

    damage_area_ratio = None
    damage_detected = None
    # Support several likely keys from service-summary scripts.
    for key in ("damage_area_ratio", "damage_ratio", "damage_percent", "positive_ratio"):
        value = raw_summary.get(key)
        if isinstance(value, (int, float)):
            damage_area_ratio = float(value)
            if key == "damage_percent":
                damage_area_ratio = damage_area_ratio / 100.0
            break
    if damage_area_ratio is not None:
        damage_detected = damage_area_ratio > 0

    return {
        "overlay_path": str(overlay.relative_to(settings.repo_root)) if overlay and overlay.is_relative_to(settings.repo_root) else (str(overlay) if overlay else None),
        "mask_path": str(mask.relative_to(settings.repo_root)) if mask and mask.is_relative_to(settings.repo_root) else (str(mask) if mask else None),
        "evidence_json_path": str(summary.relative_to(settings.repo_root)) if summary and summary.is_relative_to(settings.repo_root) else (str(summary) if summary else None),
        "request_dir": str(request_dir.relative_to(settings.repo_root)) if request_dir.is_relative_to(settings.repo_root) else str(request_dir),
        "damage_area_ratio": damage_area_ratio,
        "damage_detected": damage_detected,
        "raw_summary": raw_summary,
        "mode_note": mode_note,
    }
