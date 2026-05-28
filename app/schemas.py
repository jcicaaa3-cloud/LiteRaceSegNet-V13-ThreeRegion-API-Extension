from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    name: str = "LiteRaceSegNet"
    version: str = "v13"
    task: str = "road_damage_semantic_segmentation"
    checkpoint: Optional[str] = None


class InputInfo(BaseModel):
    original_filename: str
    saved_path: str
    input_type: str = "multipart"


class RuntimeInfo(BaseModel):
    device: str = "server-configured"
    latency_ms: Optional[float] = None
    backend_runner: str = "seg/capstone_batch_service.py"


class ResultClass(BaseModel):
    class_id: int
    class_name: str
    area_ratio: Optional[float] = None


class SegmentationResult(BaseModel):
    damage_detected: Optional[bool] = None
    damage_area_ratio: Optional[float] = None
    predicted_classes: List[ResultClass] = Field(default_factory=list)
    raw_summary: Dict[str, Any] = Field(default_factory=dict)


class FileLinks(BaseModel):
    mask_path: Optional[str] = None
    overlay_path: Optional[str] = None
    evidence_json_path: Optional[str] = None
    request_dir: str


class SegmentResponse(BaseModel):
    request_id: str
    status: str
    model: ModelInfo
    input: InputInfo
    result: SegmentationResult
    files: FileLinks
    runtime: RuntimeInfo
    warnings: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str = "v13"
    checkpoint_exists: bool
    config_exists: bool
    batch_service_exists: bool
    warnings: List[str] = Field(default_factory=list)


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None
