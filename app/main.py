from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .schemas import (
    FileLinks,
    HealthResponse,
    InputInfo,
    ModelInfo,
    ResultClass,
    RuntimeInfo,
    SegmentResponse,
    SegmentationResult,
)
from .service_runner import (
    ServiceRunnerError,
    make_request_id,
    prepare_request_dirs,
    run_v13_batch_service,
    safe_request_id,
    save_upload_bytes,
    summarize_outputs,
)
from .settings import settings
from .three_region_visualization import generate_three_region_visualization

app = FastAPI(
    title="LiteRaceSegNet V13 API Server",
    version="v13-api-ready-addon",
    description="Backend integration layer for LiteRaceSegNet V13 road-damage segmentation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.runtime_root.mkdir(parents=True, exist_ok=True)
app.mount("/runtime_api", StaticFiles(directory=str(settings.runtime_root.parent)), name="runtime_api")

SAFETY_WARNING = (
    "This is a pilot-scale research/capstone prototype output, not a certified road safety diagnosis."
)


def _resolve_output_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else settings.repo_root / path


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _generate_v13_visualization_extension(
    *,
    request_id: str,
    saved_input_path: Path,
    mask_path_value: str | None,
    request_dir: Path,
    raw_dir: Path,
) -> Dict[str, Any] | None:
    """Generate separate V13 visualization artifacts without changing API response shape."""
    mask_path = _resolve_output_path(mask_path_value)
    if mask_path is None or not mask_path.exists():
        error_payload = {
            "schema_version": "v13_three_region_visualization_0.1",
            "request_id": request_id,
            "status": "skipped",
            "reason": "v13 service mask was not found",
            "compatibility_mode": "separate_extension_json",
        }
        _write_json(request_dir / "v13_visualization.json", error_payload)
        return error_payload
    try:
        return generate_three_region_visualization(
            request_id=request_id,
            input_image_path=saved_input_path,
            binary_mask_path=mask_path,
            request_dir=request_dir,
            repo_root=settings.repo_root,
            raw_model_output_dir=raw_dir,
        )
    except Exception as exc:
        # Do not fail or reshape the legacy-compatible response because this is
        # an extension artifact. The error is kept in the extension JSON only.
        error_payload = {
            "schema_version": "v13_three_region_visualization_0.1",
            "request_id": request_id,
            "status": "failed",
            "compatibility_mode": "separate_extension_json",
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
        }
        _write_json(request_dir / "v13_visualization.json", error_payload)
        return error_payload


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    checkpoint_exists = settings.checkpoint_path.exists()
    config_exists = settings.config_path.exists()
    batch_service_exists = settings.batch_service_script.exists()
    warnings = []
    if not checkpoint_exists:
        warnings.append("V13 checkpoint is not present. Set LRS_CKPT or place best.pth at the expected path.")
    if not config_exists:
        warnings.append("V13 config is not present. Set LRS_CONFIG or copy the expected yaml file.")
    if not batch_service_exists:
        warnings.append("V13 capstone batch-service script is not present. Run from the repository root.")
    return HealthResponse(
        status="ok" if checkpoint_exists and config_exists and batch_service_exists else "not_ready",
        model_loaded=checkpoint_exists and config_exists and batch_service_exists,
        checkpoint_exists=checkpoint_exists,
        config_exists=config_exists,
        batch_service_exists=batch_service_exists,
        warnings=warnings,
    )


@app.get("/api/v1/model-info")
def model_info() -> dict:
    return {
        "name": "LiteRaceSegNet",
        "version": "v13",
        "task": "road_damage_semantic_segmentation",
        "config_path": str(settings.config_path),
        "checkpoint_path": str(settings.checkpoint_path),
        "batch_service_script": str(settings.batch_service_script),
        "class_mapping": {"0": "background", "1": "pothole_or_road_damage"},
        "disclaimer": SAFETY_WARNING,
    }


@app.get("/api/v1/results/{request_id}/v13-visualization")
def get_v13_visualization(request_id: str) -> dict:
    """Return the separate V13 three-region visualization JSON, if it exists.

    This endpoint is intentionally separate from the v11-compatible segmentation
    response so strict legacy clients can keep parsing the old JSON path.
    """
    rid = safe_request_id(request_id)
    path = settings.runtime_root / rid / "v13_visualization.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "V13_VISUALIZATION_NOT_FOUND",
                "message": "No V13 three-region visualization JSON exists for this request_id.",
            },
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "V13_VISUALIZATION_JSON_INVALID",
                "message": "The V13 visualization JSON could not be parsed.",
                "detail": str(exc),
            },
        )


@app.post("/api/v1/road-damage/segment", response_model=SegmentResponse)
async def segment_road_damage(
    file: UploadFile = File(...),
    request_id: str | None = Form(default=None),
    return_mask: bool = Form(default=True),
    return_overlay: bool = Form(default=True),
    return_evidence_json: bool = Form(default=True),
    min_area_pixels: int = Form(default=settings.default_min_area_pixels),
) -> SegmentResponse:
    rid = safe_request_id(request_id or make_request_id())
    dirs = prepare_request_dirs(rid)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_UPLOAD", "message": "Uploaded file is empty."})
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail={"code": "UPLOAD_TOO_LARGE", "message": "Uploaded image exceeds server limit."},
        )

    saved_path = save_upload_bytes(data, file.filename or "input.jpg", dirs["input_dir"])

    try:
        runtime = run_v13_batch_service(
            input_dir=dirs["input_dir"],
            output_dir=dirs["output_dir"],
            raw_dir=dirs["raw_dir"],
            min_area_pixels=min_area_pixels,
        )
    except ServiceRunnerError as exc:
        raise HTTPException(status_code=500, detail={"code": exc.code, "message": exc.message, "detail": exc.detail})

    output = summarize_outputs(dirs["output_dir"], dirs["request_dir"])

    mask_path = output["mask_path"] if return_mask else None
    overlay_path = output["overlay_path"] if return_overlay else None
    evidence_json_path = output["evidence_json_path"] if return_evidence_json else None

    predicted = []
    if output["damage_detected"] is True:
        predicted.append(ResultClass(class_id=1, class_name="pothole_or_road_damage", area_ratio=output["damage_area_ratio"]))

    warnings = [SAFETY_WARNING]
    if output["mode_note"].get("warning"):
        warnings.append(str(output["mode_note"]["warning"]))
    if not overlay_path:
        warnings.append("Overlay file was not found in the V13 service output folder.")
    if not mask_path:
        warnings.append("Mask file was not found in the V13 service output folder.")

    _generate_v13_visualization_extension(
        request_id=rid,
        saved_input_path=saved_path,
        mask_path_value=output["mask_path"],
        request_dir=dirs["request_dir"],
        raw_dir=dirs["raw_dir"],
    )

    response = SegmentResponse(
        request_id=rid,
        status="success",
        model=ModelInfo(checkpoint=str(settings.checkpoint_path)),
        input=InputInfo(original_filename=file.filename or "input.jpg", saved_path=str(saved_path)),
        result=SegmentationResult(
            damage_detected=output["damage_detected"],
            damage_area_ratio=output["damage_area_ratio"],
            predicted_classes=predicted,
            raw_summary=output["raw_summary"],
        ),
        files=FileLinks(
            mask_path=mask_path,
            overlay_path=overlay_path,
            evidence_json_path=evidence_json_path,
            request_dir=output["request_dir"],
        ),
        runtime=RuntimeInfo(latency_ms=runtime["elapsed_ms"]),
        warnings=warnings,
    )

    # Store the exact legacy-compatible response body as a file for audit/replay.
    # The response schema itself is not changed by the V13 visualization extension.
    _write_json(dirs["request_dir"] / "result.json", response.model_dump(mode="json"))
    return response
