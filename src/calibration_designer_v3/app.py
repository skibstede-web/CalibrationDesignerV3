"""Top-level application entry points."""

from __future__ import annotations

import argparse

from calibration_designer_v3.core.pipeline import run_design_pipeline
from calibration_designer_v3.models.config import build_example_run_config
from calibration_designer_v3.ui.input_state import (
    app_input_state_from_run_config,
    build_run_config_from_app_input_state,
)


def run_smoke_test() -> int:
    config = build_example_run_config()
    if config.api_content_mg_mg <= 0:
        return 1
    if not any(component.is_api for component in config.components):
        return 1
    if not any(component.is_balance for component in config.components):
        return 1
    return 0


def run_input_state_smoke_test() -> int:
    config = build_example_run_config()
    state = app_input_state_from_run_config(config)

    state.components[0].name = "API_CUSTOM"
    state.api_content_mg_mg = 0.73
    state.strengths[0].name = "CustomStrength"
    state.strengths[0].targets_mg_g[0] = 22.5
    api_index = next(i for i, comp in enumerate(state.components) if comp.is_api)
    balance_index = next(i for i, comp in enumerate(state.components) if comp.is_balance)
    for strength in state.strengths:
        strength.targets_mg_g[api_index] = 22.5
        api_ds_total = strength.targets_mg_g[api_index] / state.api_content_mg_mg
        non_api_non_balance = sum(
            strength.targets_mg_g[i] for i in range(len(strength.targets_mg_g)) if i not in {api_index, balance_index}
        )
        strength.targets_mg_g[balance_index] = 1000.0 - api_ds_total - non_api_non_balance
    state.api_calibration_range_settings.lower = 60.0
    state.api_calibration_range_settings.upper = 140.0
    state.api_calibration_range_settings.api_levels = 5
    state.objective_settings.include_target_strengths_in_calibration_design = True
    state.batch_settings.desired_batches = 8
    state.batch_settings.min_batches = 6
    state.batch_settings.max_batches = 12
    state.batch_settings.default_batch_size = 2.0
    state.seed = 987

    rebuilt = build_run_config_from_app_input_state(state)
    if rebuilt.api_component_name != "API_CUSTOM":
        return 1
    if rebuilt.api_content_mg_mg != 0.73:
        return 1
    if rebuilt.product_strengths[0].name != "CustomStrength":
        return 1
    if rebuilt.batch_settings.desired_batches != 8:
        return 1

    result = run_design_pipeline(rebuilt)
    if len(result.design.batches) == 0:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="calibration_designer_v3")
    parser.add_argument("--smoke-test", action="store_true", help="Run non-GUI smoke checks")
    parser.add_argument("--input-smoke-test", action="store_true", help="Run input-state conversion smoke checks")
    args = parser.parse_args(argv)

    if args.smoke_test:
        return run_smoke_test()
    if args.input_smoke_test:
        return run_input_state_smoke_test()

    from calibration_designer_v3.ui.main_window import launch_ui

    launch_ui()
    return 0
