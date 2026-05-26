from __future__ import annotations

import math

from calibration_designer_v3.core.candidate_generation import (
    calculate_raw_grid_combinations,
    generate_candidate_compositions,
)
from calibration_designer_v3.models.domain import (
    ApiCalibrationRangeSettings,
    BatchSettings,
    ComponentConstraint,
    ComponentSpec,
    ProductStrength,
    RunConfig,
)


def _config_basic() -> RunConfig:
    return RunConfig(
        components=[
            ComponentSpec(name="API", is_api=True),
            ComponentSpec(name="Exc1"),
            ComponentSpec(name="Balance", is_balance=True),
        ],
        api_content_mg_mg=1.0,
        product_strengths=[ProductStrength(name="S1", component_targets_mg_g={"API": 10.0, "Exc1": 150.0})],
        component_constraints=[
            ComponentConstraint(component_name="API", min_mg_g=10.0, max_mg_g=20.0, preferred_levels=2),
            ComponentConstraint(component_name="Exc1", min_mg_g=100.0, max_mg_g=200.0, preferred_levels=3),
            ComponentConstraint(component_name="Balance", min_mg_g=700.0, max_mg_g=900.0, preferred_levels=1),
        ],
        batch_settings=BatchSettings(desired_batches=4, min_batches=3, max_batches=10),
    )


def test_candidate_generation_returns_feasible_candidates() -> None:
    cfg = _config_basic()
    df = generate_candidate_compositions(cfg)
    assert not df.empty
    assert len(df) == calculate_raw_grid_combinations(cfg) == 15


def test_candidates_sum_to_1000() -> None:
    df = generate_candidate_compositions(_config_basic())
    assert all(math.isclose(v, 1000.0, abs_tol=1e-6) for v in df["sum_weighed_components_mg_g"])


def test_api_levels_use_pure_basis() -> None:
    df = generate_candidate_compositions(_config_basic())
    assert sorted(df["api_pure_mg_g"].unique().tolist()) == [6.0, 8.0, 10.0, 12.0, 14.0]


def test_balance_constraints_respected() -> None:
    df = generate_candidate_compositions(_config_basic())
    assert (df["balance_mg_g"] >= 700.0).all()
    assert (df["balance_mg_g"] <= 900.0).all()


def test_fixed_level_component_is_handled() -> None:
    cfg = RunConfig(
        components=[
            ComponentSpec(name="API", is_api=True),
            ComponentSpec(name="Exc1"),
            ComponentSpec(name="Exc2"),
            ComponentSpec(name="Balance", is_balance=True),
        ],
        api_content_mg_mg=1.0,
        product_strengths=[
            ProductStrength(name="S1", component_targets_mg_g={"API": 10.0, "Exc1": 100.0, "Exc2": 20.0})
        ],
        component_constraints=[
            ComponentConstraint(component_name="API", min_mg_g=10.0, max_mg_g=20.0, preferred_levels=2),
            ComponentConstraint(component_name="Exc1", min_mg_g=100.0, max_mg_g=150.0, preferred_levels=2),
            ComponentConstraint(component_name="Exc2", min_mg_g=20.0, max_mg_g=20.0, preferred_levels=1),
            ComponentConstraint(component_name="Balance", min_mg_g=700.0, max_mg_g=900.0, preferred_levels=1),
        ],
        batch_settings=BatchSettings(desired_batches=4, min_batches=3, max_batches=10),
    )
    df = generate_candidate_compositions(cfg)
    assert set(df["Exc2_mg_g"].unique().tolist()) == {20.0}


def test_candidate_generation_is_deterministic() -> None:
    cfg = _config_basic()
    df1 = generate_candidate_compositions(cfg)
    df2 = generate_candidate_compositions(cfg)
    assert df1.equals(df2)


def test_duplicate_candidates_are_removed() -> None:
    cfg = RunConfig(
        components=[
            ComponentSpec(name="API", is_api=True),
            ComponentSpec(name="Exc1"),
            ComponentSpec(name="Balance", is_balance=True),
        ],
        api_content_mg_mg=1.0,
        product_strengths=[ProductStrength(name="S1", component_targets_mg_g={"API": 10.0, "Exc1": 100.0})],
        component_constraints=[
            ComponentConstraint(component_name="API", min_mg_g=10.0, max_mg_g=10.0, preferred_levels=3),
            ComponentConstraint(component_name="Exc1", min_mg_g=100.0, max_mg_g=100.0, preferred_levels=2),
            ComponentConstraint(component_name="Balance", min_mg_g=800.0, max_mg_g=900.0, preferred_levels=1),
        ],
        api_calibration_range_settings=ApiCalibrationRangeSettings(
            mode="absolute_mg_g",
            lower=10.0,
            upper=10.0,
            api_levels=2,
            include_target_api_level=True,
        ),
        batch_settings=BatchSettings(desired_batches=1, min_batches=1, max_batches=3),
    )
    df = generate_candidate_compositions(cfg)
    assert len(df) == 1


def test_calculated_balance_component_generation_for_feasible_snac_case() -> None:
    cfg = RunConfig(
        components=[
            ComponentSpec(name="API", is_api=True),
            ComponentSpec(name="SNAC", is_balance=True),
            ComponentSpec(name="Niacinamide"),
            ComponentSpec(name="Glidant"),
        ],
        api_content_mg_mg=0.8,
        product_strengths=[
            ProductStrength(
                name="Target",
                component_targets_mg_g={
                    "API": 14.0,
                    "SNAC": 570.5,
                    "Niacinamide": 397.0,
                    "Glidant": 15.0,
                },
            )
        ],
        component_constraints=[
            ComponentConstraint(component_name="API", min_mg_g=0.0, max_mg_g=20.0, preferred_levels=5),
            ComponentConstraint(component_name="SNAC", min_mg_g=500.0, max_mg_g=600.0, preferred_levels=1),
            ComponentConstraint(component_name="Niacinamide", min_mg_g=300.0, max_mg_g=450.0, preferred_levels=3),
            ComponentConstraint(component_name="Glidant", min_mg_g=10.0, max_mg_g=20.0, preferred_levels=3),
        ],
        batch_settings=BatchSettings(desired_batches=16, min_batches=10, max_batches=24),
    )

    raw_grid = calculate_raw_grid_combinations(cfg)
    df = generate_candidate_compositions(cfg)

    assert raw_grid == 45
    assert len(df) >= 10
    assert (df["balance_mg_g"] >= 500.0).all()
    assert (df["balance_mg_g"] <= 600.0).all()
    assert (df["sum_weighed_components_mg_g"] - 1000.0).abs().max() <= 1e-6
