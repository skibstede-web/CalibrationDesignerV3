from __future__ import annotations

import math

from calibration_designer_v3.core.candidate_generation import generate_candidate_compositions
from calibration_designer_v3.core.design_engine import select_calibration_design
from calibration_designer_v3.core.diagnostics import calculate_diagnostics
from calibration_designer_v3.core.guided_workflow import (
    auto_select_balance_component,
    default_allow_variation_map,
    generate_api_levels_for_strength,
)
from calibration_designer_v3.models.domain import (
    ApiCalibrationRangeSettings,
    BatchSettings,
    ComponentConstraint,
    ComponentSpec,
    ExcipientVariationSettings,
    ProductStrength,
    RunConfig,
)


def _guided_config() -> RunConfig:
    return RunConfig(
        components=[
            ComponentSpec(name="API", is_api=True, component_type="api"),
            ComponentSpec(name="SNAC", is_balance=True, component_type="major_excipient"),
            ComponentSpec(name="Niacinamide", component_type="major_excipient"),
            ComponentSpec(name="Glidant", component_type="glidant_lubricant"),
        ],
        api_content_mg_mg=0.8,
        product_strengths=[
            ProductStrength(
                name="1%",
                component_targets_mg_g={
                    "API": 10.0,
                    "SNAC": 520.5,
                    "Niacinamide": 452.0,
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
        api_calibration_range_settings=ApiCalibrationRangeSettings(
            mode="percent_of_target",
            lower=60.0,
            upper=140.0,
            api_levels=5,
            include_target_api_level=True,
            apply_same_api_range_to_all_strengths=True,
        ),
        excipient_variation_settings=ExcipientVariationSettings(
            preset="standard",
            allow_variation_by_component={"SNAC": True, "Niacinamide": True, "Glidant": False},
            keep_glidant_lubricant_fixed=True,
            auto_select_balance_component=True,
        ),
        batch_settings=BatchSettings(desired_batches=16, min_batches=10, max_batches=24),
    )


def test_api_range_generation_percent_of_target_mode() -> None:
    levels = generate_api_levels_for_strength(
        target_api_pure_mg_g=10.0,
        settings=ApiCalibrationRangeSettings(
            mode="percent_of_target",
            lower=60.0,
            upper=140.0,
            api_levels=5,
            include_target_api_level=True,
        ),
    )
    assert levels == [6.0, 8.0, 10.0, 12.0, 14.0]


def test_api_range_generation_absolute_mode() -> None:
    levels = generate_api_levels_for_strength(
        target_api_pure_mg_g=10.0,
        settings=ApiCalibrationRangeSettings(
            mode="absolute_mg_g",
            lower=4.0,
            upper=12.0,
            api_levels=5,
            include_target_api_level=False,
        ),
    )
    assert levels == [4.0, 6.0, 8.0, 10.0, 12.0]


def test_include_target_api_level_off_does_not_force_target() -> None:
    levels = generate_api_levels_for_strength(
        target_api_pure_mg_g=10.0,
        settings=ApiCalibrationRangeSettings(
            mode="percent_of_target",
            lower=60.0,
            upper=140.0,
            api_levels=4,
            include_target_api_level=False,
        ),
    )
    assert 10.0 not in levels


def test_auto_balance_selection_prefers_major_non_glidant() -> None:
    cfg = _guided_config()
    chosen = auto_select_balance_component(
        components=cfg.components,
        strength=cfg.product_strengths[0],
        allow_variation_by_component=default_allow_variation_map(cfg.components),
        keep_glidant_lubricant_fixed=True,
    )
    assert chosen == "SNAC"
    assert chosen != "Glidant"


def test_candidate_generation_uses_api_ds_and_sums_to_1000() -> None:
    cfg = _guided_config()
    candidates = generate_candidate_compositions(cfg)
    assert not candidates.empty
    assert (candidates["sum_weighed_components_mg_g"] - 1000.0).abs().max() <= 1e-6

    row = candidates.iloc[0]
    assert math.isclose(row["api_ds_total_mg_g"], row["api_pure_mg_g"] / 0.8, rel_tol=0.0, abs_tol=1e-9)


def test_flexible_excipient_variation_produces_more_candidates_than_fixed() -> None:
    flexible = _guided_config()
    fixed = flexible.model_copy(deep=True)
    fixed.excipient_variation_settings = ExcipientVariationSettings(
        preset="custom",
        allow_variation_by_component={"SNAC": False, "Niacinamide": False, "Glidant": False},
        keep_glidant_lubricant_fixed=True,
        auto_select_balance_component=True,
        custom_variation_pct_by_component={"SNAC": 0.0, "Niacinamide": 0.0, "Glidant": 0.0},
    )

    flexible_df = generate_candidate_compositions(flexible)
    fixed_df = generate_candidate_compositions(fixed)
    assert len(flexible_df) > len(fixed_df)


def test_selection_returns_desired_batches_when_feasible_pool_is_large_enough() -> None:
    cfg = _guided_config().model_copy(deep=True)
    cfg.batch_settings.desired_batches = 10
    cfg.batch_settings.min_batches = 8
    cfg.batch_settings.max_batches = 24

    result = select_calibration_design(cfg)
    assert len(result.batches) == 10
    assert not any(w.code == "INSUFFICIENT_BATCHES" for w in result.warnings)


def test_selection_warns_when_desired_batches_cannot_be_reached() -> None:
    cfg = _guided_config().model_copy(deep=True)
    cfg.batch_settings.desired_batches = 24
    cfg.batch_settings.min_batches = 10
    cfg.batch_settings.max_batches = 30

    result = select_calibration_design(cfg)
    assert len(result.batches) < 24
    assert any(w.code == "INSUFFICIENT_BATCHES" for w in result.warnings)


def test_named_api_snac_and_api_niacinamide_diagnostics_are_reported() -> None:
    cfg = _guided_config().model_copy(deep=True)
    cfg.batch_settings.desired_batches = 12

    design = select_calibration_design(cfg)
    diagnostics = calculate_diagnostics(design.batches, cfg)
    metrics = set(diagnostics.summary["metric"].tolist())
    assert "api_vs_snac_correlation" in metrics
    assert "api_vs_niacinamide_correlation" in metrics
