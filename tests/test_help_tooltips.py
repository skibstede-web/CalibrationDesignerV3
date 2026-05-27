from __future__ import annotations

import tkinter as tk

import pytest

from calibration_designer_v3.ui.help_tooltips import HELP_TEXTS, REQUIRED_INPUT_HELP_KEYS, HoverTooltip


def _root_or_skip() -> tk.Tk:
    try:
        return tk.Tk()
    except tk.TclError as exc:
        message = str(exc).lower()
        if any(marker in message for marker in ("display", "screen", "couldn't connect", "no protocol specified")):
            pytest.skip("Tk display not available in this environment")
        raise


def test_help_texts_include_all_expected_input_entries() -> None:
    required_keys = {
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
    assert required_keys.issubset(HELP_TEXTS.keys())
    assert set(REQUIRED_INPUT_HELP_KEYS).issubset(HELP_TEXTS.keys())


def test_hover_tooltip_constructs_without_crashing() -> None:
    root = _root_or_skip()
    try:
        btn = tk.Button(root, text="?")
        btn.pack()
        tooltip = HoverTooltip(btn, text="test help text")
        assert tooltip is not None
    finally:
        root.destroy()
