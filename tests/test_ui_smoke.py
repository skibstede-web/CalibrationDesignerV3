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


def test_header_logo_is_display_resized_when_available() -> None:
    root, app = create_app_root_or_skip()

    try:
        if app._header_logo_image is None:
            pytest.skip("Header logo not available")
        assert app._header_logo_image.height() <= main_window.HEADER_LOGO_MAX_HEIGHT
    finally:
        root.destroy()


def test_input_sections_are_clean_scrollable_and_do_not_show_manual_editor() -> None:
    root, app = create_app_root_or_skip()

    def visible_texts(widget: tk.Misc) -> list[str]:
        texts: list[str] = []
        try:
            text = str(widget.cget("text"))
        except tk.TclError:
            text = ""
        if text:
            texts.append(text)
        for child in widget.winfo_children():
            texts.extend(visible_texts(child))
        return texts

    try:
        texts = visible_texts(app.root)
        expected_titles = {
            "Component setup",
            "Product strengths",
            "API calibration range",
            "Excipient variation strategy",
            "Batch number and batch size settings",
        }
        assert expected_titles.issubset(set(texts))
        assert not any(text.startswith(("1.", "2.", "3.", "4.", "5.")) for text in texts)
        assert "Advanced: Manual design editing" not in texts
        assert len(app.input_section_vertical_scrollbars) == 5
        assert len(app.input_section_cards) == 5
        assert isinstance(app.main_split_pane, tk.PanedWindow)
        assert len(app.main_split_pane.panes()) == 2
    finally:
        root.destroy()


def test_example_input_generates_design_through_backend() -> None:
    cfg = build_example_run_config()
    result = run_design_pipeline(cfg)
    assert len(result.design.batches) > 0
