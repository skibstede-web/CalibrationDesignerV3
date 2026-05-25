from __future__ import annotations

import math

import numpy as np

from calibration_designer_v3.core.diagnostics import calculate_diagnostics
from calibration_designer_v3.models.domain import (
    BatchSettings,
    CalibrationBatch,
    ComponentConstraint,
    ComponentSpec,
    ProductStrength,
    RunConfig,
)


def _config() -> RunConfig:
    return RunConfig(
        components=[
            ComponentSpec(name="API", is_api=True),
            ComponentSpec(name="Exc1"),
            ComponentSpec(name="Exc2"),
            ComponentSpec(name="Balance", is_balance=True),
        ],
        api_content_mg_mg=1.0,
        product_strengths=[
            ProductStrength(name="S", component_targets_mg_g={"API": 20.0, "Exc1": 100.0, "Exc2": 50.0})
        ],
        component_constraints=[
            ComponentConstraint(component_name="API", min_mg_g=10.0, max_mg_g=60.0, preferred_levels=6),
            ComponentConstraint(component_name="Exc1", min_mg_g=10.0, max_mg_g=300.0, preferred_levels=6),
            ComponentConstraint(component_name="Exc2", min_mg_g=10.0, max_mg_g=300.0, preferred_levels=6),
            ComponentConstraint(component_name="Balance", min_mg_g=200.0, max_mg_g=980.0, preferred_levels=1),
        ],
        batch_settings=BatchSettings(desired_batches=6, min_batches=1, max_batches=20),
    )


def _batch(i: int, api: float, exc1: float, exc2: float) -> CalibrationBatch:
    balance = 1000.0 - api - exc1 - exc2
    return CalibrationBatch(
        batch_id=f"CAL-{i:03d}",
        batch_name=f"B{i}",
        api_pure_mg_g=api,
        api_content_mg_mg=1.0,
        api_ds_total_mg_g=api,
        api_impurity_mg_g=0.0,
        component_mg_g={"Exc1": exc1, "Exc2": exc2, "Balance": balance},
        balance_mg_g=balance,
        sum_weighed_components_mg_g=1000.0,
    )


def test_correlation_matrix_has_expected_shape() -> None:
    cfg = _config()
    batches = [_batch(i + 1, api=10.0 + i * 10.0, exc1=100.0 + i, exc2=50.0 + 2 * i) for i in range(6)]
    result = calculate_diagnostics(batches, cfg)
    assert result.correlation_matrix.shape == (4, 4)


def test_api_excipient_correlation_detected() -> None:
    cfg = _config()
    batches = [_batch(i + 1, api=10.0 + i * 10.0, exc1=100.0 + i * 20.0, exc2=80.0 - i * 5.0) for i in range(6)]
    result = calculate_diagnostics(batches, cfg)
    corr_row = result.api_vs_component[result.api_vs_component["component"] == "Exc1_mg_g"].iloc[0]
    assert corr_row["abs_correlation"] > 0.9


def test_high_correlation_warning() -> None:
    cfg = _config()
    api = [10, 20, 30, 40, 50, 60]
    exc1 = [1, 2, 3, 5, 6, 4]  # corr ~= 0.8286
    batches = [_batch(i + 1, float(a), float(e1), 50.0) for i, (a, e1) in enumerate(zip(api, exc1, strict=True))]
    result = calculate_diagnostics(batches, cfg)
    row = result.api_vs_component[result.api_vs_component["component"] == "Exc1_mg_g"].iloc[0]
    assert row["status"] == "WARNING"


def test_critical_correlation_warning() -> None:
    cfg = _config()
    batches = [_batch(i + 1, float(10 + i * 10), float(i + 1), 70.0) for i in range(6)]
    result = calculate_diagnostics(batches, cfg)
    row = result.api_vs_component[result.api_vs_component["component"] == "Exc1_mg_g"].iloc[0]
    assert row["status"] == "CRITICAL"


def test_collinear_design_has_high_vif() -> None:
    cfg = _config()
    batches = [_batch(i + 1, float(10 + i * 10), float(2 * (10 + i * 10)), float(3 * (10 + i * 10))) for i in range(6)]
    result = calculate_diagnostics(batches, cfg)
    vif_row = result.summary[result.summary["metric"] == "api_vif_excluding_balance"].iloc[0]
    assert np.isinf(vif_row["value"]) or vif_row["value"] > 10


def test_non_collinear_design_has_lower_vif() -> None:
    cfg = _config()
    batches = [
        _batch(1, 10.0, 2.0, 9.0),
        _batch(2, 20.0, 5.0, 2.0),
        _batch(3, 30.0, 1.0, 8.0),
        _batch(4, 40.0, 6.0, 3.0),
        _batch(5, 50.0, 3.0, 7.0),
        _batch(6, 60.0, 4.0, 1.0),
    ]
    result = calculate_diagnostics(batches, cfg)
    vif_row = result.summary[result.summary["metric"] == "api_vif_excluding_balance"].iloc[0]
    assert math.isfinite(vif_row["value"])
    assert vif_row["value"] < 10


def test_constant_components_do_not_crash() -> None:
    cfg = _config()
    batches = [_batch(i + 1, float(10 + i * 10), 100.0, 50.0) for i in range(6)]
    result = calculate_diagnostics(batches, cfg)
    assert not result.summary.empty


def test_balance_excluded_from_default_vif() -> None:
    cfg = _config()
    batches = [
        _batch(1, 10.0, 100.0, 70.0),
        _batch(2, 20.0, 80.0, 60.0),
        _batch(3, 30.0, 120.0, 65.0),
        _batch(4, 40.0, 90.0, 55.0),
        _batch(5, 50.0, 110.0, 50.0),
        _batch(6, 60.0, 95.0, 45.0),
    ]
    result = calculate_diagnostics(batches, cfg)
    vif_row = result.summary[result.summary["metric"] == "api_vif_excluding_balance"].iloc[0]
    assert math.isfinite(vif_row["value"])