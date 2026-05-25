"""Plot builders for exported design runs."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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
