#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

# Keep local smoke tests lightweight in constrained CI/sandbox environments.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.three_region_visualization import generate_three_region_visualization  # noqa: E402


def main() -> int:
    rid = "smoke_three_region"
    request_dir = ROOT / "runtime_api" / "requests" / rid
    if request_dir.exists():
        shutil.rmtree(request_dir)
    (request_dir / "input").mkdir(parents=True, exist_ok=True)
    (request_dir / "output").mkdir(parents=True, exist_ok=True)
    (request_dir / "raw_model_output").mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (240, 160), (95, 95, 95))
    draw = ImageDraw.Draw(image)
    draw.line((0, 130, 240, 120), fill=(135, 135, 135), width=4)
    image_path = request_dir / "input" / "input.jpg"
    image.save(image_path)

    mask = Image.new("L", image.size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.line((25, 105, 180, 88), fill=255, width=3)  # crack-like thin structure
    draw_mask.ellipse((150, 55, 210, 112), fill=255)       # blob-like damage
    draw_mask.rectangle((40, 35, 45, 39), fill=255)        # uncertain small component
    mask_path = request_dir / "output" / "input_service_mask.png"
    mask.save(mask_path)

    # Raw model output includes one extra weak/noisy region to be visualized as suspected.
    raw = np.asarray(mask).copy()
    raw[20:25, 200:212] = 255
    Image.fromarray(raw).save(request_dir / "raw_model_output" / "input_pred_class.png")

    payload = generate_three_region_visualization(
        request_id=rid,
        input_image_path=image_path,
        binary_mask_path=mask_path,
        request_dir=request_dir,
        repo_root=ROOT,
        raw_model_output_dir=request_dir / "raw_model_output",
    )
    required = [
        request_dir / "v13_visualization.json",
        request_dir / "output" / "crack_mask.png",
        request_dir / "output" / "major_damage_mask.png",
        request_dir / "output" / "suspected_mask.png",
        request_dir / "output" / "three_region_overlay.png",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing smoke-test outputs: {missing}")
    summary = payload["region_summary"]
    if summary["crack_pixels"] <= 0 or summary["major_damage_pixels"] <= 0 or summary["suspected_pixels"] <= 0:
        raise AssertionError(f"Expected non-empty three regions, got: {json.dumps(summary, indent=2)}")
    print("OK: three-region postprocess smoke test generated all extension artifacts.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
