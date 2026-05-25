from __future__ import annotations

import pandas as pd

from calibration_designer_v3.core.candidate_generation import generate_candidate_compositions
from calibration_designer_v3.core.design_engine import select_calibration_design
from calibration_designer_v3.models.domain import (
    BatchSettings,
    CalibrationBatch,
    ComponentConstraint,
    ComponentSpec,
    DesignObjectiveSettings,
    ProductStrength,
    RunConfig,
)


def _base_config(
    desired_batches: int = 4,
    include_target_strengths: bool = False,
    manual_batches: list[CalibrationBatch] | None = None,
) -> RunConfig:
    return RunConfig(
        components=[
            ComponentSpec(name="API", is_api=True),
            ComponentSpec(name="Exc1"),
            ComponentSpec(name="Balance", is_balance=True),
        ],
        api_content_mg_mg=1.0,
        product_strengths=[
            ProductStrength(name="S1", component_targets_mg_g={"API": 10.0, "Exc1": 150.0}),
            ProductStrength(name="S2", component_targets_mg_g={"API": 20.0, "Exc1": 150.0}),
        ],
        component_constraints=[
            ComponentConstraint(component_name="API", min_mg_g=10.0, max_mg_g=20.0, preferred_levels=2),
            ComponentConstraint(component_name="Exc1", min_mg_g=100.0, max_mg_g=200.0, preferred_levels=3),
            ComponentConstraint(component_name="Balance", min_mg_g=700.0, max_mg_g=900.0, preferred_levels=1),
        ],
        objective_settings=DesignObjectiveSettings(
            include_target_strengths_in_calibration_design=include_target_strengths,
        ),
        batch_settings=BatchSettings(desired_batches=desired_batches, min_batches=1, max_batches=30),
        manual_batches=manual_batches or [],
    )


def test_design_contains_desired_batches_when_enough_candidates() -> None:
    cfg = _base_config(desired_batches=4)
    result = select_calibration_design(cfg)
    assert len(result.batches) == 4


def test_returns_available_candidates_with_warning_if_fewer_than_desired() -> None:
    cfg = _base_config(desired_batches=10)
    result = select_calibration_design(cfg)
    assert len(result.batches) == 6
    assert any(w.code == "INSUFFICIENT_BATCHES" for w in result.warnings)


def test_target_strengths_included_when_toggle_on() -> None:
    cfg = _base_config(desired_batches=3, include_target_strengths=True)
    result = select_calibration_design(cfg)
    api_levels = {b.api_pure_mg_g for b in result.batches}
    assert 10.0 in api_levels
    assert 20.0 in api_levels


def test_target_strengths_not_forced_when_toggle_off() -> None:
    cfg = _base_config(desired_batches=1, include_target_strengths=False)
    result = select_calibration_design(cfg)
    assert len(result.batches) == 1


def test_locked_and_forced_batches_are_preserved() -> None:
    locked = CalibrationBatch(
        batch_name="Locked Batch",
        locked=True,
        forced=True,
        api_pure_mg_g=15.0,
        api_content_mg_mg=1.0,
        api_ds_total_mg_g=15.0,
        api_impurity_mg_g=0.0,
        component_mg_g={"Exc1": 150.0, "Balance": 835.0},
        balance_mg_g=835.0,
        sum_weighed_components_mg_g=1000.0,
    )
    cfg = _base_config(desired_batches=3, manual_batches=[locked])
    result = select_calibration_design(cfg)
    assert any(batch.batch_name == "Locked Batch" for batch in result.batches)


def test_same_inputs_give_same_selected_design() -> None:
    cfg = _base_config(desired_batches=4)
    result1 = select_calibration_design(cfg)
    result2 = select_calibration_design(cfg)

    rows1 = [(b.batch_id, b.api_pure_mg_g, b.balance_mg_g) for b in result1.batches]
    rows2 = [(b.batch_id, b.api_pure_mg_g, b.balance_mg_g) for b in result2.batches]
    assert rows1 == rows2


def test_engine_does_not_select_infeasible_candidates() -> None:
    cfg = _base_config(desired_batches=1)
    good = {
        "api_pure_mg_g": 10.0,
        "api_content_mg_mg": 1.0,
        "api_ds_total_mg_g": 10.0,
        "api_impurity_mg_g": 0.0,
        "Exc1_mg_g": 100.0,
        "balance_mg_g": 890.0,
        "sum_weighed_components_mg_g": 1000.0,
    }
    bad = {
        "api_pure_mg_g": 10.0,
        "api_content_mg_mg": 1.0,
        "api_ds_total_mg_g": 10.0,
        "api_impurity_mg_g": 0.0,
        "Exc1_mg_g": 500.0,
        "balance_mg_g": 490.0,
        "sum_weighed_components_mg_g": 1000.0,
    }
    candidates = pd.DataFrame([bad, good])
    result = select_calibration_design(cfg, candidates=candidates)
    assert len(result.batches) == 1
    assert result.batches[0].balance_mg_g == 890.0


def test_generated_candidates_used_by_default() -> None:
    cfg = _base_config(desired_batches=2)
    candidates = generate_candidate_compositions(cfg)
    result = select_calibration_design(cfg)
    assert not candidates.empty
    assert len(result.batches) == 2