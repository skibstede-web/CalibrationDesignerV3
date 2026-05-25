from __future__ import annotations

from pathlib import Path

from calibration_designer_v3.core.pipeline import run_design_pipeline
from calibration_designer_v3.io.config_io import load_run_config


def test_example_config_generates_design() -> None:
    config_path = Path(__file__).resolve().parents[1] / "examples" / "example_run_config.json"
    cfg = load_run_config(config_path)
    result = run_design_pipeline(cfg)
    assert len(result.design.batches) > 0