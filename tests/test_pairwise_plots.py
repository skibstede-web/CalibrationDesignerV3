from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from calibration_designer_v3.core.pipeline import run_design_pipeline
from calibration_designer_v3.io.export import export_design_run
from calibration_designer_v3.models.config import build_example_run_config
from calibration_designer_v3.models.domain import (
    BatchSettings,
    ComponentConstraint,
    ComponentSpec,
    ProductStrength,
    RunConfig,
)
from calibration_designer_v3.plotting.plots import (
    PAIRWISE_MANIFEST_FILENAME,
    annotate_target_strength_columns,
    build_pairwise_plot_variables,
    create_pairwise_component_plots,
)


def _config_with_components(component_names: list[str]) -> RunConfig:
    api_name = component_names[0]
    balance_name = component_names[1]
    components = []
    constraints = []
    targets: dict[str, float] = {}
    for i, name in enumerate(component_names):
        is_api = i == 0
        is_balance = i == 1
        components.append(
            ComponentSpec(
                name=name,
                is_api=is_api,
                is_balance=is_balance,
                component_type="api" if is_api else "major_excipient",
            )
        )
        constraints.append(
            ComponentConstraint(
                component_name=name,
                min_mg_g=0.0 if is_api else 1.0,
                max_mg_g=100.0 if is_api else 900.0,
                preferred_levels=3 if is_api else 1,
            )
        )
        if is_api:
            targets[name] = 10.0
        elif is_balance:
            targets[name] = 700.0
        else:
            targets[name] = 100.0

    return RunConfig(
        components=components,
        api_content_mg_mg=0.8,
        product_strengths=[ProductStrength(name="T1", component_targets_mg_g=targets)],
        component_constraints=constraints,
        batch_settings=BatchSettings(desired_batches=6, min_batches=3, max_batches=10),
    )


def _example_design_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "batch_id": "CAL-001",
                "batch_role": "calibration",
                "source": "generated",
                "forced": False,
                "api_pure_mg_g": 8.0,
                "api_ds_total_mg_g": 10.0,
                "SNAC_mg_g": 530.0,
                "Niacinamide_mg_g": 447.5,
                "Glidant_mg_g": 12.5,
                "sum_weighed_components_mg_g": 1000.0,
            },
            {
                "batch_id": "CAL-002",
                "batch_role": "target_strength",
                "source": "generated",
                "forced": False,
                "api_pure_mg_g": 10.0,
                "api_ds_total_mg_g": 12.5,
                "SNAC_mg_g": 520.5,
                "Niacinamide_mg_g": 452.0,
                "Glidant_mg_g": 15.0,
                "sum_weighed_components_mg_g": 1000.0,
            },
            {
                "batch_id": "CAL-003",
                "batch_role": "calibration",
                "source": "generated",
                "forced": False,
                "api_pure_mg_g": 14.0,
                "api_ds_total_mg_g": 17.5,
                "SNAC_mg_g": 502.0,
                "Niacinamide_mg_g": 465.0,
                "Glidant_mg_g": 15.5,
                "sum_weighed_components_mg_g": 1000.0,
            },
        ]
    )


def test_pairwise_variable_selection_includes_api_and_non_api_excludes_api_ds() -> None:
    cfg = build_example_run_config()
    design = _example_design_table()
    variables = build_pairwise_plot_variables(cfg, design)
    names = [name for name, _ in variables]
    cols = [col for _, col in variables]

    assert "API_pure" in names
    assert "SNAC" in names
    assert "Niacinamide" in names
    assert "Glidant" in names
    assert "api_ds_total_mg_g" not in cols


def test_pairwise_combination_count_for_4_variables_is_6() -> None:
    cfg = build_example_run_config()
    design = _example_design_table()
    variables = build_pairwise_plot_variables(cfg, design)
    assert len(variables) == 4
    assert len(variables) * (len(variables) - 1) // 2 == 6


def test_pairwise_combination_count_for_5_variables_is_10() -> None:
    cfg = _config_with_components(["API", "SNAC", "Niacinamide", "Glidant", "Colorant"])
    design = pd.DataFrame(
        [
            {
                "batch_id": "CAL-001",
                "batch_role": "calibration",
                "source": "generated",
                "forced": False,
                "api_pure_mg_g": 10.0,
                "SNAC_mg_g": 700.0,
                "Niacinamide_mg_g": 100.0,
                "Glidant_mg_g": 100.0,
                "Colorant_mg_g": 87.5,
            }
        ]
    )
    variables = build_pairwise_plot_variables(cfg, design)
    assert len(variables) == 5
    assert len(variables) * (len(variables) - 1) // 2 == 10


def test_target_strength_detection_by_role_and_nominal_match() -> None:
    cfg = build_example_run_config()
    design = _example_design_table()
    annotated = annotate_target_strength_columns(design_table=design, config=cfg, tolerance_mg_g=0.001)

    row_by_id = {row["batch_id"]: row for _, row in annotated.iterrows()}
    assert bool(row_by_id["CAL-002"]["is_target_strength"]) is True
    assert row_by_id["CAL-002"]["target_strength_name"] in {"1%", ""}

    assert bool(row_by_id["CAL-001"]["is_target_strength"]) is False


def test_target_strength_detection_by_forced_flag() -> None:
    cfg = build_example_run_config()
    design = _example_design_table().copy()
    design.loc[0, "forced"] = True
    annotated = annotate_target_strength_columns(design_table=design, config=cfg, tolerance_mg_g=0.001)
    assert bool(annotated.loc[annotated["batch_id"] == "CAL-001", "is_target_strength"].iloc[0]) is True


def test_pairwise_plot_files_and_manifest_created(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    design = _example_design_table()
    manifest = create_pairwise_component_plots(
        config=cfg,
        design_table=design,
        output_root=local_tmp_path,
        tolerance_mg_g=0.001,
    )

    assert len(manifest) == 6
    assert set(["plot_file", "x_variable", "y_variable", "n_points", "n_target_points"]).issubset(manifest.columns)

    files = sorted(local_tmp_path.glob("*.png"))
    assert len(files) == 6
    for f in files:
        assert re.match(r"^pairwise_[A-Za-z0-9_]+_vs_[A-Za-z0-9_]+\.png$", f.name)

    manifest_path = local_tmp_path / PAIRWISE_MANIFEST_FILENAME
    assert manifest_path.exists()
    loaded = pd.read_csv(manifest_path)
    assert len(loaded) == 6


def test_export_smoke_creates_pairwise_plots_for_manual_case(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    run_folder = export_design_run(cfg, result, output_root=local_tmp_path)

    pairwise_dir = run_folder / "plots" / "pairwise"
    manifest_path = pairwise_dir / PAIRWISE_MANIFEST_FILENAME
    assert pairwise_dir.exists()
    assert manifest_path.exists()

    manifest = pd.read_csv(manifest_path)
    assert len(manifest) == 6
