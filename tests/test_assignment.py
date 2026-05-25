from __future__ import annotations

from calibration_designer_v3.core.assignment import assign_batches_to_strength_models
from calibration_designer_v3.models.domain import (
    BatchSettings,
    CalibrationBatch,
    ComponentConstraint,
    ComponentSpec,
    DesignObjectiveSettings,
    ProductStrength,
    RunConfig,
)


def _config(reuse: bool) -> RunConfig:
    return RunConfig(
        components=[
            ComponentSpec(name="API", is_api=True),
            ComponentSpec(name="Exc1"),
            ComponentSpec(name="Balance", is_balance=True),
        ],
        api_content_mg_mg=1.0,
        product_strengths=[
            ProductStrength(name="S1", component_targets_mg_g={"API": 10.0, "Exc1": 100.0}),
            ProductStrength(name="S2", component_targets_mg_g={"API": 30.0, "Exc1": 100.0}),
            ProductStrength(name="S3", component_targets_mg_g={"API": 50.0, "Exc1": 100.0}),
        ],
        component_constraints=[
            ComponentConstraint(component_name="API", min_mg_g=5.0, max_mg_g=60.0, preferred_levels=6),
            ComponentConstraint(component_name="Exc1", min_mg_g=80.0, max_mg_g=150.0, preferred_levels=4),
            ComponentConstraint(component_name="Balance", min_mg_g=700.0, max_mg_g=920.0, preferred_levels=1),
        ],
        objective_settings=DesignObjectiveSettings(allow_reuse_across_strength_models=reuse),
        batch_settings=BatchSettings(desired_batches=3, min_batches=1, max_batches=10),
    )


def _batch(batch_id: str, api: float, assigned: list[str] | None = None) -> CalibrationBatch:
    exc1 = 100.0
    balance = 1000.0 - api - exc1
    return CalibrationBatch(
        batch_id=batch_id,
        batch_name=batch_id,
        assigned_strength_models=assigned or [],
        api_pure_mg_g=api,
        api_content_mg_mg=1.0,
        api_ds_total_mg_g=api,
        api_impurity_mg_g=0.0,
        component_mg_g={"Exc1": exc1, "Balance": balance},
        balance_mg_g=balance,
        sum_weighed_components_mg_g=1000.0,
    )


def test_nearest_strength_assignment() -> None:
    cfg = _config(reuse=False)
    batches = [_batch("CAL-001", 12.0), _batch("CAL-002", 49.0)]
    table = assign_batches_to_strength_models(batches, cfg)

    first = table[table["batch_id"] == "CAL-001"].iloc[0]
    second = table[table["batch_id"] == "CAL-002"].iloc[0]
    assert first["strength_model"] == "S1"
    assert second["strength_model"] == "S3"


def test_reuse_on_increases_or_maintains_assignment_count() -> None:
    batches = [_batch("CAL-001", 29.0), _batch("CAL-002", 31.0)]
    off_count = len(assign_batches_to_strength_models(batches, _config(reuse=False)))
    on_count = len(assign_batches_to_strength_models(batches, _config(reuse=True)))
    assert on_count >= off_count


def test_reuse_off_assigns_only_nearest_unless_manual_assignment() -> None:
    cfg = _config(reuse=False)
    batch = _batch("CAL-001", 30.0)
    table = assign_batches_to_strength_models([batch], cfg)
    assert len(table) == 1


def test_model_assignment_table_long_format_columns() -> None:
    cfg = _config(reuse=True)
    table = assign_batches_to_strength_models([_batch("CAL-001", 28.0)], cfg)
    assert {"batch_id", "strength_model", "included", "role_in_model"}.issubset(table.columns)


def test_manual_assignment_metadata_is_respected() -> None:
    cfg = _config(reuse=False)
    batch = _batch("CAL-001", 12.0, assigned=["S2", "S3"])
    table = assign_batches_to_strength_models([batch], cfg)
    assert table["strength_model"].tolist() == ["S2", "S3"]