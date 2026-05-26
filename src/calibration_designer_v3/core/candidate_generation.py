"""Guided deterministic feasible candidate generation."""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd

from calibration_designer_v3.core.composition import (
    calculate_api_ds_total,
    calculate_api_impurity,
    calculate_balance,
)
from calibration_designer_v3.core.feasibility import is_feasible_candidate
from calibration_designer_v3.core.guided_workflow import (
    component_variation_fraction,
    generate_api_levels_for_strength,
)
from calibration_designer_v3.models.domain import RunConfig


def _deterministic_thin(df: pd.DataFrame, max_candidates: int) -> pd.DataFrame:
    if len(df) <= max_candidates:
        return df
    idx = np.linspace(0, len(df) - 1, max_candidates, dtype=int)
    return df.iloc[idx].reset_index(drop=True)


def _component_levels(
    *,
    nominal: float,
    variation_fraction: float,
    component_min: float,
    component_max: float,
) -> list[float]:
    if variation_fraction <= 0:
        return [float(min(max(nominal, component_min), component_max))]

    lower = max(component_min, nominal * (1.0 - variation_fraction))
    upper = min(component_max, nominal * (1.0 + variation_fraction))
    values = [lower, nominal, upper]
    return sorted({round(float(v), 8) for v in values})


def calculate_raw_grid_combinations(config: RunConfig) -> int:
    constraint_map = config.constraint_map()
    balance_name = config.balance_component_name
    total = 0
    for strength in config.product_strengths:
        api_target = float(strength.component_targets_mg_g.get(config.api_component_name, 0.0))
        api_levels = generate_api_levels_for_strength(
            target_api_pure_mg_g=api_target,
            settings=config.api_calibration_range_settings,
        )
        level_counts = [len(api_levels)]

        for component in config.components:
            if component.is_api or component.name == balance_name:
                continue
            nominal = float(strength.component_targets_mg_g.get(component.name, 0.0))
            constraint = constraint_map[component.name]
            frac = component_variation_fraction(
                component_name=component.name,
                component_type=component.component_type,
                settings=config.excipient_variation_settings,
            )
            levels = _component_levels(
                nominal=nominal,
                variation_fraction=frac,
                component_min=float(constraint.min_mg_g),
                component_max=float(constraint.max_mg_g),
            )
            level_counts.append(len(levels))

        total += int(math.prod(level_counts))
    return total


def generate_candidate_compositions_with_stats(
    config: RunConfig,
    max_candidates: int | None = None,
) -> tuple[pd.DataFrame, int]:
    df = generate_candidate_compositions(config=config, max_candidates=max_candidates)
    raw_combinations = calculate_raw_grid_combinations(config=config)
    return df, raw_combinations


def generate_candidate_compositions(
    config: RunConfig,
    max_candidates: int | None = None,
) -> pd.DataFrame:
    api_name = config.api_component_name
    balance_name = config.balance_component_name
    constraint_map = config.constraint_map()

    candidate_rows: list[dict[str, float | str]] = []

    for strength in config.product_strengths:
        if api_name not in strength.component_targets_mg_g:
            raise ValueError(f"Strength '{strength.name}' missing API target for component '{api_name}'")

        api_levels = generate_api_levels_for_strength(
            target_api_pure_mg_g=float(strength.component_targets_mg_g[api_name]),
            settings=config.api_calibration_range_settings,
        )

        non_balance_components = [
            component for component in config.components if not component.is_api and component.name != balance_name
        ]
        component_level_map: dict[str, list[float]] = {}
        ordered_component_names = sorted(component.name for component in non_balance_components)
        for component_name in ordered_component_names:
            component = next(comp for comp in non_balance_components if comp.name == component_name)
            nominal = float(strength.component_targets_mg_g.get(component_name, 0.0))
            constraint = constraint_map[component_name]
            variation_fraction = component_variation_fraction(
                component_name=component_name,
                component_type=component.component_type,
                settings=config.excipient_variation_settings,
            )
            levels = _component_levels(
                nominal=nominal,
                variation_fraction=variation_fraction,
                component_min=float(constraint.min_mg_g),
                component_max=float(constraint.max_mg_g),
            )
            component_level_map[component_name] = levels

        level_vectors = [component_level_map[name] for name in ordered_component_names]

        for api_pure in api_levels:
            api_ds_total = calculate_api_ds_total(api_pure_mg_g=api_pure, api_content_mg_mg=config.api_content_mg_mg)
            api_impurity = calculate_api_impurity(api_pure_mg_g=api_pure, api_content_mg_mg=config.api_content_mg_mg)
            for excipient_values in itertools.product(*level_vectors):
                excipient_map = {
                    name: float(value) for name, value in zip(ordered_component_names, excipient_values, strict=True)
                }
                balance_mg_g = calculate_balance(
                    api_ds_total_mg_g=api_ds_total,
                    non_api_non_balance_components_mg_g=excipient_map,
                )
                candidate_component_mg_g = dict(excipient_map)
                candidate_component_mg_g[balance_name] = float(balance_mg_g)

                if not is_feasible_candidate(
                    candidate_component_mg_g=candidate_component_mg_g,
                    constraint_map={name: constraint_map[name] for name in ordered_component_names + [balance_name]},
                    api_ds_total_mg_g=api_ds_total,
                    balance_mg_g=balance_mg_g,
                    tolerance_mg_g=config.tolerance_mg_g,
                ):
                    continue

                if any(value < -config.tolerance_mg_g for value in candidate_component_mg_g.values()):
                    continue

                row: dict[str, float | str] = {
                    "source_strength_name": strength.name,
                    "auto_balance_component": balance_name,
                    "api_pure_mg_g": float(api_pure),
                    "api_content_mg_mg": float(config.api_content_mg_mg),
                    "api_ds_total_mg_g": float(api_ds_total),
                    "api_impurity_mg_g": float(api_impurity),
                    "balance_mg_g": float(balance_mg_g),
                    "sum_weighed_components_mg_g": float(api_ds_total + sum(excipient_map.values()) + balance_mg_g),
                    f"{balance_name}_mg_g": float(balance_mg_g),
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
