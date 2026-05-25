from __future__ import annotations

import math

from calibration_designer_v3.core.composition import (
    calculate_api_ds_total,
    calculate_api_impurity,
    calculate_balance,
    calculate_component_masses,
    calculate_weighed_sum,
)
from calibration_designer_v3.core.feasibility import is_feasible_candidate
from calibration_designer_v3.models.domain import ComponentConstraint


def test_api_content_correction() -> None:
    assert math.isclose(calculate_api_ds_total(api_pure_mg_g=10.0, api_content_mg_mg=0.8), 12.5)


def test_api_impurity_calculation() -> None:
    assert math.isclose(calculate_api_impurity(api_pure_mg_g=10.0, api_content_mg_mg=0.8), 2.5)


def test_balance_calculation_sums_to_1000() -> None:
    api_ds_total = 12.5
    others = {"Exc1": 100.0, "Exc2": 200.0}
    balance = calculate_balance(api_ds_total_mg_g=api_ds_total, non_api_non_balance_components_mg_g=others)
    total = calculate_weighed_sum(
        api_ds_total_mg_g=api_ds_total,
        non_api_non_balance_components_mg_g=others,
        balance_mg_g=balance,
    )
    assert math.isclose(total, 1000.0)


def test_negative_balance_is_infeasible() -> None:
    constraints = {
        "Exc1": ComponentConstraint(component_name="Exc1", min_mg_g=0.0, max_mg_g=900.0, preferred_levels=2),
        "Balance": ComponentConstraint(component_name="Balance", min_mg_g=100.0, max_mg_g=1000.0, preferred_levels=2),
    }
    candidate = {"Exc1": 950.0, "Balance": -10.0}
    assert not is_feasible_candidate(
        candidate_component_mg_g=candidate,
        constraint_map=constraints,
        api_ds_total_mg_g=60.0,
        balance_mg_g=-10.0,
    )


def test_component_outside_range_is_infeasible() -> None:
    constraints = {
        "Exc1": ComponentConstraint(component_name="Exc1", min_mg_g=10.0, max_mg_g=20.0, preferred_levels=2),
        "Balance": ComponentConstraint(component_name="Balance", min_mg_g=900.0, max_mg_g=990.0, preferred_levels=2),
    }
    candidate = {"Exc1": 30.0, "Balance": 950.0}
    assert not is_feasible_candidate(
        candidate_component_mg_g=candidate,
        constraint_map=constraints,
        api_ds_total_mg_g=20.0,
        balance_mg_g=950.0,
    )


def test_component_masses_for_known_batch_size() -> None:
    masses = calculate_component_masses(
        component_mg_g={"API_DS": 12.5, "Exc1": 100.0, "Balance": 887.5},
        batch_size_kg=10.0,
    )
    assert math.isclose(masses["API_DS"]["component_mass_g"], 125.0)
    assert math.isclose(masses["API_DS"]["component_mass_kg"], 0.125)