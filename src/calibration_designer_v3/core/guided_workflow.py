"""Guided workflow helpers for API-driven calibration design."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from calibration_designer_v3.models.domain import (
    ApiCalibrationRangeSettings,
    ComponentSpec,
    ExcipientVariationSettings,
    ProductStrength,
)


def auto_select_balance_component(
    *,
    components: list[ComponentSpec],
    strength: ProductStrength,
    allow_variation_by_component: dict[str, bool],
    keep_glidant_lubricant_fixed: bool,
    manual_override: str | None = None,
) -> str:
    component_names = {component.name for component in components}
    if manual_override:
        if manual_override not in component_names:
            raise ValueError(f"Manual balance component override '{manual_override}' is not a known component")
        chosen = next(component for component in components if component.name == manual_override)
        if chosen.is_api:
            raise ValueError("Manual balance component override cannot be API")
        return chosen.name

    candidates = [component for component in components if not component.is_api]
    if not candidates:
        raise ValueError("No non-API component available for auto-selected balance")

    non_glidants = [
        component
        for component in candidates
        if component.component_type != "glidant_lubricant" or not keep_glidant_lubricant_fixed
    ]
    if non_glidants:
        candidates = non_glidants

    major = [component for component in candidates if component.component_type == "major_excipient"]
    if major:
        candidates = major

    preferred_flexible = [
        component for component in candidates if allow_variation_by_component.get(component.name, True)
    ]
    if preferred_flexible:
        candidates = preferred_flexible

    def nominal_value(component: ComponentSpec) -> float:
        return float(strength.component_targets_mg_g.get(component.name, 0.0))

    chosen = max(candidates, key=lambda component: (nominal_value(component), component.name))
    return chosen.name


def generate_api_levels_for_strength(
    *,
    target_api_pure_mg_g: float,
    settings: ApiCalibrationRangeSettings,
) -> list[float]:
    if settings.mode == "percent_of_target":
        lower_value = target_api_pure_mg_g * (settings.lower / 100.0)
        upper_value = target_api_pure_mg_g * (settings.upper / 100.0)
    else:
        lower_value = settings.lower
        upper_value = settings.upper

    levels = np.linspace(lower_value, upper_value, settings.api_levels).tolist()
    if settings.include_target_api_level:
        levels.append(float(target_api_pure_mg_g))

    return sorted({round(float(level), 8) for level in levels})


def component_variation_fraction(
    *,
    component_name: str,
    component_type: str,
    settings: ExcipientVariationSettings,
) -> float:
    if settings.keep_glidant_lubricant_fixed and component_type == "glidant_lubricant":
        return 0.0
    if not settings.allow_variation_by_component.get(component_name, component_type in {"major_excipient", "minor_excipient"}):
        return 0.0
    if settings.preset == "custom":
        pct = settings.custom_variation_pct_by_component.get(component_name, 0.0)
        return max(0.0, float(pct) / 100.0)
    return settings.preset_fraction()


def summarize_variation_components(
    *,
    components: list[ComponentSpec],
    settings: ExcipientVariationSettings,
) -> tuple[list[str], list[str]]:
    varied: list[str] = []
    fixed: list[str] = []
    for component in components:
        if component.is_api:
            continue
        fraction = component_variation_fraction(
            component_name=component.name,
            component_type=component.component_type,
            settings=settings,
        )
        if fraction > 0:
            varied.append(component.name)
        else:
            fixed.append(component.name)
    return varied, fixed


def default_allow_variation_map(components: list[ComponentSpec]) -> dict[str, bool]:
    mapping = defaultdict(bool)
    for component in components:
        if component.is_api:
            continue
        if component.component_type == "major_excipient":
            mapping[component.name] = True
        elif component.component_type == "minor_excipient":
            mapping[component.name] = True
        elif component.component_type == "glidant_lubricant":
            mapping[component.name] = False
        else:
            mapping[component.name] = True
    return dict(mapping)
