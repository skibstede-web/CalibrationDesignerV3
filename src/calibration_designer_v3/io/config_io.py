"""Read/write run configuration files."""

from __future__ import annotations

import json
from pathlib import Path

from calibration_designer_v3.models.domain import RunConfig


def load_run_config(path: str | Path) -> RunConfig:
    file_path = Path(path)
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return RunConfig.model_validate(payload)


def save_run_config(config: RunConfig, path: str | Path) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(config.model_dump(), indent=2), encoding="utf-8")