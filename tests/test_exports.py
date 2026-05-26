from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from calibration_designer_v3.core.pipeline import run_design_pipeline
from calibration_designer_v3.io.export import REQUIRED_CSVS, REQUIRED_PNGS, export_design_run
from calibration_designer_v3.models.config import build_example_run_config


def test_export_creates_timestamped_run_folder(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    assert run_folder.exists()
    assert run_folder.name.startswith("design_run_")


def test_required_csv_outputs_exist(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    for filename in REQUIRED_CSVS:
        assert (run_folder / filename).exists(), filename


def test_required_png_outputs_exist(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    for filename in REQUIRED_PNGS:
        assert (run_folder / filename).exists(), filename


def test_run_configuration_json_exists_and_contains_seed(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    cfg_json = run_folder / "run_configuration.json"
    assert cfg_json.exists()

    payload = json.loads(cfg_json.read_text(encoding="utf-8"))
    assert payload["seed"] == 123


def test_exported_compositions_sum_to_1000(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    design_table = pd.read_csv(run_folder / "calibration_design_table.csv")
    assert "is_target_strength" in design_table.columns
    assert "target_strength_name" in design_table.columns
    assert (design_table["sum_weighed_components_mg_g"].sub(1000.0).abs() <= 1e-6).all()


def test_exported_api_ds_uses_api_content_correction(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    design_table = pd.read_csv(run_folder / "calibration_design_table.csv")
    calc = design_table["api_pure_mg_g"] / design_table["api_content_mg_mg"]
    assert (design_table["api_ds_total_mg_g"] - calc).abs().max() < 1e-9


def test_material_consumption_summary_contains_required_api_rows(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    summary = pd.read_csv(run_folder / "material_consumption_summary.csv")
    assert "API pure equivalent" in summary["component"].values
    assert "API drug substance weighed" in summary["component"].values
    assert "API impurity/material fraction" in summary["component"].values


def test_diagnostics_summary_contains_pairwise_metrics(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    summary = pd.read_csv(run_folder / "design_diagnostics_summary.csv")
    metrics = set(summary["metric"].tolist())
    assert "pairwise_plot_count" in metrics
    assert "target_strength_points_in_design" in metrics
