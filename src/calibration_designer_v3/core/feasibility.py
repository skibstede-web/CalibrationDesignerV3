"""Candidate feasibility checks."""

from __future__ import annotations

from calibration_designer_v3.models.domain import ComponentConstraint


def is_feasible_candidate(
    candidate_component_mg_g: dict[str, float],
    constraint_map: dict[str, ComponentConstraint],
    api_ds_total_mg_g: float,
    balance_mg_g: float,
    tolerance_mg_g: float = 1e-6,
) -> bool:
    if balance_mg_g < -tolerance_mg_g:
        return False

    for component_name, constraint in constraint_map.items():
        if component_name not in candidate_component_mg_g:
            return False
        value = float(candidate_component_mg_g[component_name])
        if value < (constraint.min_mg_g - tolerance_mg_g):
            return False
        if value > (constraint.max_mg_g + tolerance_mg_g):
            return False

    total = float(sum(candidate_component_mg_g.values())) + float(api_ds_total_mg_g)
    if abs(total - 1000.0) > tolerance_mg_g:
        return False

    return True