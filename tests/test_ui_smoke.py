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


def test_api_content_input_is_in_component_setup_and_editable() -> None:
    root, app = create_app_root_or_skip()

    try:
        assert app.api_content_entry.winfo_parent() == str(app.component_api_content_frame)
        app.api_content_var.set("0.77")
        app._refresh_dependent_sections()
        assert app.api_content_var.get() == "0.77"
    finally:
        root.destroy()


def test_api_content_input_is_used_in_api_ds_correction_in_ui_totals() -> None:
    root, app = create_app_root_or_skip()

    try:
        api_index = app.component_api_index_var.get()
        targets = app._strength_row_targets(app.strength_rows[0])
        api_pure = float(targets[api_index])

        app.api_content_var.set("0.50")
        app._update_strength_totals()
        api_ds_display = app.strength_rows[0]["api_ds_total_var"].get()  # type: ignore[index]

        assert float(api_ds_display) == pytest.approx(api_pure / 0.50, rel=0, abs=1e-6)
    finally:
        root.destroy()


def test_all_five_input_cards_have_expected_help_icon_keys() -> None:
    root, app = create_app_root_or_skip()

    try:
        expected_keys = {
            "component_count",
            "component_name",
            "api_component_selector",
            "balance_component_selector",
            "component_type",
            "api_content_mg_mg",
            "strength_count",
            "strength_name",
            "component_concentration_mg_g",
            "api_ds_mg_g_display",
            "weighed_total_status",
            "api_range_mode",
            "api_lower_level",
            "api_upper_level",
            "api_level_count",
            "include_target_api_level",
            "apply_same_api_range",
            "variation_preset",
            "allow_variation_by_component",
            "keep_glidant_lubricant_fixed",
            "auto_select_balance_component",
            "manual_balance_override",
            "custom_variation_percentages",
            "use_constrained_mixture_design",
            "reduce_api_excipient_correlation",
            "improve_api_specificity",
            "use_d_optimal_or_approximate_d_optimal_selection",
            "include_target_strengths_in_calibration_design",
            "allow_reuse_across_strength_models",
            "reduce_redundant_overlap_between_strengths",
            "minimize_api_material_consumption",
            "prefer_fewer_calibration_batches",
            "allow_non_nominal_excipient_ratios",
            "desired_batches",
            "min_batches",
            "max_batches",
            "default_batch_size",
            "batch_size_unit",
            "allow_different_batch_sizes",
            "min_batch_size",
            "max_batch_size",
            "include_replicates",
            "replicate_count",
            "replicate_type",
            "seed",
        }
        assert expected_keys.issubset(set(app._help_icon_keys))
    finally:
        root.destroy()


def test_diagnostics_table_is_left_aligned_with_medium_grey_border() -> None:
    root, app = create_app_root_or_skip()

    try:
        app.generate_design()
        tree = app.diagnostics_tree
        columns = tree["columns"]
        assert "explanation" in columns
        assert "interpretation" not in columns
        for column in columns:
            assert str(tree.column(column, "anchor")) == "w"
            assert str(tree.heading(column, "anchor")) == "w"
        assert app.diagnostics_tab.cget("highlightbackground") == main_window.COLORS["table_grid"]
        assert app.diagnostics_tab.cget("highlightthickness") == 1
        assert len(tree.get_children()) > 0
    finally:
        root.destroy()
