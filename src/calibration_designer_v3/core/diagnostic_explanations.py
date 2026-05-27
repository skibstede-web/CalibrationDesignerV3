"""Human-readable explanations for diagnostics summary metrics."""

from __future__ import annotations

import re

import pandas as pd

_FALLBACK_EXPLANATION = (
    "Diagnostic metric calculated by the app. Review the value together with the status and warnings."
)

_METRIC_EXPLANATIONS: dict[str, str] = {
    "api_snac_correlation": (
        "Correlation between pure API concentration and SNAC concentration across selected calibration batches. "
        "High absolute values suggest the model may use SNAC as a surrogate for API. Lower absolute values are preferred."
    ),
    "api_vs_snac_correlation": (
        "Correlation between pure API concentration and SNAC concentration across selected calibration batches. "
        "High absolute values suggest the model may use SNAC as a surrogate for API. Lower absolute values are preferred."
    ),
    "api_niacinamide_correlation": (
        "Correlation between pure API concentration and niacinamide concentration. High absolute values indicate "
        "possible confounding between API and niacinamide. Lower absolute values support better API specificity."
    ),
    "api_vs_niacinamide_correlation": (
        "Correlation between pure API concentration and niacinamide concentration. High absolute values indicate "
        "possible confounding between API and niacinamide. Lower absolute values support better API specificity."
    ),
    "api_vif_excluding_balance": (
        "VIF means Variance Inflation Factor. It indicates how well API can be predicted from the other "
        "non-balance components. High VIF means API is not sufficiently independent in the design. Lower values are preferred."
    ),
    "candidate_count": (
        "Number of raw candidate compositions generated before feasibility filtering or final selection. "
        "A very low number may indicate that the design settings are too restrictive."
    ),
    "raw_grid_combinations": (
        "Number of raw candidate compositions generated before feasibility filtering or final selection. "
        "A very low number may indicate that the design settings are too restrictive."
    ),
    "feasible_candidate_count": (
        "Number of candidate compositions that satisfy formulation constraints and sum to 1000 mg/g after API content correction "
        "and balance calculation. This should be higher than the desired number of batches."
    ),
    "feasible_candidates_after_balance": (
        "Number of candidate compositions that satisfy formulation constraints and sum to 1000 mg/g after API content correction "
        "and balance calculation. This should be higher than the desired number of batches."
    ),
    "selected_batch_count": (
        "Number of calibration batches selected for the final design. This should normally be close to the desired "
        "number of batches and at least the minimum number requested."
    ),
    "selected_calibration_batches": (
        "Number of calibration batches selected for the final design. This should normally be close to the desired "
        "number of batches and at least the minimum number requested."
    ),
    "batch_count": (
        "Number of calibration batches selected for the final design. This should normally be close to the desired "
        "number of batches and at least the minimum number requested."
    ),
    "balance_component": (
        "The component calculated to make the formulation sum to 1000 mg/g. This should normally be a major excipient, "
        "not API or a low-level glidant/lubricant."
    ),
    "selected_balance_component": (
        "The component calculated to make the formulation sum to 1000 mg/g. This should normally be a major excipient, "
        "not API or a low-level glidant/lubricant."
    ),
    "max_api_excipient_correlation": (
        "Maximum absolute correlation between API and any non-API component. High values indicate risk that the calibration "
        "model may learn excipient variation instead of API-specific spectral variation."
    ),
    "max_abs_api_excipient_correlation": (
        "Maximum absolute correlation between API and any non-API component. High values indicate risk that the calibration "
        "model may learn excipient variation instead of API-specific spectral variation."
    ),
    "unique_api_levels": (
        "Number of distinct pure API concentration levels represented in the selected design. More levels generally improve "
        "API range coverage and calibration stability."
    ),
    "api_unique_levels": (
        "Number of distinct pure API concentration levels represented in the selected design. More levels generally improve "
        "API range coverage and calibration stability."
    ),
    "target_strengths_included": (
        "Indicates whether exact target-strength compositions were included in the calibration design. Target points may be useful "
        "as anchors, but they are not always statistically required."
    ),
    "target_strength_points_in_design": (
        "Indicates how many exact target-strength compositions were included in the calibration design. Target points may be useful "
        "as anchors, but they are not always statistically required."
    ),
    "non_api_unique_levels_total": (
        "Total count of unique levels across non-API non-balance components. Higher diversity usually improves orthogonality "
        "and robustness of the calibration design."
    ),
    "api_range_mg_g": (
        "Range of pure API concentrations covered in the selected design. Wider and well-populated ranges generally improve "
        "calibration stability for low-dose methods."
    ),
    "pairwise_plot_count": (
        "Number of pairwise component scatter plots generated for visual review of composition spread and clustering."
    ),
}


def explanation_for_metric(metric: str) -> str:
    if metric in _METRIC_EXPLANATIONS:
        return _METRIC_EXPLANATIONS[metric]

    match = re.fullmatch(r"api_vs_(.+)_correlation", metric)
    if match:
        component = match.group(1).replace("_", " ")
        return (
            f"Correlation between pure API concentration and {component} concentration across selected calibration batches. "
            "High absolute values indicate possible confounding. Lower absolute values are preferred."
        )

    return _FALLBACK_EXPLANATION


def with_diagnostic_explanations(summary: pd.DataFrame) -> pd.DataFrame:
    """Return diagnostics summary with a stable explanation column."""
    if summary.empty:
        out = summary.copy()
        out = out.drop(columns=["interpretation"], errors="ignore")
        out["explanation"] = pd.Series(dtype="object")
        return out

    out = summary.copy()
    out = out.drop(columns=["interpretation"], errors="ignore")
    metric_series = out.get("metric", pd.Series([""] * len(out))).astype(str)
    out["explanation"] = metric_series.map(explanation_for_metric)
    return out
