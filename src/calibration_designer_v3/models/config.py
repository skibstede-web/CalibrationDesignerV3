"""Configuration helpers for defaults and examples."""

from __future__ import annotations

from calibration_designer_v3.models.domain import (
    ApiCalibrationRangeSettings,
    BatchSettings,
    ComponentConstraint,
    ComponentSpec,
    ExcipientVariationSettings,
    ProductStrength,
    RunConfig,
)


def build_example_run_config() -> RunConfig:
    components = [
        ComponentSpec(name="API", is_api=True, component_type="api"),
        ComponentSpec(name="SNAC", is_balance=True, component_type="major_excipient"),
        ComponentSpec(name="Niacinamide", component_type="major_excipient"),
        ComponentSpec(name="Glidant", component_type="glidant_lubricant"),
    ]

    constraints = [
        ComponentConstraint(component_name="API", min_mg_g=0.0, max_mg_g=25.0, preferred_levels=5),
        ComponentConstraint(component_name="SNAC", min_mg_g=450.0, max_mg_g=650.0, preferred_levels=1),
        ComponentConstraint(component_name="Niacinamide", min_mg_g=300.0, max_mg_g=500.0, preferred_levels=3),
        ComponentConstraint(component_name="Glidant", min_mg_g=10.0, max_mg_g=25.0, preferred_levels=1),
    ]

    strengths = [
        ProductStrength(
            name="1%",
            component_targets_mg_g={
                "API": 10.0,
                "SNAC": 520.5,
                "Niacinamide": 452.0,
                "Glidant": 15.0,
            },
        ),
    ]

    batch_settings = BatchSettings(
        desired_batches=16,
        min_batches=10,
        max_batches=24,
        default_batch_size=1.0,
        batch_size_unit="kg",
        allow_different_batch_sizes=False,
        min_batch_size=1.0,
        max_batch_size=1.0,
    )

    return RunConfig(
        components=components,
        api_content_mg_mg=0.80,
        product_strengths=strengths,
        component_constraints=constraints,
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
        batch_settings=batch_settings,
        seed=123,
    )
