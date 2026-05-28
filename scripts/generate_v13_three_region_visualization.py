#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.three_region_visualization import generate_three_region_visualization  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate V13 three-region visualization artifacts from an existing V13 image + binary mask."
    )
    parser.add_argument("--request_id", required=True)
    parser.add_argument("--image", required=True, help="Input road image path")
    parser.add_argument("--mask", required=True, help="V13 binary/service mask path")
    parser.add_argument(
        "--request_dir",
        required=True,
        help="runtime_api/requests/<request_id> directory where v13_visualization.json will be written",
    )
    parser.add_argument("--raw_model_output_dir", default=None, help="Optional raw_model_output folder with *_pred_class.png")
    parser.add_argument("--repo_root", default=str(ROOT), help="Repository root used for relative JSON paths")
    args = parser.parse_args()

    payload = generate_three_region_visualization(
        request_id=args.request_id,
        input_image_path=Path(args.image),
        binary_mask_path=Path(args.mask),
        request_dir=Path(args.request_dir),
        repo_root=Path(args.repo_root),
        raw_model_output_dir=Path(args.raw_model_output_dir) if args.raw_model_output_dir else None,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
