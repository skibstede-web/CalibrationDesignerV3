"""Core composition calculations."""

from __future__ import annotations

from collections.abc import Mapping


def calculate_api_ds_total(api_pure_mg_g: float, api_content_mg_mg: float) -> float:
    if api_content_mg_mg <= 0:
        raise ValueError("API content must be > 0")
    return float(api_pure_mg_g) / float(api_content_mg_mg)


def calculate_api_impurity(api_pure_mg_g: float, api_content_mg_mg: float) -> float:
    api_ds_total = calculate_api_ds_total(api_pure_mg_g=api_pure_mg_g, api_content_mg_mg=api_content_mg_mg)
    return api_ds_total - float(api_pure_mg_g)


def calculate_balance(api_ds_total_mg_g: float, non_api_non_balance_components_mg_g: Mapping[str, float]) -> float:
    return 1000.0 - float(api_ds_total_mg_g) - float(sum(non_api_non_balance_components_mg_g.values()))


def calculate_weighed_sum(
    api_ds_total_mg_g: float,
    non_api_non_balance_components_mg_g: Mapping[str, float],
    balance_mg_g: float,
) -> float:
    return float(api_ds_total_mg_g) + float(sum(non_api_non_balance_components_mg_g.values())) + float(balance_mg_g)


def calculate_component_masses(component_mg_g: Mapping[str, float], batch_size_kg: float) -> dict[str, dict[str, float]]:
    if batch_size_kg <= 0:
        raise ValueError("batch_size_kg must be > 0")

    masses: dict[str, dict[str, float]] = {}
    for component_name, concentration_mg_g in component_mg_g.items():
        mass_g = float(concentration_mg_g) * float(batch_size_kg)
        masses[component_name] = {
            "component_concentration_mg_g": float(concentration_mg_g),
            "component_mass_g": mass_g,
            "component_mass_kg": mass_g / 1000.0,
        }
    return masses