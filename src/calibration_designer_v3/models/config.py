"""Configuration helpers for defaults and examples."""

from __future__ import annotations

from calibration_designer_v3.models.domain import (
    BatchSettings,
    ComponentConstraint,
    ComponentSpec,
    ProductStrength,
    RunConfig,
)


def build_example_run_config() -> RunConfig:
    components = [
        ComponentSpec(name="API", is_api=True),
        ComponentSpec(name="SNAC"),
        ComponentSpec(name="Niacinamide"),
        ComponentSpec(name="Glidant"),
        ComponentSpec(name="Lactose", is_balance=True),
    ]

    constraints = [
        ComponentConstraint(component_name="API", min_mg_g=10.0, max_mg_g=60.0, preferred_levels=6),
        ComponentConstraint(component_name="SNAC", min_mg_g=20.0, max_mg_g=120.0, preferred_levels=5),
        ComponentConstraint(component_name="Niacinamide", min_mg_g=5.0, max_mg_g=60.0, preferred_levels=4),
        ComponentConstraint(component_name="Glidant", min_mg_g=2.0, max_mg_g=15.0, preferred_levels=3),
        ComponentConstraint(component_name="Lactose", min_mg_g=600.0, max_mg_g=980.0, preferred_levels=1),
    ]

    strengths = [
        ProductStrength(
            name="1%",
            component_targets_mg_g={
                "API": 10.0,
                "SNAC": 60.0,
                "Niacinamide": 20.0,
                "Glidant": 6.0,
            },
        ),
        ProductStrength(
            name="3%",
            component_targets_mg_g={
                "API": 30.0,
                "SNAC": 70.0,
                "Niacinamide": 25.0,
                "Glidant": 8.0,
            },
        ),
        ProductStrength(
            name="6%",
            component_targets_mg_g={
                "API": 60.0,
                "SNAC": 90.0,
                "Niacinamide": 30.0,
                "Glidant": 10.0,
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
        batch_settings=batch_settings,
        seed=123,
    )