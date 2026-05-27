from __future__ import annotations

import re
from pathlib import Path

import pytest
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from calibration_designer_v3.core.pipeline import run_design_pipeline
from calibration_designer_v3.io.export import export_design_run
from calibration_designer_v3.models.config import build_example_run_config
from calibration_designer_v3.models.domain import (
    ApiCalibrationRangeSettings,
    BatchSettings,
    ComponentConstraint,
    ComponentSpec,
    ProductStrength,
    RunConfig,
)
from calibration_designer_v3.plotting.plots import (
    PAIRWISE_MANIFEST_FILENAME,
    annotate_target_strength_columns,
    api_value_to_y_position,
    build_api_calibration_range_whiskers,
    build_batch_reuse_map_plot_data,
    build_component_correlation_plot_matrix,
    build_component_label_map,
    build_material_consumption_plot_data,
    build_pairwise_plot_variables,
    create_pairwise_component_plots,
    plot_batch_reuse_map,
    plot_component_correlation_heatmap,
    plot_material_consumption,
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

    assert "API" in names
    assert "SNAC" in names
    assert "Niacinamide" in names
    assert "Glidant" in names
    assert "api_ds_total_mg_g" not in cols


def test_component_plot_labels_use_user_defined_component_names() -> None:
    cfg = _config_with_components(["Semaglutide", "SNAC", "Niacinamide", "Magnesium stearate"])

    label_map = build_component_label_map(cfg)

    assert label_map["api_pure_mg_g"] == "Semaglutide"
    assert label_map["SNAC_mg_g"] == "SNAC"
    assert label_map["niacinamide_mg_g"] == "Niacinamide"
    assert label_map["Magnesium stearate_mg_g"] == "Magnesium stearate"
    assert "api_pure_mg_g" not in label_map.values()
    assert "api_ds_total_mg_g" not in label_map.values()


def test_correlation_plot_matrix_uses_user_names_and_excludes_internal_duplicates() -> None:
    cfg = _config_with_components(["Semaglutide", "SNAC", "Niacinamide", "Magnesium stearate"])
    internal_columns = [
        "api_pure_mg_g",
        "api_ds_total_mg_g",
        "SNAC_mg_g",
        "niacinamide_mg_g",
        "Magnesium stearate_mg_g",
        "balance_mg_g",
    ]
    values = pd.DataFrame(1.0, index=internal_columns, columns=internal_columns)

    plot_matrix = build_component_correlation_plot_matrix(values, cfg)
    labels = list(plot_matrix.columns)

    assert labels == ["Semaglutide", "SNAC", "Niacinamide", "Magnesium stearate"]
    assert "api_pure_mg_g" not in labels
    assert "api_ds_total_mg_g" not in labels
    assert "balance_mg_g" not in labels
    assert "niacinamide_mg_g" not in labels


def test_heatmap_plot_file_created_with_user_label_mapping(local_tmp_path: Path) -> None:
    cfg = _config_with_components(["Semaglutide", "SNAC", "Niacinamide", "Magnesium stearate"])
    internal_columns = [
        "api_pure_mg_g",
        "SNAC_mg_g",
        "Niacinamide_mg_g",
        "Magnesium stearate_mg_g",
    ]
    values = pd.DataFrame(
        [
            [1.0, 0.2, -0.1, 0.0],
            [0.2, 1.0, 0.3, -0.2],
            [-0.1, 0.3, 1.0, 0.1],
            [0.0, -0.2, 0.1, 1.0],
        ],
        index=internal_columns,
        columns=internal_columns,
    )
    output_path = local_tmp_path / "component_correlation_heatmap.png"

    plot_component_correlation_heatmap(values, output_path, config=cfg)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_material_consumption_plot_data_has_one_row_per_user_component() -> None:
    material_consumption = pd.DataFrame(
        [
            {"component": "Semaglutide", "total_mass_g": 12.5, "total_mass_kg": 0.0125},
            {"component": "SNAC", "total_mass_g": 100.0, "total_mass_kg": 0.1},
            {"component": "API pure equivalent", "total_mass_g": 10.0, "total_mass_kg": 0.01},
            {"component": "API drug substance weighed", "total_mass_g": 12.5, "total_mass_kg": 0.0125},
            {"component": "API impurity/material fraction", "total_mass_g": 2.5, "total_mass_kg": 0.0025},
        ]
    )

    plot_data = build_material_consumption_plot_data(material_consumption)

    assert plot_data["component"].tolist() == ["Semaglutide", "SNAC"]
    assert len(plot_data) == 2
    assert float(plot_data.loc[plot_data["component"] == "Semaglutide", "total_mass_g"].iloc[0]) == pytest.approx(12.5)


def test_material_consumption_plot_data_uses_api_ds_for_api_component() -> None:
    api_pure_mg_g = 10.0
    api_content_mg_mg = 0.8
    batch_size_kg = 1.0
    api_ds_consumption_g = api_pure_mg_g / api_content_mg_mg * batch_size_kg
    material_consumption = pd.DataFrame(
        [
            {"component": "API", "total_mass_g": api_ds_consumption_g, "total_mass_kg": api_ds_consumption_g / 1000.0},
            {"component": "Filler", "total_mass_g": 987.5, "total_mass_kg": 0.9875},
            {"component": "API pure equivalent", "total_mass_g": api_pure_mg_g, "total_mass_kg": 0.01},
            {
                "component": "API drug substance weighed",
                "total_mass_g": api_ds_consumption_g,
                "total_mass_kg": api_ds_consumption_g / 1000.0,
            },
        ]
    )

    plot_data = build_material_consumption_plot_data(material_consumption)

    api_bar_value = float(plot_data.loc[plot_data["component"] == "API", "total_mass_g"].iloc[0])
    assert api_bar_value == pytest.approx(12.5)
    assert api_bar_value != pytest.approx(10.0)


def test_material_consumption_plot_png_created(local_tmp_path: Path) -> None:
    material_consumption = pd.DataFrame(
        [
            {"component": "API", "total_mass_g": 12.5, "total_mass_kg": 0.0125},
            {"component": "Excipient", "total_mass_g": 987.5, "total_mass_kg": 0.9875},
            {"component": "API pure equivalent", "total_mass_g": 10.0, "total_mass_kg": 0.01},
            {"component": "API drug substance weighed", "total_mass_g": 12.5, "total_mass_kg": 0.0125},
        ]
    )
    output_path = local_tmp_path / "material_consumption.png"

    plot_material_consumption(material_consumption, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


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


def _reuse_map_design_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "batch_id": "CAL-LOW",
                "batch_role": "calibration",
                "source": "generated",
                "forced": False,
                "api_pure_mg_g": 5.0,
                "is_target_strength": False,
            },
            {
                "batch_id": "CAL-HIGH",
                "batch_role": "calibration",
                "source": "generated",
                "forced": False,
                "api_pure_mg_g": 30.0,
                "is_target_strength": False,
            },
            {
                "batch_id": "CAL-TARGET",
                "batch_role": "target_strength",
                "source": "generated",
                "forced": False,
                "api_pure_mg_g": 10.0,
                "is_target_strength": True,
            },
        ]
    )


def _reuse_map_assignments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"batch_id": "CAL-LOW", "strength_model": "Strength 1", "included": True, "role_in_model": "primary"},
            {"batch_id": "CAL-HIGH", "strength_model": "Strength 2", "included": True, "role_in_model": "primary"},
            {"batch_id": "CAL-TARGET", "strength_model": "Strength 1", "included": True, "role_in_model": "primary"},
        ]
    )


def test_batch_reuse_map_rows_sort_by_api_pure_descending() -> None:
    plot_data = build_batch_reuse_map_plot_data(
        assignments=_reuse_map_assignments(),
        design_table=_reuse_map_design_table(),
    )

    assert plot_data["batch_ids"] == ["CAL-HIGH", "CAL-TARGET", "CAL-LOW"]
    assert plot_data["api_pure_mg_g"] == [30.0, 10.0, 5.0]


def test_batch_reuse_map_matrix_codes_empty_non_target_and_target() -> None:
    plot_data = build_batch_reuse_map_plot_data(
        assignments=_reuse_map_assignments(),
        design_table=_reuse_map_design_table(),
    )

    matrix = plot_data["matrix"]
    assert matrix.tolist() == [
        [0, 1],
        [2, 0],
        [1, 0],
    ]


def test_batch_reuse_map_target_detection_from_role_when_flag_missing() -> None:
    design_table = _reuse_map_design_table().drop(columns=["is_target_strength"])
    plot_data = build_batch_reuse_map_plot_data(
        assignments=_reuse_map_assignments(),
        design_table=design_table,
    )

    assert plot_data["is_target_strength"] == [False, True, False]


def test_batch_reuse_map_target_name_overrides_non_target_flag() -> None:
    design_table = _reuse_map_design_table()
    design_table.loc[design_table["batch_id"] == "CAL-TARGET", "batch_role"] = "calibration"
    design_table.loc[design_table["batch_id"] == "CAL-TARGET", "is_target_strength"] = False
    design_table.loc[design_table["batch_id"] == "CAL-TARGET", "target_strength_name"] = "Strength 1"

    plot_data = build_batch_reuse_map_plot_data(
        assignments=_reuse_map_assignments(),
        design_table=design_table,
    )

    assert plot_data["matrix"].tolist()[1][0] == 2
    assert plot_data["is_target_strength"] == [False, True, False]


def test_batch_reuse_map_nominal_target_match_gives_target_state() -> None:
    cfg = build_example_run_config()
    design_table = _example_design_table().copy()
    design_table.loc[design_table["batch_id"] == "CAL-002", "batch_role"] = "calibration"
    design_table.loc[design_table["batch_id"] == "CAL-002", "source"] = "generated"
    design_table.loc[design_table["batch_id"] == "CAL-002", "forced"] = False
    design_table.loc[design_table["batch_id"] == "CAL-002", "is_target_strength"] = False
    design_table.loc[design_table["batch_id"] == "CAL-002", "target_strength_name"] = ""
    assignments = pd.DataFrame(
        [
            {"batch_id": "CAL-002", "strength_model": "1%", "included": True, "role_in_model": "primary"},
        ]
    )

    plot_data = build_batch_reuse_map_plot_data(
        assignments=assignments,
        design_table=design_table,
        config=cfg,
        tolerance_mg_g=0.001,
    )

    assert plot_data["matrix"].tolist() == [[0], [2], [0]]


def test_api_calibration_range_whiskers_percent_of_target() -> None:
    cfg = build_example_run_config()
    cfg.product_strengths = [
        ProductStrength(name="Strength 1", component_targets_mg_g={"API": 10.0}),
        ProductStrength(name="Strength 2", component_targets_mg_g={"API": 30.0}),
        ProductStrength(name="Strength 3", component_targets_mg_g={"API": 50.0}),
        ProductStrength(name="Strength 4", component_targets_mg_g={"API": 100.0}),
    ]
    cfg.api_calibration_range_settings = ApiCalibrationRangeSettings(
        mode="percent_of_target",
        lower=50.0,
        upper=150.0,
        api_levels=5,
        include_target_api_level=True,
    )

    ranges = build_api_calibration_range_whiskers(
        config=cfg,
        strength_models=["Strength 1", "Strength 2", "Strength 3", "Strength 4"],
    )

    assert [(row["lower_api_mg_g"], row["upper_api_mg_g"]) for row in ranges] == [
        (5.0, 15.0),
        (15.0, 45.0),
        (25.0, 75.0),
        (50.0, 150.0),
    ]


def test_api_calibration_range_whiskers_absolute_mg_g() -> None:
    cfg = build_example_run_config()
    cfg.product_strengths = [
        ProductStrength(name="Strength 1", component_targets_mg_g={"API": 10.0}),
        ProductStrength(name="Strength 2", component_targets_mg_g={"API": 30.0}),
    ]
    cfg.api_calibration_range_settings = ApiCalibrationRangeSettings(
        mode="absolute_mg_g",
        lower=5.0,
        upper=55.0,
        api_levels=5,
        include_target_api_level=True,
    )

    ranges = build_api_calibration_range_whiskers(config=cfg, strength_models=["Strength 1", "Strength 2"])

    assert [(row["lower_api_mg_g"], row["upper_api_mg_g"]) for row in ranges] == [(5.0, 55.0), (5.0, 55.0)]


def test_api_value_to_y_position_maps_higher_api_toward_top() -> None:
    sorted_api_values = [100.0, 50.0, 10.0]

    assert api_value_to_y_position(100.0, sorted_api_values) == pytest.approx(0.0)
    assert api_value_to_y_position(50.0, sorted_api_values) == pytest.approx(1.0)
    assert api_value_to_y_position(10.0, sorted_api_values) == pytest.approx(2.0)
    assert api_value_to_y_position(75.0, sorted_api_values) == pytest.approx(0.5)
    assert api_value_to_y_position(150.0, sorted_api_values) == pytest.approx(0.0)
    assert api_value_to_y_position(5.0, sorted_api_values) == pytest.approx(2.0)


def test_batch_reuse_map_png_created(local_tmp_path: Path) -> None:
    output_path = local_tmp_path / "batch_reuse_map.png"

    plot_batch_reuse_map(
        assignments=_reuse_map_assignments(),
        design_table=_reuse_map_design_table(),
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_batch_reuse_map_does_not_add_colorbar(monkeypatch: pytest.MonkeyPatch, local_tmp_path: Path) -> None:
    def fail_colorbar(self: Figure, *args: object, **kwargs: object) -> None:
        raise AssertionError("Batch Reuse Map should not add a continuous colorbar")

    monkeypatch.setattr(Figure, "colorbar", fail_colorbar)
    output_path = local_tmp_path / "batch_reuse_map.png"

    plot_batch_reuse_map(
        assignments=_reuse_map_assignments(),
        design_table=_reuse_map_design_table(),
        config=build_example_run_config(),
        output_path=output_path,
    )

    assert output_path.exists()


def test_batch_reuse_map_legend_is_anchored_beyond_secondary_axis(
    monkeypatch: pytest.MonkeyPatch,
    local_tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    original_legend = Axes.legend

    def capture_legend(self: Axes, *args: object, **kwargs: object) -> object:
        captured["bbox_to_anchor"] = kwargs.get("bbox_to_anchor")
        captured["fontsize"] = kwargs.get("fontsize")
        return original_legend(self, *args, **kwargs)

    monkeypatch.setattr(Axes, "legend", capture_legend)
    output_path = local_tmp_path / "batch_reuse_map.png"

    plot_batch_reuse_map(
        assignments=_reuse_map_assignments(),
        design_table=_reuse_map_design_table(),
        config=build_example_run_config(),
        output_path=output_path,
    )

    assert captured["bbox_to_anchor"][0] >= 1.45  # type: ignore[index]
    assert captured["fontsize"] == 8
    assert output_path.exists()
