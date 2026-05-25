from __future__ import annotations

import pytest
from pydantic import ValidationError

from calibration_designer_v3.models.config import build_example_run_config
from calibration_designer_v3.models.domain import (
    BatchSettings,
    ComponentConstraint,
    ComponentSpec,
    ProductStrength,
    RunConfig,
)


def _base_components() -> list[ComponentSpec]:
    return [
        ComponentSpec(name="API", is_api=True),
        ComponentSpec(name="Exc1"),
        ComponentSpec(name="Balance", is_balance=True),
    ]


def _base_constraints() -> list[ComponentConstraint]:
    return [
        ComponentConstraint(component_name="API", min_mg_g=10, max_mg_g=20, preferred_levels=3),
        ComponentConstraint(component_name="Exc1", min_mg_g=100, max_mg_g=200, preferred_levels=3),
        ComponentConstraint(component_name="Balance", min_mg_g=700, max_mg_g=900, preferred_levels=1),
    ]


def _base_strengths() -> list[ProductStrength]:
    return [
        ProductStrength(
            name="2%",
            component_targets_mg_g={"API": 20.0, "Exc1": 150.0},
        )
    ]


def _valid_run_config() -> RunConfig:
    return RunConfig(
        components=_base_components(),
        api_content_mg_mg=0.8,
        product_strengths=_base_strengths(),
        component_constraints=_base_constraints(),
        batch_settings=BatchSettings(desired_batches=10, min_batches=8, max_batches=12),
    )


def test_valid_configuration_is_accepted() -> None:
    cfg = _valid_run_config()
    assert cfg.api_component_name == "API"
    assert cfg.balance_component_name == "Balance"


def test_missing_api_rejected() -> None:
    components = [
        ComponentSpec(name="Exc1"),
        ComponentSpec(name="Balance", is_balance=True),
    ]
    with pytest.raises(ValidationError):
        RunConfig(
            components=components,
            api_content_mg_mg=0.8,
            product_strengths=_base_strengths(),
            component_constraints=[
                ComponentConstraint(component_name="Exc1", min_mg_g=100, max_mg_g=200, preferred_levels=3),
                ComponentConstraint(component_name="Balance", min_mg_g=700, max_mg_g=900, preferred_levels=1),
            ],
        )


def test_missing_balance_rejected() -> None:
    components = [ComponentSpec(name="API", is_api=True), ComponentSpec(name="Exc1")]
    with pytest.raises(ValidationError):
        RunConfig(
            components=components,
            api_content_mg_mg=0.8,
            product_strengths=_base_strengths(),
            component_constraints=[
                ComponentConstraint(component_name="API", min_mg_g=10, max_mg_g=20, preferred_levels=3),
                ComponentConstraint(component_name="Exc1", min_mg_g=100, max_mg_g=200, preferred_levels=3),
            ],
        )


def test_duplicate_component_names_rejected() -> None:
    components = [
        ComponentSpec(name="API", is_api=True),
        ComponentSpec(name="API"),
        ComponentSpec(name="Balance", is_balance=True),
    ]
    with pytest.raises(ValidationError):
        RunConfig(
            components=components,
            api_content_mg_mg=0.8,
            product_strengths=_base_strengths(),
            component_constraints=[
                ComponentConstraint(component_name="API", min_mg_g=10, max_mg_g=20, preferred_levels=3),
                ComponentConstraint(component_name="Balance", min_mg_g=700, max_mg_g=900, preferred_levels=1),
            ],
        )


def test_invalid_api_content_rejected() -> None:
    with pytest.raises(ValidationError):
        RunConfig(
            components=_base_components(),
            api_content_mg_mg=0.0,
            product_strengths=_base_strengths(),
            component_constraints=_base_constraints(),
        )


def test_invalid_constraints_rejected() -> None:
    with pytest.raises(ValidationError):
        ComponentConstraint(component_name="API", min_mg_g=20, max_mg_g=10, preferred_levels=3)


def test_invalid_preferred_levels_rejected() -> None:
    with pytest.raises(ValidationError):
        ComponentConstraint(component_name="API", min_mg_g=10, max_mg_g=20, preferred_levels=0)


def test_desired_batch_count_outside_limits_rejected() -> None:
    with pytest.raises(ValidationError):
        BatchSettings(desired_batches=25, min_batches=8, max_batches=12)


def test_example_config_is_valid() -> None:
    cfg = build_example_run_config()
    assert cfg.seed == 123