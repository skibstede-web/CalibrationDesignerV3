from __future__ import annotations

import tkinter as tk

import pytest

from calibration_designer_v3.core.pipeline import run_design_pipeline
from calibration_designer_v3.models.config import build_example_run_config
from calibration_designer_v3.ui import main_window


def create_app_root_or_skip() -> tuple[tk.Tk, main_window.CalibrationDesignerApp]:
    try:
        return main_window.create_app_root()
    except tk.TclError as exc:
        message = str(exc).lower()
        display_error_markers = ("display", "screen", "couldn't connect", "no protocol specified")
        if any(marker in message for marker in display_error_markers):
            pytest.skip("Tk display not available in this environment")
        raise


def test_ui_module_imports() -> None:
    assert hasattr(main_window, "CalibrationDesignerApp")


def test_main_app_object_constructs_without_mainloop() -> None:
    root, app = create_app_root_or_skip()

    try:
        assert app is not None
    finally:
        root.destroy()


def test_missing_logo_does_not_crash() -> None:
    root, app = create_app_root_or_skip()

    try:
        assert app.root.title() == "CalibrationDesignerV3"
    finally:
        root.destroy()


def test_example_input_generates_design_through_backend() -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    assert len(result.design.batches) > 0
