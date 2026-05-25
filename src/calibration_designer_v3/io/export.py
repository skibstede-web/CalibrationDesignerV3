"""Export utilities for complete design-run outputs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from calibration_designer_v3.core.composition import calculate_component_masses
from calibration_designer_v3.core.pipeline import PipelineResult
from calibration_designer_v3.models.domain import CalibrationBatch, RunConfig, WarningEntry
from calibration_designer_v3.plotting.plots import (
    plot_api_range_coverage,
    plot_api_vs_each_excipient,
    plot_batch_reuse_map,
    plot_component_correlation_heatmap,
    plot_material_consumption,
)


REQUIRED_CSVS = [
    "calibration_design_table.csv",
    "batch_weighing_sheet.csv",
    "model_assignment_table.csv",
    "correlation_matrix.csv",
    "design_diagnostics_summary.csv",
    "material_consumption_summary.csv",
    "warnings.csv",
]

REQUIRED_PNGS = [
    "api_range_coverage.png",
    "api_vs_each_excipient.png",
    "component_correlation_heatmap.png",
    "material_consumption.png",
    "batch_reuse_map.png",
]


def _build_design_table(batches: list[CalibrationBatch]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for batch in batches:
        row: dict[str, object] = {
            "batch_id": batch.batch_id,
            "batch_name": batch.batch_name,
            "batch_role": batch.batch_role,
            "source": batch.source,
            "locked": batch.locked,
            "forced": batch.forced,
            "derived_batch": batch.derived_batch,
            "parent_batch_a": batch.parent_batch_a,
            "parent_batch_b": batch.parent_batch_b,
            "fraction_from_a": batch.fraction_from_a,
            "assigned_strength_models": "|".join(batch.assigned_strength_models),
            "preparation_route": batch.preparation_route,
            "batch_size_kg": batch.batch_size_kg,
            "api_pure_mg_g": batch.api_pure_mg_g,
            "api_content_mg_mg": batch.api_content_mg_mg,
            "api_ds_total_mg_g": batch.api_ds_total_mg_g,
            "api_impurity_mg_g": batch.api_impurity_mg_g,
            "balance_mg_g": batch.balance_mg_g,
            "sum_weighed_components_mg_g": batch.sum_weighed_components_mg_g,
        }
        for component_name, value in batch.component_mg_g.items():
            row[f"{component_name}_mg_g"] = value
        rows.append(row)

    return pd.DataFrame(rows)


def _build_weighing_sheet(batches: list[CalibrationBatch], api_component_name: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for batch in batches:
        mass_input = dict(batch.component_mg_g)
        mass_input[api_component_name] = batch.api_ds_total_mg_g
        masses = calculate_component_masses(component_mg_g=mass_input, batch_size_kg=batch.batch_size_kg)

        for component_name, mass_data in masses.items():
            if component_name == api_component_name:
                component_type = "API_DS"
                concentration = batch.api_ds_total_mg_g
            elif component_name.lower() == "balance":
                component_type = "BALANCE"
                concentration = batch.balance_mg_g
            else:
                component_type = "EXCIPIENT"
                concentration = batch.component_mg_g.get(component_name, 0.0)

            rows.append(
                {
                    "batch_id": batch.batch_id,
                    "batch_size_kg": batch.batch_size_kg,
                    "component_name": component_name,
                    "component_type": component_type,
                    "component_concentration_mg_g": concentration,
                    "component_mass_g": mass_data["component_mass_g"],
                    "component_mass_kg": mass_data["component_mass_kg"],
                    "weighing_basis": "actual_weighed_material",
                    "api_content_mg_mg": batch.api_content_mg_mg,
                }
            )

    return pd.DataFrame(rows)


def _build_material_consumption_summary(
    design_table: pd.DataFrame,
    weighing_sheet: pd.DataFrame,
    api_component_name: str,
) -> pd.DataFrame:
    grouped = (
        weighing_sheet.groupby("component_name", as_index=False)[["component_mass_g", "component_mass_kg"]]
        .sum()
        .rename(columns={"component_name": "component", "component_mass_g": "total_mass_g", "component_mass_kg": "total_mass_kg"})
    )

    api_pure_total_g = float((design_table["api_pure_mg_g"] * design_table["batch_size_kg"]).sum())
    api_ds_total_g = float((design_table["api_ds_total_mg_g"] * design_table["batch_size_kg"]).sum())
    api_impurity_total_g = float((design_table["api_impurity_mg_g"] * design_table["batch_size_kg"]).sum())

    extras = pd.DataFrame(
        [
            {
                "component": "API pure equivalent",
                "total_mass_g": api_pure_total_g,
                "total_mass_kg": api_pure_total_g / 1000.0,
            },
            {
                "component": "API drug substance weighed",
                "total_mass_g": api_ds_total_g,
                "total_mass_kg": api_ds_total_g / 1000.0,
            },
            {
                "component": "API impurity/material fraction",
                "total_mass_g": api_impurity_total_g,
                "total_mass_kg": api_impurity_total_g / 1000.0,
            },
        ]
    )

    return pd.concat([grouped, extras], ignore_index=True)


def _warnings_to_frame(warnings: list[WarningEntry]) -> pd.DataFrame:
    if not warnings:
        return pd.DataFrame(
            [
                {
                    "severity": "PASS",
                    "code": "NO_WARNINGS",
                    "message": "No warnings generated.",
                    "affected_batch_id": "",
                    "suggested_action": "",
                }
            ]
        )
    return pd.DataFrame([warning.model_dump() for warning in warnings])


def _make_run_folder(output_root: Path, timestamp: str | None = None) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = output_root / f"design_run_{ts}"
    counter = 1
    while run_folder.exists():
        run_folder = output_root / f"design_run_{ts}_{counter:02d}"
        counter += 1
    run_folder.mkdir(parents=True, exist_ok=False)
    return run_folder


def export_design_run(
    config: RunConfig,
    pipeline_result: PipelineResult,
    output_root: str | Path = "outputs",
    timestamp: str | None = None,
) -> Path:
    run_folder = _make_run_folder(Path(output_root), timestamp=timestamp)

    design_table = _build_design_table(pipeline_result.design.batches)
    weighing_sheet = _build_weighing_sheet(
        batches=pipeline_result.design.batches,
        api_component_name=config.api_component_name,
    )
    assignments = pipeline_result.assignments.copy()
    diagnostics_summary = pipeline_result.diagnostics.summary.copy()
    correlation_matrix = pipeline_result.diagnostics.correlation_matrix.copy()
    warnings_df = _warnings_to_frame(pipeline_result.warnings)
    material_summary = _build_material_consumption_summary(
        design_table=design_table,
        weighing_sheet=weighing_sheet,
        api_component_name=config.api_component_name,
    )

    design_table.to_csv(run_folder / "calibration_design_table.csv", index=False)
    weighing_sheet.to_csv(run_folder / "batch_weighing_sheet.csv", index=False)
    assignments.to_csv(run_folder / "model_assignment_table.csv", index=False)
    correlation_matrix.to_csv(run_folder / "correlation_matrix.csv", index=True)
    diagnostics_summary.to_csv(run_folder / "design_diagnostics_summary.csv", index=False)
    material_summary.to_csv(run_folder / "material_consumption_summary.csv", index=False)
    warnings_df.to_csv(run_folder / "warnings.csv", index=False)

    plot_api_range_coverage(design_table=design_table, output_path=run_folder / "api_range_coverage.png")
    plot_api_vs_each_excipient(design_table=design_table, output_path=run_folder / "api_vs_each_excipient.png")
    plot_component_correlation_heatmap(
        correlation_matrix=correlation_matrix,
        output_path=run_folder / "component_correlation_heatmap.png",
    )
    plot_material_consumption(material_consumption=material_summary, output_path=run_folder / "material_consumption.png")
    plot_batch_reuse_map(assignments=assignments, output_path=run_folder / "batch_reuse_map.png")

    run_configuration = config.model_dump()
    run_configuration["exported_at"] = datetime.now().isoformat(timespec="seconds")
    run_configuration["seed"] = config.seed
    with open(run_folder / "run_configuration.json", "w", encoding="utf-8") as f:
        json.dump(run_configuration, f, indent=2)

    return run_folder