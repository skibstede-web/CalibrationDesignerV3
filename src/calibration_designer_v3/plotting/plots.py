"""Plot builders for exported design runs."""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from calibration_designer_v3.models.domain import RunConfig


PAIRWISE_DIRNAME = "pairwise"
PAIRWISE_MANIFEST_FILENAME = "pairwise_plot_manifest.csv"
BATCH_REUSE_EMPTY_COLOR = "#FFFFFF"
BATCH_REUSE_CALIBRATION_COLOR = "#1976D2"
BATCH_REUSE_TARGET_COLOR = "#2E7D32"
MATERIAL_CONSUMPTION_PLOT_EXCLUDED_COMPONENTS = {
    "API pure equivalent",
    "API drug substance weighed",
    "API impurity/material fraction",
}


def _sanitize_plot_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "var"


def _normalized_component_column(component_name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", component_name.strip().lower())
    token = re.sub(r"_+", "_", token).strip("_")
    return f"{token}_mg_g"


def build_component_label_map(config: RunConfig) -> dict[str, str]:
    """Map internal concentration columns to user-facing component names."""
    api_label = config.api_component_name
    label_map = {
        "api_pure_mg_g": api_label,
        "API_pure": api_label,
        "api_pure": api_label,
        "balance_mg_g": config.balance_component_name,
    }

    for component in config.components:
        if component.is_api:
            continue
        label_map[f"{component.name}_mg_g"] = component.name
        label_map[_normalized_component_column(component.name)] = component.name

    return label_map


def build_component_correlation_plot_matrix(
    correlation_matrix: pd.DataFrame,
    config: RunConfig,
) -> pd.DataFrame:
    """Return a correlation matrix labelled with user component names for plotting."""
    if correlation_matrix.empty:
        return correlation_matrix.copy()

    label_map = build_component_label_map(config)
    selected_columns: list[str] = []
    available = set(correlation_matrix.columns).intersection(set(correlation_matrix.index))

    for component in config.components:
        if component.is_api:
            candidates = ["api_pure_mg_g", "API_pure", "api_pure"]
        else:
            candidates = [f"{component.name}_mg_g", _normalized_component_column(component.name)]
            if component.is_balance:
                candidates.append("balance_mg_g")

        selected = next((candidate for candidate in candidates if candidate in available), None)
        if selected and selected not in selected_columns:
            selected_columns.append(selected)

    if not selected_columns:
        return pd.DataFrame()

    plot_matrix = correlation_matrix.loc[selected_columns, selected_columns].copy()
    labels = [label_map[column] for column in selected_columns]
    plot_matrix.index = labels
    plot_matrix.columns = labels
    return plot_matrix


def build_pairwise_plot_variables(config: RunConfig, design_table: pd.DataFrame) -> list[tuple[str, str]]:
    label_map = build_component_label_map(config)
    variables: list[tuple[str, str]] = [(label_map["api_pure_mg_g"], "api_pure_mg_g")]
    for component in config.components:
        if component.is_api:
            continue
        col = f"{component.name}_mg_g"
        if col in design_table.columns:
            variables.append((label_map.get(col, component.name), col))
    return variables


def annotate_target_strength_columns(
    *,
    design_table: pd.DataFrame,
    config: RunConfig,
    tolerance_mg_g: float,
) -> pd.DataFrame:
    df = design_table.copy()
    if "is_target_strength" not in df.columns:
        df["is_target_strength"] = False
    if "target_strength_name" not in df.columns:
        df["target_strength_name"] = ""

    role_target = df.get("batch_role", pd.Series("", index=df.index)).astype(str).str.contains(
        "target", case=False, na=False
    )
    source_target = df.get("source", pd.Series("", index=df.index)).astype(str).str.contains(
        "target", case=False, na=False
    )
    forced_target = df.get("forced", pd.Series(False, index=df.index)).astype(bool)
    target_name_present = df["target_strength_name"].fillna("").astype(str).str.strip().ne("")
    explicit_target = df["is_target_strength"].astype(bool)
    combined = explicit_target | role_target | source_target | forced_target | target_name_present
    df["is_target_strength"] = combined

    api_name = config.api_component_name
    non_api_names = [component.name for component in config.components if not component.is_api]

    for idx, row in df.iterrows():
        if bool(row["is_target_strength"]) and str(row.get("target_strength_name", "")).strip():
            continue

        matched_strength_name = ""
        for strength in config.product_strengths:
            matches = True
            target_api = float(strength.component_targets_mg_g.get(api_name, np.nan))
            if np.isnan(target_api) or abs(float(row["api_pure_mg_g"]) - target_api) > tolerance_mg_g:
                matches = False
            else:
                for name in non_api_names:
                    col = f"{name}_mg_g"
                    if col not in df.columns:
                        matches = False
                        break
                    target_value = float(strength.component_targets_mg_g.get(name, np.nan))
                    if np.isnan(target_value) or abs(float(row[col]) - target_value) > tolerance_mg_g:
                        matches = False
                        break
            if matches:
                matched_strength_name = strength.name
                break

        if matched_strength_name:
            df.at[idx, "is_target_strength"] = True
            if not str(row.get("target_strength_name", "")).strip():
                df.at[idx, "target_strength_name"] = matched_strength_name

    df["target_strength_name"] = df["target_strength_name"].fillna("").astype(str)
    return df


def create_pairwise_component_plots(
    *,
    config: RunConfig,
    design_table: pd.DataFrame,
    output_root: Path,
    tolerance_mg_g: float,
) -> pd.DataFrame:
    output_root.mkdir(parents=True, exist_ok=True)
    variables = build_pairwise_plot_variables(config=config, design_table=design_table)
    annotated = annotate_target_strength_columns(
        design_table=design_table,
        config=config,
        tolerance_mg_g=tolerance_mg_g,
    )

    manifest_rows: list[dict[str, Any]] = []
    for (x_label, x_col), (y_label, y_col) in itertools.combinations(variables, 2):
        fig, ax = plt.subplots(figsize=(7, 5))

        target_mask = annotated["is_target_strength"].astype(bool)
        normal = annotated[~target_mask]
        target = annotated[target_mask]

        if not normal.empty:
            ax.scatter(normal[x_col], normal[y_col], marker="o", alpha=0.85, label="Calibration batch")
        if not target.empty:
            ax.scatter(
                target[x_col],
                target[y_col],
                marker="*",
                s=160,
                edgecolors="black",
                linewidths=0.8,
                alpha=0.95,
                label="Target-strength batch",
            )

        for _, row in annotated.iterrows():
            batch_id = str(row.get("batch_id", ""))
            if not batch_id:
                continue
            ax.annotate(
                batch_id,
                xy=(float(row[x_col]), float(row[y_col])),
                xytext=(4, 3),
                textcoords="offset points",
                fontsize=8,
            )

        ax.set_title(f"{x_label} vs {y_label}")
        ax.set_xlabel(f"{x_label} (mg/g)")
        ax.set_ylabel(f"{y_label} (mg/g)")
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0)

        filename = f"pairwise_{_sanitize_plot_token(x_label)}_vs_{_sanitize_plot_token(y_label)}.png"
        output_path = output_root / filename
        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        manifest_rows.append(
            {
                "plot_file": filename,
                "x_variable": x_label,
                "y_variable": y_label,
                "n_points": int(len(annotated)),
                "n_target_points": int(target_mask.sum()),
            }
        )

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(output_root / PAIRWISE_MANIFEST_FILENAME, index=False)
    return manifest


def plot_api_range_coverage(design_table: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(design_table))
    ax.plot(x, design_table["api_pure_mg_g"], marker="o", linestyle="-")
    ax.set_title("API Range Coverage")
    ax.set_xlabel("Batch index")
    ax.set_ylabel("API pure (mg/g)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_api_vs_each_excipient(
    design_table: pd.DataFrame,
    output_path: Path,
    config: RunConfig | None = None,
) -> None:
    excipient_cols = [
        col for col in design_table.columns if col.endswith("_mg_g") and col not in {"api_pure_mg_g", "api_ds_total_mg_g", "api_impurity_mg_g", "balance_mg_g", "sum_weighed_components_mg_g"}
    ]

    label_map = build_component_label_map(config) if config is not None else {}
    api_label = label_map.get("api_pure_mg_g", "API pure")

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for col in excipient_cols:
        ax.scatter(design_table["api_pure_mg_g"], design_table[col], label=label_map.get(col, col), alpha=0.85)
    ax.set_title("API vs Each Excipient")
    ax.set_xlabel(f"{api_label} (pure API, mg/g)")
    ax.set_ylabel("Excipient concentration (mg/g)")
    if excipient_cols:
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_component_correlation_heatmap(
    correlation_matrix: pd.DataFrame,
    output_path: Path,
    config: RunConfig | None = None,
) -> None:
    plot_matrix = (
        build_component_correlation_plot_matrix(correlation_matrix, config)
        if config is not None
        else correlation_matrix
    )

    fig, ax = plt.subplots(figsize=(6, 5))
    if plot_matrix.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
    else:
        cax = ax.imshow(plot_matrix.values, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(plot_matrix.columns)))
        ax.set_yticks(range(len(plot_matrix.index)))
        ax.set_xticklabels(plot_matrix.columns, rotation=45, ha="right")
        ax.set_yticklabels(plot_matrix.index)
        fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Component Correlation Heatmap")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def build_material_consumption_plot_data(material_consumption: pd.DataFrame) -> pd.DataFrame:
    """Return one plotted row per formulation component.

    The exported summary may include API detail rows. The component-level API row is the weighed
    API drug-substance mass because it is built from the weighing sheet.
    """
    if material_consumption.empty:
        return material_consumption.copy()

    required_columns = ["component", "total_mass_g"]
    missing = [column for column in required_columns if column not in material_consumption.columns]
    if missing:
        raise ValueError(f"Material consumption data is missing required columns: {', '.join(missing)}")

    plot_data = material_consumption.copy()
    plot_data["component"] = plot_data["component"].astype(str)
    plot_data = plot_data[~plot_data["component"].isin(MATERIAL_CONSUMPTION_PLOT_EXCLUDED_COMPONENTS)]
    return plot_data.reset_index(drop=True)


def plot_material_consumption(material_consumption: pd.DataFrame, output_path: Path) -> None:
    plot_data = build_material_consumption_plot_data(material_consumption)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    if plot_data.empty:
        ax.text(0.5, 0.5, "No material consumption data", ha="center", va="center")
        ax.set_axis_off()
    else:
        x = np.arange(len(plot_data))
        ax.bar(x, plot_data["total_mass_g"], color="#1976D2")
        ax.set_title("Material consumption by component")
        ax.set_ylabel("Total mass consumed (g)")
        ax.set_xticks(x)
        ax.set_xticklabels(plot_data["component"], rotation=45, ha="right")
        ax.text(
            0.0,
            -0.34,
            "Note: API bar shows API drug substance consumption.",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            color="#5F6C7B",
        )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _format_api_tick(value: float) -> str:
    if np.isfinite(value) and abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.1f}"


def _target_strength_mask_from_design_table(design_table: pd.DataFrame) -> pd.Series:
    explicit = (
        design_table.get("is_target_strength", pd.Series(False, index=design_table.index))
        .fillna(False)
        .astype(bool)
    )
    role_target = design_table.get("batch_role", pd.Series("", index=design_table.index)).astype(str).str.contains(
        "target", case=False, na=False
    )
    source_target = design_table.get("source", pd.Series("", index=design_table.index)).astype(str).str.contains(
        "target", case=False, na=False
    )
    forced_target = design_table.get("forced", pd.Series(False, index=design_table.index)).fillna(False).astype(bool)
    target_name_present = (
        design_table.get("target_strength_name", pd.Series("", index=design_table.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    )
    return explicit | role_target | source_target | forced_target | target_name_present


def build_batch_reuse_map_plot_data(
    assignments: pd.DataFrame,
    design_table: pd.DataFrame,
    config: RunConfig | None = None,
    tolerance_mg_g: float = 0.001,
) -> dict[str, object]:
    """Build sorted discrete reuse-map data for plotting."""
    if assignments.empty or design_table.empty:
        return {
            "matrix": np.zeros((0, 0), dtype=int),
            "batch_ids": [],
            "strength_models": [],
            "api_pure_mg_g": [],
            "is_target_strength": [],
        }

    if config is not None:
        design_table = annotate_target_strength_columns(
            design_table=design_table,
            config=config,
            tolerance_mg_g=tolerance_mg_g,
        )

    required_design_cols = {"batch_id", "api_pure_mg_g"}
    missing_design_cols = required_design_cols.difference(design_table.columns)
    if missing_design_cols:
        raise ValueError(f"design_table missing required columns for batch reuse map: {sorted(missing_design_cols)}")

    assignment_df = assignments.copy()
    if "included" in assignment_df.columns:
        assignment_df = assignment_df[assignment_df["included"].astype(bool)]

    if assignment_df.empty:
        strength_models: list[str] = []
    else:
        strength_models = sorted(assignment_df["strength_model"].astype(str).unique().tolist())

    batch_meta = design_table.copy()
    batch_meta["batch_id"] = batch_meta["batch_id"].astype(str)
    batch_meta["api_pure_mg_g"] = batch_meta["api_pure_mg_g"].astype(float)
    batch_meta["is_target_strength"] = _target_strength_mask_from_design_table(batch_meta)

    batch_meta = batch_meta.sort_values(["api_pure_mg_g", "batch_id"], ascending=[False, True]).reset_index(drop=True)
    batch_ids = batch_meta["batch_id"].tolist()
    batch_to_row = {batch_id: idx for idx, batch_id in enumerate(batch_ids)}
    strength_to_col = {strength: idx for idx, strength in enumerate(strength_models)}

    matrix = np.zeros((len(batch_ids), len(strength_models)), dtype=int)
    target_by_batch = dict(zip(batch_meta["batch_id"], batch_meta["is_target_strength"], strict=True))

    for _, row in assignment_df.iterrows():
        batch_id = str(row["batch_id"])
        strength_model = str(row["strength_model"])
        if batch_id not in batch_to_row or strength_model not in strength_to_col:
            continue
        matrix[batch_to_row[batch_id], strength_to_col[strength_model]] = 2 if target_by_batch.get(batch_id, False) else 1

    return {
        "matrix": matrix,
        "batch_ids": batch_ids,
        "strength_models": strength_models,
        "api_pure_mg_g": batch_meta["api_pure_mg_g"].tolist(),
        "is_target_strength": batch_meta["is_target_strength"].tolist(),
    }


def build_api_calibration_range_whiskers(config: RunConfig, strength_models: list[str]) -> list[dict[str, float | str]]:
    settings = config.api_calibration_range_settings
    strength_by_name = {strength.name: strength for strength in config.product_strengths}
    ranges: list[dict[str, float | str]] = []

    for strength_model in strength_models:
        strength = strength_by_name.get(strength_model)
        if strength is None:
            continue
        target_api = float(strength.component_targets_mg_g[config.api_component_name])
        if settings.mode == "percent_of_target":
            lower_api = target_api * (float(settings.lower) / 100.0)
            upper_api = target_api * (float(settings.upper) / 100.0)
        else:
            lower_api = float(settings.lower)
            upper_api = float(settings.upper)

        ranges.append(
            {
                "strength_model": strength_model,
                "lower_api_mg_g": min(lower_api, upper_api),
                "upper_api_mg_g": max(lower_api, upper_api),
            }
        )

    return ranges


def api_value_to_y_position(api_value: float, sorted_api_values_desc: list[float]) -> float:
    if not sorted_api_values_desc:
        return 0.0
    if len(sorted_api_values_desc) == 1:
        return 0.0

    y_positions = np.arange(len(sorted_api_values_desc), dtype=float)
    ascending_api = np.array(list(reversed(sorted_api_values_desc)), dtype=float)
    ascending_y = np.array(list(reversed(y_positions)), dtype=float)
    if np.allclose(ascending_api[0], ascending_api[-1]):
        return float(np.mean(y_positions))
    return float(np.interp(float(api_value), ascending_api, ascending_y, left=ascending_y[0], right=ascending_y[-1]))


def plot_batch_reuse_map(
    assignments: pd.DataFrame,
    output_path: Path,
    design_table: pd.DataFrame | None = None,
    config: RunConfig | None = None,
    tolerance_mg_g: float = 0.001,
) -> None:
    if assignments.empty or design_table is None or design_table.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No assignments", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    plot_data = build_batch_reuse_map_plot_data(
        assignments=assignments,
        design_table=design_table,
        config=config,
        tolerance_mg_g=tolerance_mg_g,
    )
    matrix = plot_data["matrix"]
    batch_ids = plot_data["batch_ids"]
    strength_models = plot_data["strength_models"]
    api_pure_values = plot_data["api_pure_mg_g"]
    if not isinstance(matrix, np.ndarray) or matrix.size == 0:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No assignments", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    fig, ax = plt.subplots(figsize=(7, 4.5))
    cmap = ListedColormap([BATCH_REUSE_EMPTY_COLOR, BATCH_REUSE_CALIBRATION_COLOR, BATCH_REUSE_TARGET_COLOR])
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)
    ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")
    ax.set_title("Batch Reuse Map")
    ax.set_xlabel("Strength model")
    ax.set_ylabel("Batch ID")
    ax.set_xticks(range(len(strength_models)))
    ax.set_xticklabels(strength_models, rotation=45, ha="right")
    y_positions = range(len(batch_ids))
    ax.set_yticks(y_positions)
    ax.set_yticklabels(batch_ids)

    right_ax = ax.twinx()
    right_ax.set_ylim(ax.get_ylim())
    right_ax.set_yticks(list(y_positions))
    right_ax.set_yticklabels([_format_api_tick(float(value)) for value in api_pure_values])
    right_ax.set_ylabel("Batch pure API (mg/g)")

    whisker_handle: Line2D | None = None
    if config is not None:
        cap_width = 0.16
        for api_range in build_api_calibration_range_whiskers(config=config, strength_models=list(strength_models)):
            strength_model = str(api_range["strength_model"])
            if strength_model not in strength_models:
                continue
            x = strength_models.index(strength_model)
            y_upper = api_value_to_y_position(float(api_range["upper_api_mg_g"]), list(api_pure_values))
            y_lower = api_value_to_y_position(float(api_range["lower_api_mg_g"]), list(api_pure_values))
            ax.vlines(x=x, ymin=y_upper, ymax=y_lower, colors="#333333", linewidth=1.2, alpha=0.8)
            ax.hlines(y=y_upper, xmin=x - cap_width, xmax=x + cap_width, colors="#333333", linewidth=1.2, alpha=0.8)
            ax.hlines(y=y_lower, xmin=x - cap_width, xmax=x + cap_width, colors="#333333", linewidth=1.2, alpha=0.8)
        whisker_handle = Line2D([0], [0], color="#333333", linewidth=1.2, label="API calibration range")

    legend_handles: list[object] = [
        Patch(facecolor=BATCH_REUSE_CALIBRATION_COLOR, edgecolor="black", label="Calibration batch"),
        Patch(facecolor=BATCH_REUSE_TARGET_COLOR, edgecolor="black", label="Target-strength batch"),
        Patch(facecolor=BATCH_REUSE_EMPTY_COLOR, edgecolor="black", label="Not assigned"),
    ]
    if whisker_handle is not None:
        legend_handles.append(whisker_handle)

    ax.legend(
        handles=legend_handles,
        loc="center left",
        bbox_to_anchor=(1.55, 0.5),
        borderaxespad=0.0,
        fontsize=8,
    )
    fig.subplots_adjust(left=0.16, right=0.56, bottom=0.24, top=0.88)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
