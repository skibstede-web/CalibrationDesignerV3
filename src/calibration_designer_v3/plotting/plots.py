"""Plot builders for exported design runs."""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from calibration_designer_v3.models.domain import RunConfig


PAIRWISE_DIRNAME = "pairwise"
PAIRWISE_MANIFEST_FILENAME = "pairwise_plot_manifest.csv"


def _sanitize_plot_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "var"


def build_pairwise_plot_variables(config: RunConfig, design_table: pd.DataFrame) -> list[tuple[str, str]]:
    variables: list[tuple[str, str]] = [("API_pure", "api_pure_mg_g")]
    for component in config.components:
        if component.is_api:
            continue
        col = f"{component.name}_mg_g"
        if col in design_table.columns:
            variables.append((component.name, col))
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

    role_target = df["batch_role"].astype(str).str.contains("target", case=False, na=False)
    source_target = df["source"].astype(str).str.contains("target", case=False, na=False)
    if "forced" in df.columns:
        forced_target = df["forced"].astype(bool)
    else:
        forced_target = pd.Series(False, index=df.index)
    explicit_target = df["is_target_strength"].astype(bool)
    combined = explicit_target | role_target | source_target | forced_target
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


def plot_api_vs_each_excipient(design_table: pd.DataFrame, output_path: Path) -> None:
    excipient_cols = [
        col for col in design_table.columns if col.endswith("_mg_g") and col not in {"api_pure_mg_g", "api_ds_total_mg_g", "api_impurity_mg_g", "balance_mg_g", "sum_weighed_components_mg_g"}
    ]

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for col in excipient_cols:
        ax.scatter(design_table["api_pure_mg_g"], design_table[col], label=col, alpha=0.85)
    ax.set_title("API vs Each Excipient")
    ax.set_xlabel("API pure (mg/g)")
    ax.set_ylabel("Excipient concentration (mg/g)")
    if excipient_cols:
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_component_correlation_heatmap(correlation_matrix: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    if correlation_matrix.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
    else:
        cax = ax.imshow(correlation_matrix.values, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(correlation_matrix.columns)))
        ax.set_yticks(range(len(correlation_matrix.index)))
        ax.set_xticklabels(correlation_matrix.columns, rotation=45, ha="right")
        ax.set_yticklabels(correlation_matrix.index)
        fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Component Correlation Heatmap")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_material_consumption(material_consumption: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(material_consumption))
    ax.bar(x, material_consumption["total_mass_g"])
    ax.set_title("Material Consumption")
    ax.set_ylabel("Total mass (g)")
    ax.set_xticks(x)
    ax.set_xticklabels(material_consumption["component"], rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_batch_reuse_map(assignments: pd.DataFrame, output_path: Path) -> None:
    if assignments.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No assignments", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    pivot = (
        assignments.assign(flag=1)
        .pivot_table(index="batch_id", columns="strength_model", values="flag", aggfunc="max", fill_value=0)
        .sort_index(axis=0)
        .sort_index(axis=1)
    )

    fig, ax = plt.subplots(figsize=(7, 4.5))
    cax = ax.imshow(pivot.values, cmap="Blues", vmin=0, vmax=1)
    ax.set_title("Batch Reuse Map")
    ax.set_xlabel("Strength model")
    ax.set_ylabel("Batch ID")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
