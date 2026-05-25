"""Design diagnostics for correlation, VIF, and specificity."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from calibration_designer_v3.models.domain import CalibrationBatch, RunConfig, WarningEntry


@dataclass
class DiagnosticsResult:
    correlation_matrix: pd.DataFrame
    api_vs_component: pd.DataFrame
    summary: pd.DataFrame
    warnings: list[WarningEntry]


def _batches_to_frame(batches: list[CalibrationBatch]) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for batch in batches:
        row: dict[str, float] = {
            "api_pure_mg_g": float(batch.api_pure_mg_g),
            "balance_mg_g": float(batch.balance_mg_g),
        }
        for component_name, amount in batch.component_mg_g.items():
            row[f"{component_name}_mg_g"] = float(amount)
        rows.append(row)
    return pd.DataFrame(rows)


def _api_vif(df: pd.DataFrame, feature_cols: list[str]) -> float:
    if not feature_cols or len(df) < 3:
        return float("nan")

    x = df[feature_cols].to_numpy(dtype=float)
    y = df["api_pure_mg_g"].to_numpy(dtype=float)

    # Handle all-constant predictor matrix gracefully.
    if np.all(np.std(x, axis=0) < 1e-12):
        return float("nan")

    x_design = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(x_design, y, rcond=None)
    y_hat = x_design @ beta
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot <= 1e-12:
        return float("nan")
    r2 = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot)))
    if r2 >= 0.999999:
        return float("inf")
    return 1.0 / (1.0 - r2)


def _severity_for_correlation(abs_corr: float) -> str:
    if abs_corr > 0.90:
        return "CRITICAL"
    if abs_corr > 0.80:
        return "WARNING"
    return "PASS"


def _severity_for_vif(vif: float) -> str:
    if np.isinf(vif) or vif > 10.0:
        return "CRITICAL"
    if vif > 5.0:
        return "WARNING"
    return "PASS"


def calculate_diagnostics(batches: list[CalibrationBatch], config: RunConfig) -> DiagnosticsResult:
    if not batches:
        empty = pd.DataFrame()
        return DiagnosticsResult(correlation_matrix=empty, api_vs_component=empty, summary=empty, warnings=[])

    df = _batches_to_frame(batches)

    excipient_cols = []
    for component in config.components:
        if component.is_api or component.is_balance:
            continue
        col = f"{component.name}_mg_g"
        if col in df.columns:
            excipient_cols.append(col)

    matrix_cols = ["api_pure_mg_g", *excipient_cols, "balance_mg_g"]
    matrix_cols = [c for c in matrix_cols if c in df.columns]

    correlation_matrix = df[matrix_cols].corr(method="pearson") if matrix_cols else pd.DataFrame()

    api_vs_rows: list[dict[str, float | str]] = []
    warnings: list[WarningEntry] = []

    max_abs_corr = 0.0
    for col in excipient_cols:
        if df["api_pure_mg_g"].nunique() <= 1 or df[col].nunique() <= 1:
            corr = float("nan")
            abs_corr = float("nan")
            severity = "INFO"
        else:
            corr = float(df["api_pure_mg_g"].corr(df[col]))
            abs_corr = abs(corr)
            max_abs_corr = max(max_abs_corr, abs_corr)
            severity = _severity_for_correlation(abs_corr)
            if severity in {"WARNING", "CRITICAL"}:
                warnings.append(
                    WarningEntry(
                        severity=severity,
                        code="API_EXCIPIENT_CORRELATION",
                        message=f"High API correlation with {col}: {corr:.3f}",
                        suggested_action="Increase orthogonality of API and excipient levels.",
                    )
                )

        api_vs_rows.append(
            {
                "component": col,
                "correlation": corr,
                "abs_correlation": abs_corr,
                "status": severity,
            }
        )

    api_vif = _api_vif(df=df, feature_cols=excipient_cols)
    vif_status = _severity_for_vif(api_vif) if not np.isnan(api_vif) else "INFO"
    if vif_status in {"WARNING", "CRITICAL"}:
        warnings.append(
            WarningEntry(
                severity=vif_status,
                code="API_VIF_HIGH",
                message=f"API VIF is high: {api_vif:.3f}" if np.isfinite(api_vif) else "API VIF is infinite.",
                suggested_action="Adjust candidate selection to reduce API predictability from excipients.",
            )
        )

    unique_api_levels = float(df["api_pure_mg_g"].nunique())
    unique_excipient_levels = float(sum(df[c].nunique() for c in excipient_cols))
    api_range = float(df["api_pure_mg_g"].max() - df["api_pure_mg_g"].min())

    summary_rows = [
        {
            "metric": "batch_count",
            "value": float(len(df)),
            "threshold": ">= 1",
            "status": "PASS",
            "interpretation": "Number of selected calibration batches.",
        },
        {
            "metric": "api_unique_levels",
            "value": unique_api_levels,
            "threshold": ">= 2 recommended",
            "status": "PASS" if unique_api_levels >= 2 else "WARNING",
            "interpretation": "Number of unique API levels in final design.",
        },
        {
            "metric": "non_api_unique_levels_total",
            "value": unique_excipient_levels,
            "threshold": ">= number_of_excipients",
            "status": "PASS" if unique_excipient_levels >= len(excipient_cols) else "WARNING",
            "interpretation": "Total unique levels across non-API non-balance components.",
        },
        {
            "metric": "api_range_mg_g",
            "value": api_range,
            "threshold": "> 0",
            "status": "PASS" if api_range > 0 else "WARNING",
            "interpretation": "API concentration range in mg/g.",
        },
        {
            "metric": "max_abs_api_excipient_correlation",
            "value": max_abs_corr,
            "threshold": "<= 0.80",
            "status": _severity_for_correlation(max_abs_corr),
            "interpretation": "Maximum absolute API-excipient correlation.",
        },
        {
            "metric": "api_vif_excluding_balance",
            "value": api_vif,
            "threshold": "<= 5",
            "status": vif_status,
            "interpretation": "API VIF from non-API non-balance components.",
        },
    ]

    # Optional named diagnostics when names are present.
    for special in ("SNAC", "Niacinamide"):
        match_col = next((c for c in excipient_cols if c.lower() == f"{special.lower()}_mg_g"), None)
        if match_col and not pd.isna(df["api_pure_mg_g"].corr(df[match_col])):
            summary_rows.append(
                {
                    "metric": f"api_vs_{special.lower()}_correlation",
                    "value": float(df["api_pure_mg_g"].corr(df[match_col])),
                    "threshold": "informative",
                    "status": "INFO",
                    "interpretation": f"API correlation with {special}.",
                }
            )

    return DiagnosticsResult(
        correlation_matrix=correlation_matrix,
        api_vs_component=pd.DataFrame(api_vs_rows),
        summary=pd.DataFrame(summary_rows),
        warnings=warnings,
    )
