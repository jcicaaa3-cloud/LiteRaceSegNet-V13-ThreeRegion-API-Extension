from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from PIL import Image

try:
    import cv2  # type: ignore
except Exception as exc:  # pragma: no cover - dependency is listed in requirements_api.txt
    cv2 = None  # type: ignore
    _CV2_IMPORT_ERROR = exc
else:
    _CV2_IMPORT_ERROR = None


@dataclass(frozen=True)
class ThreeRegionPostprocessParams:
    """Heuristic parameters for V13 binary-mask based visualization.

    These parameters do not change the V11-compatible JSON response. They only
    control the separate V13 three-region visualization artifact.
    """

    min_component_area_pixels: int = 8
    min_crack_skeleton_pixels: int = 12
    crack_min_aspect_ratio: float = 3.0
    crack_max_mean_width_ratio: float = 0.030
    crack_max_component_area_ratio: float = 0.035
    major_min_area_ratio: float = 0.004
    major_min_area_pixels: int = 120
    major_min_fill_ratio: float = 0.18
    major_min_mean_width_ratio: float = 0.045
    suspected_dilation_ratio: float = 0.012
    suspected_min_dilation_px: int = 3
    alpha: float = 0.55


CYAN_RGB = np.array([0, 220, 220], dtype=np.float32)
RED_RGB = np.array([255, 35, 35], dtype=np.float32)
YELLOW_RGB = np.array([255, 220, 0], dtype=np.float32)
WHITE_RGB = np.array([255, 255, 255], dtype=np.float32)


class ThreeRegionVisualizationError(RuntimeError):
    pass


def _require_cv2() -> None:
    if cv2 is None:  # pragma: no cover
        raise ThreeRegionVisualizationError(
            "OpenCV is required for three-region morphology post-processing. "
            "Install opencv-python or use requirements_api.txt."
        ) from _CV2_IMPORT_ERROR


def _read_rgb(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Input image not found: {path}")
    return Image.open(path).convert("RGB")


def _read_binary_mask(path: Path, size_wh: Tuple[int, int]) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Mask not found: {path}")
    mask_img = Image.open(path).convert("L")
    if mask_img.size != size_wh:
        mask_img = mask_img.resize(size_wh, Image.Resampling.NEAREST)
    return (np.asarray(mask_img) > 0).astype(np.uint8)


def _maybe_read_binary_mask(path: Optional[Path], size_wh: Tuple[int, int]) -> Optional[np.ndarray]:
    if path is None or not path.exists():
        return None
    try:
        return _read_binary_mask(path, size_wh)
    except Exception:
        return None


def _save_mask(path: Path, mask: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(((mask > 0).astype(np.uint8) * 255)).save(path, compress_level=0)


def _relpath(path: Path, repo_root: Optional[Path]) -> str:
    resolved = path.resolve()
    if repo_root is not None:
        try:
            return resolved.relative_to(repo_root.resolve()).as_posix()
        except Exception:
            pass
    return resolved.as_posix()


def _kernel(radius_px: int) -> np.ndarray:
    _require_cv2()
    radius_px = max(1, int(radius_px))
    size = radius_px * 2 + 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def _binary_boundary(mask: np.ndarray) -> np.ndarray:
    _require_cv2()
    src = (mask > 0).astype(np.uint8)
    if src.sum() == 0:
        return src
    eroded = cv2.erode(src, np.ones((3, 3), dtype=np.uint8), iterations=1)
    return ((src > 0) & (eroded == 0)).astype(np.uint8)


def _morphological_skeleton(mask: np.ndarray) -> np.ndarray:
    """Return a simple binary skeleton using iterative morphology.

    This is intentionally deterministic and dependency-light. It is used only
    to estimate component thinness; it is not a trained crack detector.
    """

    _require_cv2()
    src = ((mask > 0).astype(np.uint8) * 255)
    skel = np.zeros_like(src, dtype=np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        opened = cv2.morphologyEx(src, cv2.MORPH_OPEN, element)
        temp = cv2.subtract(src, opened)
        eroded = cv2.erode(src, element)
        skel = cv2.bitwise_or(skel, temp)
        src = eroded.copy()
        if cv2.countNonZero(src) == 0:
            break
    return (skel > 0).astype(np.uint8)


def _component_contour_features(component: np.ndarray) -> Dict[str, float]:
    _require_cv2()
    comp_u8 = (component > 0).astype(np.uint8)
    contours, _ = cv2.findContours(comp_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    perimeter = 0.0
    for contour in contours:
        perimeter += float(cv2.arcLength(contour, True))
    area = float(comp_u8.sum())
    compactness = 0.0
    if perimeter > 1e-6:
        compactness = float((4.0 * math.pi * area) / (perimeter * perimeter))
    return {"perimeter_pixels": perimeter, "compactness": compactness}


def _component_stats(binary_mask: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    _require_cv2()
    src = (binary_mask > 0).astype(np.uint8)
    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(src, connectivity=8)
    components: List[Dict[str, Any]] = []
    for label_id in range(1, n_labels):
        x, y, w, h, area = [int(v) for v in stats[label_id]]
        if area <= 0:
            continue
        component = (labels == label_id).astype(np.uint8)
        skeleton = _morphological_skeleton(component)
        skeleton_pixels = int(skeleton.sum())
        mean_width = float(area / max(skeleton_pixels, 1))
        dist = cv2.distanceTransform(component, cv2.DIST_L2, 3)
        max_width = float(2.0 * dist.max())
        fill_ratio = float(area / max(w * h, 1))
        aspect_ratio = float(max(w, h) / max(min(w, h), 1))
        contour = _component_contour_features(component)
        components.append(
            {
                "label_id": int(label_id),
                "area_pixels": int(area),
                "bbox_xywh": [x, y, w, h],
                "centroid_xy": [round(float(centroids[label_id][0]), 2), round(float(centroids[label_id][1]), 2)],
                "aspect_ratio": aspect_ratio,
                "fill_ratio": fill_ratio,
                "skeleton_pixels": skeleton_pixels,
                "mean_width_est_px": mean_width,
                "max_width_est_px": max_width,
                "perimeter_pixels": contour["perimeter_pixels"],
                "compactness": contour["compactness"],
            }
        )
    components.sort(key=lambda item: item["area_pixels"], reverse=True)
    return labels, components


def _find_first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for pattern in paths:
        matches = sorted(pattern.parent.glob(pattern.name))
        if matches:
            return matches[0]
    return None


def _find_raw_pred_class(raw_model_output_dir: Optional[Path]) -> Optional[Path]:
    if raw_model_output_dir is None or not raw_model_output_dir.exists():
        return None
    return _find_first_existing(
        [
            raw_model_output_dir / "*_pred_class.png",
            raw_model_output_dir / "*_pred.png",
            raw_model_output_dir / "*_mask.png",
        ]
    )


def _load_probability_candidate(
    raw_model_output_dir: Optional[Path], size_wh: Tuple[int, int]
) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Best-effort support for future V13 probability/logit outputs.

    Current public V13 inference writes class masks. If a future runner saves
    probability maps, this function can use near-threshold pixels as suspected
    candidates without changing the response contract.
    """

    if raw_model_output_dir is None or not raw_model_output_dir.exists():
        return None, None

    npy_path = _find_first_existing(
        [
            raw_model_output_dir / "*_damage_prob.npy",
            raw_model_output_dir / "*_prob_damage.npy",
            raw_model_output_dir / "*_prob.npy",
            raw_model_output_dir / "*_logits.npy",
        ]
    )
    if npy_path is not None:
        try:
            arr = np.load(npy_path)
            arr = np.asarray(arr)
            if arr.ndim == 3:
                # Accept CHW or HWC. Use class-1 probability/logit-like plane.
                if arr.shape[0] in (1, 2):
                    arr = arr[min(1, arr.shape[0] - 1)]
                elif arr.shape[-1] in (1, 2):
                    arr = arr[..., min(1, arr.shape[-1] - 1)]
            arr = arr.astype(np.float32)
            # If the map looks like logits, squeeze with sigmoid for a stable 0..1 scale.
            finite = arr[np.isfinite(arr)]
            if finite.size and (finite.min() < 0.0 or finite.max() > 1.0):
                arr = 1.0 / (1.0 + np.exp(-arr))
            arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
            if arr.shape[::-1] != size_wh:
                _require_cv2()
                arr = cv2.resize(arr, size_wh, interpolation=cv2.INTER_LINEAR)
            return arr, npy_path.as_posix()
        except Exception:
            pass

    png_path = _find_first_existing(
        [
            raw_model_output_dir / "*_damage_prob.png",
            raw_model_output_dir / "*_prob_damage.png",
            raw_model_output_dir / "*_prob.png",
        ]
    )
    if png_path is not None:
        try:
            img = Image.open(png_path).convert("L")
            if img.size != size_wh:
                img = img.resize(size_wh, Image.Resampling.BILINEAR)
            return np.asarray(img).astype(np.float32) / 255.0, png_path.as_posix()
        except Exception:
            pass
    return None, None


def _classify_components(
    binary_mask: np.ndarray, params: ThreeRegionPostprocessParams
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[Dict[str, Any]]]:
    _require_cv2()
    h, w = binary_mask.shape
    image_pixels = max(h * w, 1)
    min_side = max(min(h, w), 1)
    labels, components = _component_stats(binary_mask)

    crack = np.zeros_like(binary_mask, dtype=np.uint8)
    major = np.zeros_like(binary_mask, dtype=np.uint8)
    suspected = np.zeros_like(binary_mask, dtype=np.uint8)

    crack_max_mean_width_px = max(3.0, params.crack_max_mean_width_ratio * min_side)
    major_min_mean_width_px = max(5.0, params.major_min_mean_width_ratio * min_side)
    major_min_area_px = max(params.major_min_area_pixels, int(round(params.major_min_area_ratio * image_pixels)))
    crack_max_area_px = max(params.min_component_area_pixels, int(round(params.crack_max_component_area_ratio * image_pixels)))

    def is_thin_line_like(item: Dict[str, Any]) -> bool:
        return (
            float(item["aspect_ratio"]) >= params.crack_min_aspect_ratio
            and float(item["mean_width_est_px"]) <= crack_max_mean_width_px
            and int(item["skeleton_pixels"]) >= params.min_crack_skeleton_pixels
            and int(item["area_pixels"]) <= crack_max_area_px
        )

    def split_mixed_blob_and_thin_parts(component_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, bool]:
        """Split a connected blob+thin-tail component when the binary mask merged them.

        V13 currently emits a binary foreground mask. A crack touching a pothole
        can therefore become one connected component. For visualization only, we
        keep thick core / non-thin residual pixels as red and route elongated
        thin residual pixels to cyan.
        """

        comp_u8 = (component_mask > 0).astype(np.uint8)
        dist = cv2.distanceTransform(comp_u8, cv2.DIST_L2, 3)
        thick_core = ((dist * 2.0) >= major_min_mean_width_px).astype(np.uint8)
        if int(thick_core.sum()) < params.min_component_area_pixels:
            return comp_u8, np.zeros_like(comp_u8), np.zeros_like(comp_u8), False

        thick_core = cv2.morphologyEx(thick_core, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8))
        expand_radius = max(1, int(round(crack_max_mean_width_px / 2.0)))
        major_part = (cv2.dilate(thick_core, _kernel(expand_radius), iterations=1) > 0) & (comp_u8 > 0)
        residual = ((comp_u8 > 0) & ~major_part).astype(np.uint8)
        if int(residual.sum()) < params.min_component_area_pixels:
            return comp_u8, np.zeros_like(comp_u8), np.zeros_like(comp_u8), False

        # A thick blob often leaves a one-pixel residual rim after core
        # extraction. Keep this near-core rim red; otherwise a pothole boundary
        # can be mislabeled as a cyan crack. Farther elongated residual pixels
        # remain eligible for crack-like visualization.
        near_core_radius = max(2, int(round(major_min_mean_width_px)))
        near_core = (cv2.dilate(thick_core, _kernel(near_core_radius), iterations=1) > 0) & (comp_u8 > 0)
        near_core_residual = (residual > 0) & near_core
        residual_far = ((residual > 0) & ~near_core_residual).astype(np.uint8)

        if int(residual_far.sum()) < params.min_component_area_pixels:
            major_part = (major_part | near_core_residual).astype(np.uint8)
            return major_part, np.zeros_like(comp_u8), np.zeros_like(comp_u8), int(near_core_residual.sum()) > 0

        residual_labels, residual_components = _component_stats(residual_far)
        crack_part = np.zeros_like(comp_u8, dtype=np.uint8)
        uncertain_part = np.zeros_like(comp_u8, dtype=np.uint8)
        noncrack_part = np.zeros_like(comp_u8, dtype=np.uint8)
        for residual_comp in residual_components:
            residual_mask = residual_labels == int(residual_comp["label_id"])
            if int(residual_comp["area_pixels"]) < params.min_component_area_pixels:
                uncertain_part[residual_mask] = 1
            elif is_thin_line_like(residual_comp):
                crack_part[residual_mask] = 1
            else:
                noncrack_part[residual_mask] = 1

        # Keep near-core and non-thin residual pixels red so ordinary pothole
        # rims are not mistaken for cracks just because they are near the
        # boundary.
        major_part = (major_part | near_core_residual | (noncrack_part > 0)).astype(np.uint8)
        did_split = int(crack_part.sum()) > 0 or int(uncertain_part.sum()) > 0
        return major_part.astype(np.uint8), crack_part.astype(np.uint8), uncertain_part.astype(np.uint8), did_split

    classified_components: List[Dict[str, Any]] = []
    for comp in components:
        area = int(comp["area_pixels"])
        label_id = int(comp["label_id"])
        comp_mask = (labels == label_id)
        if area < params.min_component_area_pixels:
            suspected[comp_mask] = 1
            comp_class = "suspected_tiny_component"
        else:
            fill = float(comp["fill_ratio"])
            mean_width = float(comp["mean_width_est_px"])
            compactness = float(comp["compactness"])

            large_enough = area >= major_min_area_px
            blob_like = (
                fill >= params.major_min_fill_ratio
                or mean_width >= major_min_mean_width_px
                or compactness >= 0.16
            )
            thin_line_like = is_thin_line_like(comp)

            if large_enough and blob_like and not thin_line_like:
                major_part, crack_part, uncertain_part, did_split = split_mixed_blob_and_thin_parts(comp_mask)
                major[major_part > 0] = 1
                crack[crack_part > 0] = 1
                suspected[uncertain_part > 0] = 1
                comp_class = (
                    "mixed_major_blob_with_crack_like_thin_parts"
                    if did_split and int(crack_part.sum()) > 0
                    else "major_damage_blob_candidate"
                )
            elif thin_line_like:
                crack[comp_mask] = 1
                comp_class = "crack_like_thin_structure_candidate"
            elif large_enough:
                # Conservative fallback: if it is a non-thin, relatively large
                # foreground component, visualize it as major-damage candidate.
                major[comp_mask] = 1
                comp_class = "major_damage_size_candidate"
            else:
                suspected[comp_mask] = 1
                comp_class = "suspected_uncertain_component"

        comp_out = {k: v for k, v in comp.items() if k != "label_id"}
        comp_out["region"] = comp_class
        classified_components.append(comp_out)

    return crack, major, suspected, classified_components


def _make_suspected_mask(
    binary_mask: np.ndarray,
    suspected_seed: np.ndarray,
    raw_pred_mask: Optional[np.ndarray],
    probability: Optional[np.ndarray],
    params: ThreeRegionPostprocessParams,
) -> np.ndarray:
    _require_cv2()
    h, w = binary_mask.shape
    min_side = max(min(h, w), 1)
    radius_px = max(params.suspected_min_dilation_px, int(round(params.suspected_dilation_ratio * min_side)))
    dilated = cv2.dilate((binary_mask > 0).astype(np.uint8), _kernel(radius_px), iterations=1)
    ring = ((dilated > 0) & (binary_mask == 0)).astype(np.uint8)

    suspected = ((suspected_seed > 0) | (ring > 0)).astype(np.uint8)

    if raw_pred_mask is not None:
        # If the service mask removed tiny raw model foreground regions through
        # min_area post-processing, keep those as yellow candidates rather than
        # silently losing them in the three-region view.
        raw_extra = ((raw_pred_mask > 0) & (binary_mask == 0)).astype(np.uint8)
        suspected = ((suspected > 0) | (raw_extra > 0)).astype(np.uint8)

    if probability is not None:
        # Near-threshold probability/logit regions are candidate zones. They are
        # not reported as confidence or a ground-truth class.
        near_threshold = ((probability >= 0.35) & (probability < 0.50)).astype(np.uint8)
        suspected = ((suspected > 0) | ((near_threshold > 0) & (binary_mask == 0))).astype(np.uint8)

    return suspected.astype(np.uint8)


def _overlay_three_regions(
    image: Image.Image,
    crack: np.ndarray,
    major: np.ndarray,
    suspected: np.ndarray,
    alpha: float,
) -> Image.Image:
    base = np.asarray(image).astype(np.float32)
    out = base.copy()

    # Draw suspected first, then crack/major. This ensures yellow candidate
    # context does not hide the direct V13 foreground interpretation.
    for mask, color in ((suspected, YELLOW_RGB), (crack, CYAN_RGB), (major, RED_RGB)):
        active = mask > 0
        if active.any():
            out[active] = base[active] * (1.0 - alpha) + color * alpha

    # Do not draw a white boundary on top of the three colors. Thin crack-like
    # structures can be only a few pixels wide, so a boundary stroke would hide
    # the cyan region and violate the requested 3-color semantics.
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def _area_ratio(mask: np.ndarray) -> float:
    return float((mask > 0).sum() / max(mask.size, 1))


def _mask_pixels(mask: np.ndarray) -> int:
    return int((mask > 0).sum())


def generate_three_region_visualization(
    *,
    request_id: str,
    input_image_path: Path,
    binary_mask_path: Path,
    request_dir: Path,
    repo_root: Optional[Path] = None,
    raw_model_output_dir: Optional[Path] = None,
    params: Optional[ThreeRegionPostprocessParams] = None,
) -> Dict[str, Any]:
    """Create V13 three-region visualization artifacts without changing V11 JSON.

    Outputs are written as a separate extension JSON plus PNG files:

    runtime_api/requests/<request_id>/v13_visualization.json
    runtime_api/requests/<request_id>/output/crack_mask.png
    runtime_api/requests/<request_id>/output/major_damage_mask.png
    runtime_api/requests/<request_id>/output/suspected_mask.png
    runtime_api/requests/<request_id>/output/three_region_overlay.png
    """

    _require_cv2()
    params = params or ThreeRegionPostprocessParams()
    request_dir = request_dir.resolve()
    output_dir = request_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    image = _read_rgb(input_image_path)
    size_wh = image.size
    binary_mask = _read_binary_mask(binary_mask_path, size_wh)

    raw_pred_path = _find_raw_pred_class(raw_model_output_dir)
    raw_pred = _maybe_read_binary_mask(raw_pred_path, size_wh) if raw_pred_path is not None else None
    probability, probability_source = _load_probability_candidate(raw_model_output_dir, size_wh)

    crack_mask, major_mask, suspected_seed, components = _classify_components(binary_mask, params)
    suspected_mask = _make_suspected_mask(binary_mask, suspected_seed, raw_pred, probability, params)

    # Direct region priority: crack and major are mutually exclusive by component
    # assignment. Remove direct regions from yellow except uncertain foreground
    # components intentionally kept in suspected_seed.
    suspected_mask = ((suspected_mask > 0) & ~((crack_mask > 0) | (major_mask > 0))).astype(np.uint8) | (
        suspected_seed > 0
    ).astype(np.uint8)

    crack_path = output_dir / "crack_mask.png"
    major_path = output_dir / "major_damage_mask.png"
    suspected_path = output_dir / "suspected_mask.png"
    overlay_path = output_dir / "three_region_overlay.png"
    json_path = request_dir / "v13_visualization.json"

    _save_mask(crack_path, crack_mask)
    _save_mask(major_path, major_mask)
    _save_mask(suspected_path, suspected_mask)
    _overlay_three_regions(image, crack_mask, major_mask, suspected_mask, alpha=params.alpha).save(
        overlay_path, compress_level=0
    )

    payload: Dict[str, Any] = {
        "schema_version": "v13_three_region_visualization_0.1",
        "request_id": request_id,
        "source_model_version": "v13",
        "compatibility_baseline": "v11_json_contract_locked",
        "compatibility_mode": "separate_extension_json",
        "postprocess_basis": "v13_binary_mask_with_morphology_heuristics",
        "files": {
            "crack_mask_path": _relpath(crack_path, repo_root),
            "major_damage_mask_path": _relpath(major_path, repo_root),
            "suspected_mask_path": _relpath(suspected_path, repo_root),
            "three_region_overlay_path": _relpath(overlay_path, repo_root),
            "v13_visualization_json_path": _relpath(json_path, repo_root),
        },
        "inputs": {
            "input_image_path": _relpath(input_image_path, repo_root),
            "binary_mask_path": _relpath(binary_mask_path, repo_root),
            "raw_pred_class_path": _relpath(raw_pred_path, repo_root) if raw_pred_path else None,
            "probability_source_path": probability_source,
        },
        "region_summary": {
            "image_pixels": int(binary_mask.size),
            "binary_damage_pixels": _mask_pixels(binary_mask),
            "binary_damage_area_ratio": round(_area_ratio(binary_mask), 8),
            "crack_pixels": _mask_pixels(crack_mask),
            "crack_area_ratio": round(_area_ratio(crack_mask), 8),
            "major_damage_pixels": _mask_pixels(major_mask),
            "major_damage_area_ratio": round(_area_ratio(major_mask), 8),
            "suspected_pixels": _mask_pixels(suspected_mask),
            "suspected_area_ratio": round(_area_ratio(suspected_mask), 8),
        },
        "component_summary_top20": components[:20],
        "color_legend": {
            "crack_like_thin_structure": "cyan/turquoise",
            "pothole_or_major_damage_blob": "red",
            "suspected_or_uncertain_candidate_zone": "yellow",
        },
        "postprocess_parameters": asdict(params),
        "notes": [
            "The original v11-compatible API response is not modified by this extension file.",
            "Crack, major-damage, and suspected regions are heuristic visualization categories derived from the V13 binary output unless a separately trained multi-class model is introduced.",
            "Suspected area is a candidate/uncertain visualization zone, not a ground-truth class and not a calibrated confidence value.",
            "This is a research/capstone/prototype road-damage segmentation visualization, not a certified road safety diagnosis or legal/administrative decision system.",
        ],
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


__all__ = [
    "ThreeRegionPostprocessParams",
    "ThreeRegionVisualizationError",
    "generate_three_region_visualization",
]
