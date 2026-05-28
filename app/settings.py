from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Runtime paths for the V13 API add-on.

    The API server is intended to be launched from the V13 repository root.
    Environment variables can override paths without changing source code.
    """

    def __init__(self) -> None:
        self.repo_root = Path(os.getenv("LRS_REPO_ROOT", ".")).resolve()
        self.runtime_root = Path(os.getenv("LRS_RUNTIME_ROOT", self.repo_root / "runtime_api" / "requests")).resolve()
        self.config_path = Path(
            os.getenv("LRS_CONFIG", self.repo_root / "seg" / "config" / "pothole_binary_literace_train.yaml")
        ).resolve()
        self.checkpoint_path = Path(
            os.getenv("LRS_CKPT", self.repo_root / "seg" / "runs" / "literace_boundary_degradation" / "best.pth")
        ).resolve()
        self.batch_service_script = Path(
            os.getenv("LRS_BATCH_SERVICE", self.repo_root / "seg" / "capstone_batch_service.py")
        ).resolve()
        self.api_host = os.getenv("LRS_API_HOST", "127.0.0.1")
        self.api_port = int(os.getenv("LRS_API_PORT", "8000"))
        self.max_upload_bytes = int(os.getenv("LRS_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
        self.default_min_area_pixels = int(os.getenv("LRS_MIN_AREA_PIXELS", "80"))


settings = Settings()
