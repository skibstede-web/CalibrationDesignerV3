from __future__ import annotations

import json
from pathlib import Path

import pytest

from calibration_designer_v3.app import run_input_state_smoke_test
from calibration_designer_v3.core.pipeline import run_design_pipeline
from calibration_designer_v3.io.export import export_design_run
from calibration_designer_v3.models.config import build_example_run_config
from calibration_designer_v3.ui.input_state import (
    ManualBatchInputRow,
    app_input_state_from_run_config,
    build_run_config_from_app_input_state,
    evaluate_strength_totals,
)


def _reclose_strength_totals(state) -> None:
    api_idx = next(i for i, component in enumerate(state.components) if component.is_api)
    balance_idx = next(i for i, component in enumerate(state.components) if component.is_balance)
    for strength in state.strengths:
        api_ds = strength.targets_mg_g[api_idx] / state.api_content_mg_mg
        non_api_non_balance = sum(
            strength.targets_mg_g[i] for i in range(len(strength.targets_mg_g)) if i not in {api_idx, balance_idx}
        )
        strength.targets_mg_g[balance_idx] = 1000.0 - api_ds - non_api_non_balance


def test_input_state_roundtrip_and_edit_conversion() -> None:
    cfg = build_example_run_config()
    state = app_input_state_from_run_config(cfg)

    state.components[1].component_type = "minor_excipient"
    state.api_content_mg_mg = 0.77
    state.strengths[0].name = "EditedStrength"
    state.strengths[0].targets_mg_g[2] = 430.0
    _reclose_strength_totals(state)
    state.batch_settings.default_batch_size = 2.0
    state.seed = 321

    rebuilt = build_run_config_from_app_input_state(state)
    assert rebuilt.components[1].component_type == "minor_excipient"
    assert rebuilt.api_content_mg_mg == 0.77
    assert rebuilt.product_strengths[0].name == "EditedStrength"
    assert rebuilt.batch_settings.default_batch_size == 2.0
    assert rebuilt.seed == 321


def test_manual_batch_input_is_used_by_design_generation() -> None:
    cfg = build_example_run_config()
    state = app_input_state_from_run_config(cfg)
    state.manual_batches = [
        ManualBatchInputRow(
            batch_name="Manual Forced Batch",
            api_pure_mg_g=12.0,
            non_api_non_balance_mg_g=[440.0, 15.0],
            forced=True,
            locked=False,
            reusable_across_strengths=True,
        )
    ]

    rebuilt = build_run_config_from_app_input_state(state)
    result = run_design_pipeline(rebuilt)
    assert any(batch.batch_name == "Manual Forced Batch" for batch in result.design.batches)


def test_input_state_smoke_test_passes() -> None:
    assert run_input_state_smoke_test() == 0


def test_strength_totals_validation() -> None:
    cfg = build_example_run_config()
    state = app_input_state_from_run_config(cfg)
    validations = evaluate_strength_totals(
        components=state.components,
        strengths=state.strengths,
        api_content_mg_mg=state.api_content_mg_mg,
    )
    assert all(entry.is_valid for entry in validations)

    state.strengths[0].targets_mg_g[2] += 10.0
    invalid = evaluate_strength_totals(
        components=state.components,
        strengths=state.strengths,
        api_content_mg_mg=state.api_content_mg_mg,
    )
    assert any(not entry.is_valid for entry in invalid)


def test_multiple_target_strengths_supported_with_validation() -> None:
    cfg = build_example_run_config()
    state = app_input_state_from_run_config(cfg)
    state.strengths.append(type(state.strengths[0])(name="Second", targets_mg_g=list(state.strengths[0].targets_mg_g)))
    validations = evaluate_strength_totals(
        components=state.components,
        strengths=state.strengths,
        api_content_mg_mg=state.api_content_mg_mg,
    )
    assert len(validations) == 2
    assert all(entry.is_valid for entry in validations)


def test_exported_run_configuration_contains_new_workflow_settings(local_tmp_path: Path) -> None:
    cfg = build_example_run_config()
    state = app_input_state_from_run_config(cfg)
    state.excipient_variation_settings.preset = "aggressive"
    rebuilt = build_run_config_from_app_input_state(state)
    result = run_design_pipeline(rebuilt)
    run_folder = export_design_run(config=rebuilt, pipeline_result=result, output_root=local_tmp_path)
    payload = json.loads((run_folder / "run_configuration.json").read_text(encoding="utf-8"))
    assert "api_calibration_range_settings" in payload
    assert "excipient_variation_settings" in payload
    assert payload["excipient_variation_settings"]["preset"] == rebuilt.excipient_variation_settings.preset


def test_design_generation_uses_edited_strength_api_values() -> None:
    cfg = build_example_run_config()
    state = app_input_state_from_run_config(cfg)
    state.objective_settings.include_target_strengths_in_calibration_design = True
    state.strengths.append(type(state.strengths[0])(name="Second", targets_mg_g=list(state.strengths[0].targets_mg_g)))
    state.strengths[0].targets_mg_g[0] = 8.0
    state.strengths[1].targets_mg_g[0] = 14.0
    _reclose_strength_totals(state)
    rebuilt = build_run_config_from_app_input_state(state)
    result = run_design_pipeline(rebuilt)
    api_levels = {batch.api_pure_mg_g for batch in result.design.batches}
    assert 8.0 in api_levels
    assert 14.0 in api_levels


def test_balance_can_be_auto_selected_when_not_explicitly_selected() -> None:
    cfg = build_example_run_config()
    state = app_input_state_from_run_config(cfg)
    for component in state.components:
        component.is_balance = False
    rebuilt = build_run_config_from_app_input_state(state)
    assert any(component.is_balance for component in rebuilt.components)
