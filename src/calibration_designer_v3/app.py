"""Top-level application entry points."""

from __future__ import annotations

import argparse

from calibration_designer_v3.models.config import build_example_run_config


def run_smoke_test() -> int:
    config = build_example_run_config()
    if config.api_content_mg_mg <= 0:
        return 1
    if not any(component.is_api for component in config.components):
        return 1
    if not any(component.is_balance for component in config.components):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="calibration_designer_v3")
    parser.add_argument("--smoke-test", action="store_true", help="Run non-GUI smoke checks")
    args = parser.parse_args(argv)

    if args.smoke_test:
        return run_smoke_test()

    from calibration_designer_v3.ui.main_window import launch_ui

    launch_ui()
    return 0
