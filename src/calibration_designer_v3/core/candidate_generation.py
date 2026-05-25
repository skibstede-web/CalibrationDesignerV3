"""Deterministic feasible candidate generation."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from calibration_designer_v3.core.composition import (
    calculate_api_ds_total,
    calculate_api_impurity,
    calculate_balance,
)
from calibration_designer_v3.core.feasibility import is_feasible_candidate
from calibration_designer_v3.models.domain import ComponentConstraint, RunConfig


def _levels_from_constraint(constraint: ComponentConstraint) -> list[float]:
    if constraint.preferred_levels == 1:
        return [float(constraint.min_mg_g)]
    return np.linspace(constraint.min_mg_g, constraint.max_mg_g, constraint.preferred_levels).tolist()


def _deterministic_thin(df: pd.DataFrame, max_candidates: int) -> pd.DataFrame:
    if len(df) <= max_candidates:
        return df
    idx = np.linspace(0, len(df) - 1, max_candidates, dtype=int)
    return df.iloc[idx].reset_index(drop=True)


def generate_candidate_compositions(
    config: RunConfig,
    max_candidates: int | None = None,
) -> pd.DataFrame:
    api_name = config.api_component_name
    balance_name = config.balance_component_name
    constraint_map = config.constraint_map()

    api_constraint = constraint_map[api_name]

    non_api_non_balance_names = [
        component.name
        for component in config.components
        if not component.is_api and not component.is_balance
    ]

    api_levels = _levels_from_constraint(api_constraint)
    non_api_levels = {
        name: _levels_from_constraint(constraint_map[name]) for name in non_api_non_balance_names
    }

    non_api_constraints = {
        name: constraint_map[name] for name in non_api_non_balance_names + [balance_name]
    }

    candidate_rows: list[dict[str, float]] = []

    ordered_component_names = sorted(non_api_non_balance_names)
    ordered_level_vectors = [non_api_levels[name] for name in ordered_component_names]

    for api_pure in api_levels:
        api_ds_total = calculate_api_ds_total(
            api_pure_mg_g=api_pure,
            api_content_mg_mg=config.api_content_mg_mg,
        )
        api_impurity = calculate_api_impurity(
            api_pure_mg_g=api_pure,
            api_content_mg_mg=config.api_content_mg_mg,
        )

        for excipient_values in itertools.product(*ordered_level_vectors):
            excipient_map = {
                name: float(value)
                for name, value in zip(ordered_component_names, excipient_values, strict=True)
            }
            balance_mg_g = calculate_balance(
                api_ds_total_mg_g=api_ds_total,
                non_api_non_balance_components_mg_g=excipient_map,
            )

            candidate_component_mg_g = dict(excipient_map)
            candidate_component_mg_g[balance_name] = float(balance_mg_g)

            if not is_feasible_candidate(
                candidate_component_mg_g=candidate_component_mg_g,
                constraint_map=non_api_constraints,
                api_ds_total_mg_g=api_ds_total,
                balance_mg_g=balance_mg_g,
                tolerance_mg_g=config.tolerance_mg_g,
            ):
                continue

            row: dict[str, float] = {
                "api_pure_mg_g": float(api_pure),
                "api_content_mg_mg": float(config.api_content_mg_mg),
                "api_ds_total_mg_g": float(api_ds_total),
                "api_impurity_mg_g": float(api_impurity),
                "balance_mg_g": float(balance_mg_g),
                "sum_weighed_components_mg_g": float(api_ds_total + sum(excipient_map.values()) + balance_mg_g),
            }
            for name in ordered_component_names:
                row[f"{name}_mg_g"] = float(excipient_map[name])
            candidate_rows.append(row)

    if not candidate_rows:
        return pd.DataFrame()

    df = pd.DataFrame(candidate_rows)

    sort_columns = sorted(df.columns)
    df = df.sort_values(by=sort_columns).reset_index(drop=True)

    dedupe_cols = [col for col in df.columns if col.endswith("_mg_g") or col.startswith("api_")]
    df = (
        df.assign(_dedupe_key=df[dedupe_cols].round(8).astype(str).agg("|".join, axis=1))
        .drop_duplicates(subset=["_dedupe_key"])
        .drop(columns=["_dedupe_key"])
        .reset_index(drop=True)
    )

    if max_candidates is not None:
        df = _deterministic_thin(df=df, max_candidates=max_candidates)

    return df