"""Main desktop window for CalibrationDesignerV3."""

from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - defensive runtime fallback.
    Image = None  # type: ignore[assignment]
    ImageTk = None  # type: ignore[assignment]

from calibration_designer_v3.core.diagnostics import calculate_diagnostics
from calibration_designer_v3.core.guided_workflow import auto_select_balance_component, default_allow_variation_map
from calibration_designer_v3.core.pipeline import PipelineResult, run_design_pipeline
from calibration_designer_v3.io.export import export_design_run
from calibration_designer_v3.models.config import build_example_run_config
from calibration_designer_v3.plotting.plots import PAIRWISE_DIRNAME
from calibration_designer_v3.models.domain import (
    ApiCalibrationRangeSettings,
    BatchSettings,
    ComponentSpec,
    DesignObjectiveSettings,
    ExcipientVariationSettings,
    ProductStrength,
    RunConfig,
)
from calibration_designer_v3.ui.input_state import (
    AppInputState,
    ComponentInputRow,
    ConstraintInputRow,
    ManualBatchInputRow,
    StrengthInputRow,
    STRENGTH_TOTAL_TARGET_MG_G,
    STRENGTH_TOTAL_TOLERANCE_MG_G,
    build_run_config_from_app_input_state,
    evaluate_strength_totals,
)

COLORS = {
    "primary": "#12355B",
    "accent": "#F28C28",
    "background": "#FAF7F2",
    "panel": "#FFFFFF",
    "secondary_panel": "#EEF3F7",
    "text": "#0B1F33",
    "secondary_text": "#5F6C7B",
    "border": "#D8E0E8",
    "warning_bg": "#FFF4DD",
}

STATUS_COLORS = {
    "info": "#1976D2",
    "warning": "#F9A825",
    "error": "#C62828",
    "success": "#2E7D32",
}

DEFAULT_TK_FONT = "{Segoe UI} 10"
HEADER_LOGO_MAX_HEIGHT = 48


def _load_header_logo_tk_image(logo_path: Path, height_px: int = HEADER_LOGO_MAX_HEIGHT) -> object | None:
    """Load a display-resized header logo while preserving the source image file."""
    if Image is None or ImageTk is None or not logo_path.exists():
        return None

    try:
        with Image.open(logo_path) as loaded:
            logo = loaded.convert("RGBA")

        source_width, source_height = logo.size
        if source_width <= 0 or source_height <= 0:
            return None

        target_height = max(40, min(56, int(height_px)))
        target_width = max(1, int(round(target_height * (source_width / source_height))))
        resampling_module = getattr(Image, "Resampling", Image)
        resampling_filter = getattr(resampling_module, "LANCZOS")
        resized_logo = logo.resize((target_width, target_height), resampling_filter)
        return ImageTk.PhotoImage(resized_logo)
    except Exception:
        return None


class CalibrationDesignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CalibrationDesignerV3")
        self.root.geometry("1500x920")
        self.root.minsize(1200, 760)
        self.root.configure(bg=COLORS["background"])
        self.root.option_add("*Font", DEFAULT_TK_FONT)

        self.config: RunConfig = build_example_run_config()
        self.pipeline_result: PipelineResult | None = None
        self.last_output_folder: Path | None = None

        self.manual_rows: list[ManualBatchInputRow] = []
        self._manual_collapsed = True
        self._header_logo_image: object | None = None

        self._build_layout()
        self._load_state_from_config(self.config)

    def _build_layout(self) -> None:
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._build_header()

        self.main_content = tk.Frame(self.root, bg=COLORS["background"])
        self.main_content.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(2, weight=1)

        self._build_input_sections(self.main_content)
        self._build_manual_secondary_section(self.main_content)
        self._build_output_panels(self.main_content)
        self._build_action_bar()

    def _build_header(self) -> None:
        top_bar = tk.Frame(
            self.root,
            bg=COLORS["primary"],
            highlightbackground=COLORS["accent"],
            highlightthickness=1,
            bd=0,
        )
        top_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 8))
        top_bar.grid_columnconfigure(0, weight=1)

        text_block = tk.Frame(top_bar, bg=COLORS["primary"])
        text_block.grid(row=0, column=0, sticky="w", padx=14, pady=10)

        tk.Label(
            text_block,
            text="CalibrationDesignerV3",
            font=("Segoe UI", 22, "bold"),
            fg="#FFFFFF",
            bg=COLORS["primary"],
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            text_block,
            text="Low-dose NIR reflectance calibration design",
            fg=COLORS["accent"],
            bg=COLORS["primary"],
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        logo_path = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
        self._header_logo_image = _load_header_logo_tk_image(logo_path)
        if self._header_logo_image is not None:
            logo_label = tk.Label(top_bar, image=self._header_logo_image, bg=COLORS["primary"])
            logo_label.grid(row=0, column=1, sticky="e", padx=(10, 14), pady=8)

    def _build_input_sections(self, parent: tk.Frame) -> None:
        section_names = [
            "1. Component setup",
            "2. Product strengths",
            "3. API calibration range",
            "4. Excipient variation strategy",
            "5. Batch number and batch size settings",
        ]

        inputs_card = tk.Frame(
            parent,
            bg=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        inputs_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        inputs_card.grid_columnconfigure(0, weight=1)
        tk.Label(
            inputs_card,
            text="Inputs",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        input_canvas = tk.Canvas(
            inputs_card,
            bg=COLORS["panel"],
            height=430,
            highlightthickness=0,
            bd=0,
        )
        input_canvas.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        input_x_scroll = tk.Scrollbar(inputs_card, orient=tk.HORIZONTAL, command=input_canvas.xview)
        input_x_scroll.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        input_canvas.configure(xscrollcommand=input_x_scroll.set)

        self.section_columns_frame = tk.Frame(input_canvas, bg=COLORS["panel"])
        self._section_window = input_canvas.create_window((0, 0), window=self.section_columns_frame, anchor="nw")

        def _on_sections_configure(_event: tk.Event[tk.Widget]) -> None:
            input_canvas.configure(scrollregion=input_canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event[tk.Widget]) -> None:
            min_width = max(event.width, 5 * 300)
            input_canvas.itemconfigure(self._section_window, width=min_width)

        self.section_columns_frame.bind("<Configure>", _on_sections_configure)
        input_canvas.bind("<Configure>", _on_canvas_configure)

        frames: dict[str, tk.Frame] = {}
        for i, name in enumerate(section_names):
            section_card = tk.Frame(
                self.section_columns_frame,
                bg=COLORS["panel"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
                bd=0,
                width=300,
            )
            section_card.grid(row=0, column=i, sticky="n", padx=6, pady=6)
            section_card.grid_rowconfigure(1, weight=1)

            tk.Label(
                section_card,
                text=name,
                bg=COLORS["panel"],
                fg=COLORS["text"],
                font=("Segoe UI", 11, "bold"),
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

            content = tk.Frame(section_card, bg=COLORS["panel"])
            content.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
            frames[name] = content

        self._build_component_section(frames[section_names[0]])
        self._build_strength_section(frames[section_names[1]])
        self._build_api_range_section(frames[section_names[2]])
        self._build_variation_section(frames[section_names[3]])
        self._build_batch_section(frames[section_names[4]])

    def _build_manual_secondary_section(self, parent: tk.Frame) -> None:
        advanced_card = tk.Frame(
            parent,
            bg=COLORS["secondary_panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        advanced_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        advanced_card.grid_columnconfigure(0, weight=1)

        header = tk.Frame(advanced_card, bg=COLORS["secondary_panel"])
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 6))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="Advanced: Manual design editing",
            bg=COLORS["secondary_panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.manual_toggle_btn = tk.Button(
            header,
            text="Show",
            command=self._toggle_manual_section,
            bg=COLORS["primary"],
            fg="#FFFFFF",
            activebackground="#0D2A48",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
        )
        self.manual_toggle_btn.grid(row=0, column=1, sticky="e")

        self.manual_section_container = tk.Frame(advanced_card, bg=COLORS["panel"])
        self._build_manual_section(self.manual_section_container)

    def _toggle_manual_section(self) -> None:
        self._manual_collapsed = not self._manual_collapsed
        if self._manual_collapsed:
            self.manual_section_container.grid_forget()
            self.manual_toggle_btn.configure(text="Show")
            return
        self.manual_section_container.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.manual_toggle_btn.configure(text="Hide")

    def _build_component_section(self, frame: tk.LabelFrame) -> None:
        controls = tk.Frame(frame)
        controls.pack(fill="x")

        tk.Label(controls, text="Number of components:").grid(row=0, column=0, sticky="w")
        self.component_count_var = tk.StringVar(value="0")
        tk.Entry(controls, textvariable=self.component_count_var, width=6).grid(row=0, column=1, padx=(4, 8))
        tk.Button(controls, text="Apply", command=self._apply_component_count).grid(row=0, column=2, padx=(0, 12))
        tk.Button(controls, text="Refresh names", command=self._refresh_dependent_sections).grid(row=0, column=3, padx=(0, 12))

        tk.Label(controls, text="API content (mg/mg):").grid(row=0, column=4, sticky="w")
        self.api_content_var = tk.StringVar(value="0.80")
        api_content_entry = tk.Entry(controls, textvariable=self.api_content_var, width=10)
        api_content_entry.grid(row=0, column=5, padx=(4, 4))
        api_content_entry.bind("<KeyRelease>", self._on_strength_value_edited)

        self.component_api_index_var = tk.IntVar(value=0)
        self.component_balance_index_var = tk.IntVar(value=0)
        self.component_name_vars: list[tk.StringVar] = []
        self.component_type_vars: list[tk.StringVar] = []

        self.component_rows_frame = tk.Frame(frame)
        self.component_rows_frame.pack(fill="x", pady=(6, 0))

    def _build_strength_section(self, frame: tk.LabelFrame) -> None:
        controls = tk.Frame(frame)
        controls.pack(fill="x")

        tk.Label(controls, text="Number of target strengths:").grid(row=0, column=0, sticky="w")
        self.strength_count_var = tk.StringVar(value="0")
        tk.Entry(controls, textvariable=self.strength_count_var, width=6).grid(row=0, column=1, padx=(4, 8))
        tk.Button(controls, text="Apply", command=self._apply_strength_count).grid(row=0, column=2, padx=(0, 8))

        self.strength_rows: list[dict[str, object]] = []
        self.strength_rows_frame = tk.Frame(frame)
        self.strength_rows_frame.pack(fill="x", pady=(6, 0))
        self.strength_totals_info_var = tk.StringVar(
            value=(
                f"Weighed total target per strength: {STRENGTH_TOTAL_TARGET_MG_G:.3f} mg/g "
                f"(tolerance +/- {STRENGTH_TOTAL_TOLERANCE_MG_G:.3f} mg/g)"
            )
        )
        tk.Label(frame, textvariable=self.strength_totals_info_var, anchor="w").pack(fill="x", pady=(4, 0))

    def _build_api_range_section(self, frame: tk.LabelFrame) -> None:
        tk.Label(frame, text="API range mode").grid(row=0, column=0, sticky="w")
        self.api_range_mode_var = tk.StringVar(value="percent_of_target")
        ttk.Combobox(
            frame,
            textvariable=self.api_range_mode_var,
            values=["percent_of_target", "absolute_mg_g"],
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky="w")
        tk.Label(frame, text="Lower").grid(row=1, column=0, sticky="w")
        self.api_range_lower_var = tk.StringVar(value="60")
        tk.Entry(frame, textvariable=self.api_range_lower_var, width=10).grid(row=1, column=1, sticky="w")
        tk.Label(frame, text="Upper").grid(row=2, column=0, sticky="w")
        self.api_range_upper_var = tk.StringVar(value="140")
        tk.Entry(frame, textvariable=self.api_range_upper_var, width=10).grid(row=2, column=1, sticky="w")
        tk.Label(frame, text="API levels").grid(row=3, column=0, sticky="w")
        self.api_range_levels_var = tk.StringVar(value="5")
        tk.Entry(frame, textvariable=self.api_range_levels_var, width=10).grid(row=3, column=1, sticky="w")
        self.include_target_api_level_var = tk.BooleanVar(value=True)
        self.apply_same_api_range_var = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="Include target API level", variable=self.include_target_api_level_var).grid(
            row=4, column=0, columnspan=2, sticky="w"
        )
        tk.Checkbutton(frame, text="Apply same API range to all strengths", variable=self.apply_same_api_range_var).grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

    def _build_variation_section(self, frame: tk.LabelFrame) -> None:
        tk.Label(frame, text="Variation preset").grid(row=0, column=0, sticky="w")
        self.variation_preset_var = tk.StringVar(value="standard")
        ttk.Combobox(
            frame,
            textvariable=self.variation_preset_var,
            values=["conservative", "standard", "aggressive", "custom"],
            state="readonly",
            width=16,
        ).grid(row=0, column=1, sticky="w")
        self.keep_glidant_fixed_var = tk.BooleanVar(value=True)
        self.auto_select_balance_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            frame,
            text="Keep glidant/lubricant fixed",
            variable=self.keep_glidant_fixed_var,
            command=self._refresh_dependent_sections,
        ).grid(
            row=1, column=0, columnspan=2, sticky="w"
        )
        tk.Checkbutton(
            frame,
            text="Auto-select balance component",
            variable=self.auto_select_balance_var,
            command=self._refresh_dependent_sections,
        ).grid(
            row=2, column=0, columnspan=2, sticky="w"
        )
        tk.Label(frame, text="Manual balance override").grid(row=3, column=0, sticky="w")
        self.manual_balance_override_var = tk.StringVar(value="")
        tk.Entry(frame, textvariable=self.manual_balance_override_var, width=18).grid(row=3, column=1, sticky="w")
        self.component_variation_allowed_vars: dict[str, tk.BooleanVar] = {}
        self.component_custom_variation_pct_vars: dict[str, tk.StringVar] = {}
        self.variation_components_frame = tk.Frame(frame)
        self.variation_components_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))

        self.objective_fields = [
            ("use_constrained_mixture_design", "Use constrained mixture design"),
            ("reduce_api_excipient_correlation", "Reduce API-excipient correlation"),
            ("improve_api_specificity", "Improve API specificity"),
            ("use_d_optimal_or_approximate_d_optimal_selection", "Use D-optimal or approximate D-optimal selection"),
            ("include_target_strengths_in_calibration_design", "Include target strengths in calibration design"),
            ("allow_reuse_across_strength_models", "Allow reuse across strength-specific models"),
            ("reduce_redundant_overlap_between_strengths", "Reduce redundant overlap between strengths"),
            ("minimize_api_material_consumption", "Minimize API material consumption"),
            ("prefer_fewer_calibration_batches", "Prefer fewer calibration batches"),
            ("allow_non_nominal_excipient_ratios", "Allow non-nominal excipient ratios"),
        ]
        self.objective_vars: dict[str, tk.BooleanVar] = {}
        start_row = 5
        for i, (key, label) in enumerate(self.objective_fields):
            var = tk.BooleanVar(value=False)
            self.objective_vars[key] = var
            tk.Checkbutton(frame, text=label, variable=var).grid(row=start_row + i, column=0, columnspan=3, sticky="w")

    def _build_batch_section(self, frame: tk.LabelFrame) -> None:
        self.batch_field_specs = [
            ("desired_batches", "Desired batches", "int"),
            ("min_batches", "Minimum batches", "int"),
            ("max_batches", "Maximum batches", "int"),
            ("default_batch_size", "Default batch size", "float"),
            ("batch_size_unit", "Batch size unit (g/kg)", "str"),
            ("allow_different_batch_sizes", "Allow different batch sizes", "bool"),
            ("min_batch_size", "Minimum batch size", "float"),
            ("max_batch_size", "Maximum batch size", "float"),
            ("include_replicates", "Include replicates", "bool"),
            ("replicate_count", "Replicate count", "int"),
            ("replicate_type", "Replicate type", "str"),
            ("seed", "Deterministic seed", "int"),
        ]

        self.batch_vars: dict[str, tk.Variable] = {}
        for i, (key, label, kind) in enumerate(self.batch_field_specs):
            tk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=(0, 6), pady=1)
            if kind == "bool":
                var = tk.BooleanVar(value=False)
                self.batch_vars[key] = var
                tk.Checkbutton(frame, variable=var).grid(row=i, column=1, sticky="w")
            else:
                var = tk.StringVar(value="")
                self.batch_vars[key] = var
                tk.Entry(frame, textvariable=var, width=16).grid(row=i, column=1, sticky="w")

    def _build_manual_section(self, frame: tk.LabelFrame) -> None:
        wrapper = tk.Frame(frame)
        wrapper.pack(fill="both", expand=True)
        wrapper.grid_columnconfigure(1, weight=1)

        left = tk.Frame(wrapper)
        left.grid(row=0, column=0, sticky="ns")

        self.manual_listbox = tk.Listbox(left, height=6, width=28)
        self.manual_listbox.pack(side=tk.TOP, fill="y")
        self.manual_listbox.bind("<<ListboxSelect>>", self._on_manual_select)

        btn_row = tk.Frame(left)
        btn_row.pack(fill="x", pady=(4, 0))
        tk.Button(btn_row, text="Add", command=self._manual_add).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="Update", command=self._manual_update_selected).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="Delete", command=self._manual_delete_selected).pack(side=tk.LEFT, padx=2)

        right = tk.Frame(wrapper)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.manual_batch_name_var = tk.StringVar(value="")
        self.manual_api_pure_var = tk.StringVar(value="")
        self.manual_locked_var = tk.BooleanVar(value=False)
        self.manual_forced_var = tk.BooleanVar(value=False)
        self.manual_reusable_var = tk.BooleanVar(value=True)

        tk.Label(right, text="Batch name").grid(row=0, column=0, sticky="w")
        tk.Entry(right, textvariable=self.manual_batch_name_var, width=24).grid(row=0, column=1, sticky="w")

        tk.Label(right, text="API pure mg/g").grid(row=1, column=0, sticky="w")
        tk.Entry(right, textvariable=self.manual_api_pure_var, width=12).grid(row=1, column=1, sticky="w")

        tk.Checkbutton(right, text="Locked", variable=self.manual_locked_var).grid(row=2, column=0, sticky="w")
        tk.Checkbutton(right, text="Forced", variable=self.manual_forced_var).grid(row=2, column=1, sticky="w")
        tk.Checkbutton(right, text="Reusable", variable=self.manual_reusable_var).grid(row=2, column=2, sticky="w")

        self.manual_component_vars: list[tk.StringVar] = []
        self.manual_components_frame = tk.Frame(right)
        self.manual_components_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def _build_output_panels(self, parent: tk.Frame) -> None:
        output_card = tk.Frame(
            parent,
            bg=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        output_card.grid(row=2, column=0, sticky="nsew")
        output_card.grid_rowconfigure(1, weight=1)
        output_card.grid_columnconfigure(0, weight=1)

        tk.Label(
            output_card,
            text="Outputs",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        style = ttk.Style(self.root)
        style.theme_use(style.theme_use())
        style.configure("V3.TNotebook", background=COLORS["panel"], borderwidth=0)
        style.configure("V3.TNotebook.Tab", padding=(10, 6))

        notebook = ttk.Notebook(output_card, style="V3.TNotebook")
        notebook.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self.design_tab = tk.Text(notebook, wrap="none")
        self.diagnostics_tab = tk.Text(notebook, wrap="none")
        self.plots_tab = tk.Frame(notebook)
        self.export_tab = tk.Text(notebook, wrap="word")

        notebook.add(self.design_tab, text="Design table")
        notebook.add(self.diagnostics_tab, text="Diagnostics")
        notebook.add(self.plots_tab, text="Plots")
        notebook.add(self.export_tab, text="Export/run folder")

        self._build_plots_tab_widgets()

    def _build_plots_tab_widgets(self) -> None:
        self.plots_tab.grid_rowconfigure(0, weight=1)
        self.plots_tab.grid_columnconfigure(1, weight=1)

        left = tk.Frame(self.plots_tab)
        left.grid(row=0, column=0, sticky="nsw", padx=(4, 8), pady=4)
        tk.Label(left, text="Generated plot files").pack(anchor="w")

        self.plot_listbox = tk.Listbox(left, width=48, height=28)
        self.plot_listbox.pack(fill="both", expand=True)
        self.plot_listbox.bind("<<ListboxSelect>>", self._on_plot_selected)

        right = tk.Frame(self.plots_tab, bd=1, relief=tk.SUNKEN)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 4), pady=4)
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.plot_preview_label = tk.Label(
            right,
            text="Generate and export a design run to preview plots here.",
            anchor="center",
            justify="center",
        )
        self.plot_preview_label.grid(row=0, column=0, sticky="nsew")
        self._plot_file_paths: list[Path] = []
        self._plot_preview_image: tk.PhotoImage | None = None

    def _build_action_bar(self) -> None:
        action_bar = tk.Frame(
            self.root,
            bg=COLORS["panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        action_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        action_bar.grid_columnconfigure(10, weight=1)

        def _btn(label: str, cmd: object, *, primary: bool = False, col: int = 0) -> None:
            tk.Button(
                action_bar,
                text=label,
                command=cmd,
                bg=COLORS["accent"] if primary else COLORS["primary"],
                fg=COLORS["text"] if primary else "#FFFFFF",
                activebackground="#D77A1E" if primary else "#0D2A48",
                activeforeground=COLORS["text"] if primary else "#FFFFFF",
                relief=tk.FLAT,
                padx=10,
                pady=7,
                font=("Segoe UI", 10, "bold" if primary else "normal"),
            ).grid(row=0, column=col, sticky="w", padx=(8 if col == 0 else 6, 0), pady=8)

        _btn("Load example", self.load_example, col=0)
        _btn("Generate design", self.generate_design, primary=True, col=1)
        _btn("Recalculate diagnostics", self.recalculate_diagnostics, col=2)
        _btn("Export design run", self.export_design, col=3)
        _btn("Open output folder", self.open_output_folder, col=4)

        self.status_pill_var = tk.StringVar(value="Ready")
        self.status_text_var = tk.StringVar(value="Edit inputs and click Generate design.")
        self.status_pill = tk.Label(
            action_bar,
            textvariable=self.status_pill_var,
            bg=STATUS_COLORS["info"],
            fg="#FFFFFF",
            padx=10,
            pady=5,
            font=("Segoe UI", 9, "bold"),
        )
        self.status_pill.grid(row=0, column=5, sticky="w", padx=(10, 0))
        tk.Label(
            action_bar,
            textvariable=self.status_text_var,
            bg=COLORS["panel"],
            fg=COLORS["secondary_text"],
            anchor="w",
        ).grid(row=0, column=10, sticky="ew", padx=12)

    def _load_state_from_config(self, config: RunConfig) -> None:
        component_names = [component.name for component in config.components]

        self.component_count_var.set(str(len(config.components)))
        self.api_content_var.set(str(config.api_content_mg_mg))
        self.component_name_vars = [tk.StringVar(value=name) for name in component_names]
        self.component_type_vars = [tk.StringVar(value=component.component_type) for component in config.components]

        api_index = next(i for i, component in enumerate(config.components) if component.is_api)
        balance_index = next(i for i, component in enumerate(config.components) if component.is_balance)
        self.component_api_index_var.set(api_index)
        self.component_balance_index_var.set(balance_index)
        self._render_component_rows()

        self.strength_count_var.set(str(len(config.product_strengths)))
        self.strength_rows = []
        for strength in config.product_strengths:
            values = [strength.component_targets_mg_g.get(name, 0.0) for name in component_names]
            self.strength_rows.append(self._new_strength_row(name=strength.name, targets=values))
        self._render_strength_rows()
        self.api_range_mode_var.set(config.api_calibration_range_settings.mode)
        self.api_range_lower_var.set(str(config.api_calibration_range_settings.lower))
        self.api_range_upper_var.set(str(config.api_calibration_range_settings.upper))
        self.api_range_levels_var.set(str(config.api_calibration_range_settings.api_levels))
        self.include_target_api_level_var.set(bool(config.api_calibration_range_settings.include_target_api_level))
        self.apply_same_api_range_var.set(bool(config.api_calibration_range_settings.apply_same_api_range_to_all_strengths))

        self.variation_preset_var.set(config.excipient_variation_settings.preset)
        self.keep_glidant_fixed_var.set(bool(config.excipient_variation_settings.keep_glidant_lubricant_fixed))
        self.auto_select_balance_var.set(bool(config.excipient_variation_settings.auto_select_balance_component))
        self.manual_balance_override_var.set(config.excipient_variation_settings.manual_balance_component_override or "")

        objective_values = config.objective_settings.model_dump()
        for key, _label in self.objective_fields:
            self.objective_vars[key].set(bool(objective_values[key]))

        batch_values = config.batch_settings.model_dump()
        for key, _label, kind in self.batch_field_specs:
            if key == "seed":
                self.batch_vars[key].set(str(config.seed))
                continue
            value = batch_values[key]
            if kind == "bool":
                self.batch_vars[key].set(bool(value))
            else:
                self.batch_vars[key].set(str(value))

        non_api_non_balance_names = [
            name
            for i, name in enumerate(component_names)
            if i != self.component_api_index_var.get() and i != self.component_balance_index_var.get()
        ]
        self.manual_rows = []
        for batch in config.manual_batches:
            vector = [float(batch.component_mg_g.get(name, 0.0)) for name in non_api_non_balance_names]
            self.manual_rows.append(
                ManualBatchInputRow(
                    batch_name=batch.batch_name,
                    api_pure_mg_g=batch.api_pure_mg_g,
                    non_api_non_balance_mg_g=vector,
                    locked=batch.locked,
                    forced=batch.forced,
                    reusable_across_strengths=batch.reusable_across_strengths,
                )
            )
        self._render_manual_components_inputs()
        self._refresh_manual_listbox()
        self._render_component_variation_controls(
            config.excipient_variation_settings.allow_variation_by_component,
            config.excipient_variation_settings.custom_variation_pct_by_component,
        )

    def _apply_component_count(self) -> None:
        try:
            desired = int(self.component_count_var.get())
            if desired < 2:
                raise ValueError
        except ValueError:
            messagebox.showerror("Component setup", "Number of components must be an integer >= 2.")
            return

        allow_seed = {name: var.get() for name, var in self.component_variation_allowed_vars.items()}
        custom_seed = {
            name: float(var.get()) if var.get().strip() else 5.0
            for name, var in self.component_custom_variation_pct_vars.items()
        }
        existing_names = [var.get() for var in self.component_name_vars]
        existing_types = [var.get() for var in self.component_type_vars]
        while len(existing_names) < desired:
            existing_names.append(f"Component{len(existing_names) + 1}")
            existing_types.append("major_excipient")
        existing_names = existing_names[:desired]
        existing_types = existing_types[:desired]

        self.component_name_vars = [tk.StringVar(value=name) for name in existing_names]
        self.component_type_vars = [tk.StringVar(value=ctype) for ctype in existing_types]
        self.component_api_index_var.set(min(self.component_api_index_var.get(), desired - 1))
        self.component_balance_index_var.set(min(self.component_balance_index_var.get(), desired - 1))
        if self.component_api_index_var.get() == self.component_balance_index_var.get():
            self.component_balance_index_var.set((self.component_api_index_var.get() + 1) % desired)

        self._render_component_rows()
        self._resize_strength_component_vectors()
        self._resize_manual_vectors_for_components()
        self._render_component_variation_controls(allow_seed, custom_seed)

    def _apply_strength_count(self) -> None:
        try:
            desired = int(self.strength_count_var.get())
            if desired < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Product strengths", "Number of strengths must be an integer >= 1.")
            return

        component_count = len(self.component_name_vars)
        while len(self.strength_rows) < desired:
            if self.strength_rows:
                template = self._strength_row_targets(self.strength_rows[-1])
            else:
                template = self._default_strength_targets(component_count)
            self.strength_rows.append(
                self._new_strength_row(
                    name=f"Strength {len(self.strength_rows) + 1}",
                    targets=template,
                )
            )
        self.strength_rows = self.strength_rows[:desired]
        self._resize_strength_component_vectors()

        self._render_strength_rows()

    def _resize_strength_component_vectors(self) -> None:
        component_count = len(self.component_name_vars)
        defaults = self._default_strength_targets(component_count)
        for row in self.strength_rows:
            target_vars: list[tk.StringVar] = row["target_vars"]  # type: ignore[assignment]
            while len(target_vars) < component_count:
                target_vars.append(tk.StringVar(value=str(defaults[len(target_vars)])))
            del target_vars[component_count:]
            self._rebalance_strength_row(row)
        self._render_strength_rows()

    def _resize_manual_vectors_for_components(self) -> None:
        count = len(self._non_api_non_balance_names())
        for row in self.manual_rows:
            while len(row.non_api_non_balance_mg_g) < count:
                row.non_api_non_balance_mg_g.append(0.0)
            row.non_api_non_balance_mg_g = row.non_api_non_balance_mg_g[:count]
        self._render_manual_components_inputs()
        self._refresh_manual_listbox()

    def _refresh_dependent_sections(self) -> None:
        allow_seed = {name: var.get() for name, var in self.component_variation_allowed_vars.items()}
        custom_seed = {
            name: float(var.get()) if var.get().strip() else 5.0
            for name, var in self.component_custom_variation_pct_vars.items()
        }
        for row in self.strength_rows:
            self._rebalance_strength_row(row)
        self._auto_select_balance_index()
        self._render_strength_rows()
        self._resize_manual_vectors_for_components()
        self._render_component_variation_controls(allow_seed, custom_seed)

    def _render_component_rows(self) -> None:
        for widget in self.component_rows_frame.winfo_children():
            widget.destroy()

        headers = ["#", "Name", "Type", "API", "Balance"]
        for j, text in enumerate(headers):
            tk.Label(self.component_rows_frame, text=text, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=j, sticky="w", padx=2
            )

        while len(self.component_type_vars) < len(self.component_name_vars):
            self.component_type_vars.append(tk.StringVar(value="major_excipient"))
        self.component_type_vars = self.component_type_vars[: len(self.component_name_vars)]

        for i, name_var in enumerate(self.component_name_vars):
            tk.Label(self.component_rows_frame, text=str(i + 1)).grid(row=i + 1, column=0, sticky="w", padx=2)
            tk.Entry(self.component_rows_frame, textvariable=name_var, width=16).grid(row=i + 1, column=1, sticky="w", padx=2)
            ttk.Combobox(
                self.component_rows_frame,
                textvariable=self.component_type_vars[i],
                values=["api", "major_excipient", "minor_excipient", "glidant_lubricant"],
                state="readonly",
                width=16,
            ).grid(row=i + 1, column=2, sticky="w", padx=2)
            tk.Radiobutton(
                self.component_rows_frame, variable=self.component_api_index_var, value=i, command=self._refresh_dependent_sections
            ).grid(
                row=i + 1, column=3, padx=2
            )
            tk.Radiobutton(
                self.component_rows_frame, variable=self.component_balance_index_var, value=i, command=self._refresh_dependent_sections
            ).grid(
                row=i + 1, column=4, padx=2
            )

    def _render_strength_rows(self) -> None:
        for widget in self.strength_rows_frame.winfo_children():
            widget.destroy()

        component_names = [var.get().strip() or f"Component{i + 1}" for i, var in enumerate(self.component_name_vars)]
        tk.Label(self.strength_rows_frame, text="Strength", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=2)
        for i, component_name in enumerate(component_names):
            tk.Label(self.strength_rows_frame, text=component_name, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=i + 1, sticky="w", padx=2
            )
        metrics_col = len(component_names) + 1
        tk.Label(self.strength_rows_frame, text="API DS mg/g", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=metrics_col, sticky="w", padx=6
        )
        tk.Label(self.strength_rows_frame, text="Weighed total mg/g", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=metrics_col + 1, sticky="w", padx=6
        )
        tk.Label(self.strength_rows_frame, text="Status", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=metrics_col + 2, sticky="w", padx=6
        )

        for row_index, row in enumerate(self.strength_rows, start=1):
            name_var: tk.StringVar = row["name_var"]  # type: ignore[assignment]
            target_vars: list[tk.StringVar] = row["target_vars"]  # type: ignore[assignment]
            api_ds_var: tk.StringVar = row["api_ds_total_var"]  # type: ignore[assignment]
            total_var: tk.StringVar = row["weighed_total_var"]  # type: ignore[assignment]
            status_var: tk.StringVar = row["status_var"]  # type: ignore[assignment]
            tk.Entry(self.strength_rows_frame, textvariable=name_var, width=12).grid(row=row_index, column=0, sticky="w", padx=2)
            for col_index, target_var in enumerate(target_vars, start=1):
                entry = tk.Entry(self.strength_rows_frame, textvariable=target_var, width=9)
                entry.grid(
                    row=row_index, column=col_index, sticky="w", padx=2
                )
                entry.bind("<KeyRelease>", self._on_strength_value_edited)
            tk.Label(self.strength_rows_frame, textvariable=api_ds_var).grid(
                row=row_index, column=metrics_col, sticky="w", padx=6
            )
            tk.Label(self.strength_rows_frame, textvariable=total_var).grid(
                row=row_index, column=metrics_col + 1, sticky="w", padx=6
            )
            tk.Label(self.strength_rows_frame, textvariable=status_var).grid(
                row=row_index, column=metrics_col + 2, sticky="w", padx=6
            )
        self._update_strength_totals()

    def _new_strength_row(self, name: str, targets: list[float]) -> dict[str, object]:
        return {
            "name_var": tk.StringVar(value=name),
            "target_vars": [tk.StringVar(value=str(value)) for value in targets],
            "api_ds_total_var": tk.StringVar(value=""),
            "weighed_total_var": tk.StringVar(value=""),
            "status_var": tk.StringVar(value=""),
        }

    def _strength_row_targets(self, row: dict[str, object]) -> list[float]:
        target_vars: list[tk.StringVar] = row["target_vars"]  # type: ignore[assignment]
        targets: list[float] = []
        for var in target_vars:
            try:
                targets.append(float(var.get()))
            except ValueError:
                targets.append(0.0)
        return targets

    def _default_strength_targets(self, component_count: int) -> list[float]:
        defaults = [0.0] * component_count
        if component_count == 0:
            return defaults

        api_index = self.component_api_index_var.get()
        balance_index = self.component_balance_index_var.get()
        if 0 <= api_index < component_count:
            defaults[api_index] = 10.0
        if 0 <= balance_index < component_count and balance_index != api_index:
            defaults[balance_index] = self._required_balance_mg_g(defaults)
        return defaults

    def _required_balance_mg_g(self, targets: list[float]) -> float:
        api_index = self.component_api_index_var.get()
        balance_index = self.component_balance_index_var.get()
        if api_index < 0 or balance_index < 0:
            return 0.0
        if api_index >= len(targets) or balance_index >= len(targets):
            return 0.0

        api_pure = float(targets[api_index])
        try:
            api_content = float(self.api_content_var.get())
        except ValueError:
            return 0.0
        if api_content <= 0:
            return 0.0
        api_ds = api_pure / api_content
        other_non_api_total = sum(float(value) for idx, value in enumerate(targets) if idx not in {api_index, balance_index})
        return float(STRENGTH_TOTAL_TARGET_MG_G - api_ds - other_non_api_total)

    def _rebalance_strength_row(self, row: dict[str, object]) -> None:
        target_vars: list[tk.StringVar] = row["target_vars"]  # type: ignore[assignment]
        targets = self._strength_row_targets(row)
        balance_index = self.component_balance_index_var.get()
        if balance_index < 0 or balance_index >= len(target_vars):
            return
        if balance_index == self.component_api_index_var.get():
            return
        target_vars[balance_index].set(str(self._required_balance_mg_g(targets)))

    def _on_strength_value_edited(self, _event: tk.Event[tk.Widget]) -> None:
        self._update_strength_totals()

    def _update_strength_totals(self) -> None:
        if not self.strength_rows:
            return
        try:
            api_content = float(self.api_content_var.get())
        except ValueError:
            for row in self.strength_rows:
                row["api_ds_total_var"].set("n/a")  # type: ignore[index]
                row["weighed_total_var"].set("n/a")  # type: ignore[index]
                row["status_var"].set("FAIL (invalid API content)")  # type: ignore[index]
            return

        components = [
            ComponentInputRow(
                name=(var.get().strip() or f"Component{i + 1}"),
                is_api=(i == self.component_api_index_var.get()),
                is_balance=(i == self.component_balance_index_var.get()),
                component_type=self.component_type_vars[i].get(),
            )
            for i, var in enumerate(self.component_name_vars)
        ]
        strengths: list[StrengthInputRow] = []
        for idx, row in enumerate(self.strength_rows, start=1):
            name_var: tk.StringVar = row["name_var"]  # type: ignore[assignment]
            strengths.append(
                StrengthInputRow(
                    name=name_var.get().strip() or f"Strength {idx}",
                    targets_mg_g=self._strength_row_targets(row),
                )
            )

        try:
            validations = evaluate_strength_totals(
                components=components,
                strengths=strengths,
                api_content_mg_mg=api_content,
                tolerance_mg_g=STRENGTH_TOTAL_TOLERANCE_MG_G,
            )
        except Exception:
            for row in self.strength_rows:
                row["api_ds_total_var"].set("n/a")  # type: ignore[index]
                row["weighed_total_var"].set("n/a")  # type: ignore[index]
                row["status_var"].set("FAIL")  # type: ignore[index]
            return

        for row, validation in zip(self.strength_rows, validations, strict=True):
            row["api_ds_total_var"].set(f"{validation.api_ds_total_mg_g:.6f}")  # type: ignore[index]
            row["weighed_total_var"].set(f"{validation.weighed_total_mg_g:.6f}")  # type: ignore[index]
            if validation.is_valid:
                row["status_var"].set("PASS")  # type: ignore[index]
            else:
                row["status_var"].set(f"FAIL ({validation.delta_from_target_mg_g:+.6f} mg/g)")  # type: ignore[index]

    def _render_component_variation_controls(
        self,
        allow_variation_seed: dict[str, bool],
        custom_pct_seed: dict[str, float],
    ) -> None:
        for widget in self.variation_components_frame.winfo_children():
            widget.destroy()
        self.component_variation_allowed_vars = {}
        self.component_custom_variation_pct_vars = {}

        defaults = default_allow_variation_map(
            [
                ComponentSpec(
                    name=(name_var.get().strip() or f"Component{i + 1}"),
                    is_api=(i == self.component_api_index_var.get()),
                    is_balance=False,
                    component_type=self.component_type_vars[i].get(),  # type: ignore[arg-type]
                )
                for i, name_var in enumerate(self.component_name_vars)
            ]
        )
        row_idx = 0
        for i, name_var in enumerate(self.component_name_vars):
            name = name_var.get().strip() or f"Component{i + 1}"
            is_api = i == self.component_api_index_var.get()
            if is_api:
                continue
            allowed_default = allow_variation_seed.get(name, defaults.get(name, True))
            allow_var = tk.BooleanVar(value=allowed_default)
            custom_pct = tk.StringVar(value=str(custom_pct_seed.get(name, 5.0)))
            self.component_variation_allowed_vars[name] = allow_var
            self.component_custom_variation_pct_vars[name] = custom_pct
            tk.Checkbutton(self.variation_components_frame, text=f"Allow {name} variation", variable=allow_var).grid(
                row=row_idx, column=0, sticky="w"
            )
            tk.Entry(self.variation_components_frame, textvariable=custom_pct, width=7).grid(
                row=row_idx, column=1, sticky="w", padx=(6, 0)
            )
            tk.Label(self.variation_components_frame, text="% (custom)").grid(row=row_idx, column=2, sticky="w", padx=(2, 0))
            row_idx += 1

    def _auto_select_balance_index(self) -> None:
        if not getattr(self, "auto_select_balance_var", tk.BooleanVar(value=True)).get():
            return
        if not self.component_name_vars or not self.strength_rows:
            return
        try:
            components = [
                ComponentSpec(
                    name=(name_var.get().strip() or f"Component{i + 1}"),
                    is_api=(i == self.component_api_index_var.get()),
                    is_balance=False,
                    component_type=self.component_type_vars[i].get(),  # type: ignore[arg-type]
                )
                for i, name_var in enumerate(self.component_name_vars)
            ]
            strength = ProductStrength(
                name="auto",
                component_targets_mg_g={
                    components[i].name: self._strength_row_targets(self.strength_rows[0])[i]
                    for i in range(len(components))
                },
            )
            chosen = auto_select_balance_component(
                components=components,
                strength=strength,
                allow_variation_by_component={k: v.get() for k, v in self.component_variation_allowed_vars.items()}
                if self.component_variation_allowed_vars
                else default_allow_variation_map(components),
                keep_glidant_lubricant_fixed=bool(self.keep_glidant_fixed_var.get()),
                manual_override=(
                    self.manual_balance_override_var.get().strip() if not self.auto_select_balance_var.get() else None
                ),
            )
            for i, component in enumerate(components):
                if component.name == chosen:
                    self.component_balance_index_var.set(i)
                    break
        except Exception:
            return

    def _render_manual_components_inputs(self) -> None:
        for widget in self.manual_components_frame.winfo_children():
            widget.destroy()

        self.manual_component_vars = []
        names = self._non_api_non_balance_names()
        for i, name in enumerate(names):
            tk.Label(self.manual_components_frame, text=f"{name} mg/g").grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value="0")
            self.manual_component_vars.append(var)
            tk.Entry(self.manual_components_frame, textvariable=var, width=12).grid(row=i, column=1, sticky="w", padx=(4, 0))

    def _non_api_non_balance_names(self) -> list[str]:
        names = [var.get().strip() or f"Component{i + 1}" for i, var in enumerate(self.component_name_vars)]
        api_idx = self.component_api_index_var.get()
        balance_idx = self.component_balance_index_var.get()
        return [name for i, name in enumerate(names) if i not in {api_idx, balance_idx}]

    def _refresh_manual_listbox(self) -> None:
        self.manual_listbox.delete(0, tk.END)
        for row in self.manual_rows:
            tags = []
            if row.locked:
                tags.append("locked")
            if row.forced:
                tags.append("forced")
            suffix = f" [{' '.join(tags)}]" if tags else ""
            self.manual_listbox.insert(tk.END, f"{row.batch_name}{suffix}")

    def _manual_add(self) -> None:
        try:
            row = self._collect_manual_form_row()
        except ValueError as exc:
            messagebox.showerror("Manual design editing", str(exc))
            return
        self.manual_rows.append(row)
        self._refresh_manual_listbox()

    def _manual_update_selected(self) -> None:
        selected = self.manual_listbox.curselection()
        if not selected:
            messagebox.showinfo("Manual design editing", "Select a manual batch to update.")
            return
        index = int(selected[0])
        try:
            row = self._collect_manual_form_row()
        except ValueError as exc:
            messagebox.showerror("Manual design editing", str(exc))
            return
        self.manual_rows[index] = row
        self._refresh_manual_listbox()

    def _manual_delete_selected(self) -> None:
        selected = self.manual_listbox.curselection()
        if not selected:
            return
        index = int(selected[0])
        del self.manual_rows[index]
        self._refresh_manual_listbox()

    def _on_manual_select(self, _event: tk.Event[tk.Widget]) -> None:
        selected = self.manual_listbox.curselection()
        if not selected:
            return
        row = self.manual_rows[int(selected[0])]
        self.manual_batch_name_var.set(row.batch_name)
        self.manual_api_pure_var.set(str(row.api_pure_mg_g))
        self.manual_locked_var.set(bool(row.locked))
        self.manual_forced_var.set(bool(row.forced))
        self.manual_reusable_var.set(bool(row.reusable_across_strengths))

        if len(row.non_api_non_balance_mg_g) != len(self.manual_component_vars):
            self._resize_manual_vectors_for_components()
        for var, value in zip(self.manual_component_vars, row.non_api_non_balance_mg_g, strict=True):
            var.set(str(value))

    def _collect_manual_form_row(self) -> ManualBatchInputRow:
        name = self.manual_batch_name_var.get().strip()
        if not name:
            raise ValueError("Manual batch name is required")

        try:
            api_pure = float(self.manual_api_pure_var.get())
        except ValueError as exc:
            raise ValueError("Manual API pure mg/g must be numeric") from exc

        vector: list[float] = []
        for var in self.manual_component_vars:
            try:
                vector.append(float(var.get()))
            except ValueError as exc:
                raise ValueError("Manual component mg/g values must be numeric") from exc

        return ManualBatchInputRow(
            batch_name=name,
            api_pure_mg_g=api_pure,
            non_api_non_balance_mg_g=vector,
            locked=bool(self.manual_locked_var.get()),
            forced=bool(self.manual_forced_var.get()),
            reusable_across_strengths=bool(self.manual_reusable_var.get()),
        )

    def _build_input_state(self) -> AppInputState:
        component_count = len(self.component_name_vars)
        if component_count < 2:
            raise ValueError("At least two components are required")
        api_index = self.component_api_index_var.get()
        if api_index < 0 or api_index >= component_count:
            raise ValueError("Select one API component before generating a constrained mixture design.")

        if self.auto_select_balance_var.get():
            self._auto_select_balance_index()
        balance_index = self.component_balance_index_var.get()
        if balance_index < 0 or balance_index >= component_count:
            raise ValueError("Select one calculated balance component before generating a constrained mixture design.")
        if api_index == balance_index:
            raise ValueError("API component and calculated balance component must be different.")

        components = [
            ComponentInputRow(
                name=(var.get().strip() or f"Component{i + 1}"),
                is_api=(i == api_index),
                is_balance=(i == balance_index),
                component_type=self.component_type_vars[i].get(),
            )
            for i, var in enumerate(self.component_name_vars)
        ]

        api_content = float(self.api_content_var.get())

        strengths: list[StrengthInputRow] = []
        for row in self.strength_rows:
            name_var: tk.StringVar = row["name_var"]  # type: ignore[assignment]
            target_vars: list[tk.StringVar] = row["target_vars"]  # type: ignore[assignment]
            targets = [float(var.get()) for var in target_vars]
            strengths.append(StrengthInputRow(name=name_var.get(), targets_mg_g=targets))

        preset_fraction_map = {
            "conservative": 0.025,
            "standard": 0.05,
            "aggressive": 0.10,
        }
        constraints: list[ConstraintInputRow] = []
        for i, component in enumerate(components):
            nominal_values = [strength.targets_mg_g[i] for strength in strengths]
            nominal_center = float(sum(nominal_values) / len(nominal_values)) if nominal_values else 0.0
            if i == api_index:
                if self.api_range_mode_var.get() == "percent_of_target":
                    min_v = min(v * (float(self.api_range_lower_var.get()) / 100.0) for v in nominal_values)
                    max_v = max(v * (float(self.api_range_upper_var.get()) / 100.0) for v in nominal_values)
                else:
                    min_v = float(self.api_range_lower_var.get())
                    max_v = float(self.api_range_upper_var.get())
                constraints.append(ConstraintInputRow(min_mg_g=min_v, max_mg_g=max_v, preferred_levels=int(self.api_range_levels_var.get())))
                continue

            if i == balance_index:
                constraints.append(ConstraintInputRow(min_mg_g=0.0, max_mg_g=1000.0, preferred_levels=1))
                continue

            allow_var = self.component_variation_allowed_vars.get(component.name)
            is_flexible = bool(allow_var.get()) if allow_var is not None else True
            if component.component_type == "glidant_lubricant" and self.keep_glidant_fixed_var.get():
                is_flexible = False
            if not is_flexible:
                constraints.append(ConstraintInputRow(min_mg_g=nominal_center, max_mg_g=nominal_center, preferred_levels=1))
                continue

            if self.variation_preset_var.get() == "custom":
                pct_var = float(self.component_custom_variation_pct_vars.get(component.name, tk.StringVar(value="5")).get())
                frac = max(0.0, pct_var / 100.0)
            else:
                frac = preset_fraction_map[self.variation_preset_var.get()]
            min_v = max(0.0, nominal_center * (1.0 - frac))
            max_v = nominal_center * (1.0 + frac)
            constraints.append(ConstraintInputRow(min_mg_g=min_v, max_mg_g=max_v, preferred_levels=3))

        objective_settings = DesignObjectiveSettings(**{key: bool(var.get()) for key, var in self.objective_vars.items()})
        api_range_settings = ApiCalibrationRangeSettings(
            mode=self.api_range_mode_var.get(),
            lower=float(self.api_range_lower_var.get()),
            upper=float(self.api_range_upper_var.get()),
            api_levels=int(self.api_range_levels_var.get()),
            include_target_api_level=bool(self.include_target_api_level_var.get()),
            apply_same_api_range_to_all_strengths=bool(self.apply_same_api_range_var.get()),
        )
        excipient_variation_settings = ExcipientVariationSettings(
            preset=self.variation_preset_var.get(),
            allow_variation_by_component={name: bool(var.get()) for name, var in self.component_variation_allowed_vars.items()},
            keep_glidant_lubricant_fixed=bool(self.keep_glidant_fixed_var.get()),
            auto_select_balance_component=bool(self.auto_select_balance_var.get()),
            manual_balance_component_override=self.manual_balance_override_var.get().strip() or None,
            custom_variation_pct_by_component={
                name: float(var.get()) for name, var in self.component_custom_variation_pct_vars.items()
            },
        )

        batch_settings = BatchSettings(
            desired_batches=int(str(self.batch_vars["desired_batches"].get())),
            min_batches=int(str(self.batch_vars["min_batches"].get())),
            max_batches=int(str(self.batch_vars["max_batches"].get())),
            default_batch_size=float(str(self.batch_vars["default_batch_size"].get())),
            batch_size_unit=str(self.batch_vars["batch_size_unit"].get()),
            allow_different_batch_sizes=bool(self.batch_vars["allow_different_batch_sizes"].get()),
            min_batch_size=float(str(self.batch_vars["min_batch_size"].get())),
            max_batch_size=float(str(self.batch_vars["max_batch_size"].get())),
            include_replicates=bool(self.batch_vars["include_replicates"].get()),
            replicate_count=int(str(self.batch_vars["replicate_count"].get())),
            replicate_type=str(self.batch_vars["replicate_type"].get()),
        )

        seed = int(str(self.batch_vars["seed"].get()))

        return AppInputState(
            components=components,
            api_content_mg_mg=api_content,
            strengths=strengths,
            constraints=constraints,
            objective_settings=objective_settings,
            batch_settings=batch_settings,
            api_calibration_range_settings=api_range_settings,
            excipient_variation_settings=excipient_variation_settings,
            manual_batches=list(self.manual_rows),
            seed=seed,
            tolerance_mg_g=self.config.tolerance_mg_g,
        )

    def _sync_config_from_inputs(self) -> None:
        state = self._build_input_state()
        self.config = build_run_config_from_app_input_state(state)

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        widget.config(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.config(state="disabled")

    def _set_status(self, pill_text: str, detail: str, level: str = "info") -> None:
        if not hasattr(self, "status_pill"):
            return
        self.status_pill_var.set(pill_text)
        self.status_text_var.set(detail)
        self.status_pill.configure(bg=STATUS_COLORS.get(level, STATUS_COLORS["info"]))

    def _set_plots_tab_message(self, message: str) -> None:
        self.plot_listbox.delete(0, tk.END)
        self._plot_file_paths = []
        self._plot_preview_image = None
        self.plot_preview_label.config(text=message, image="")

    def _refresh_plot_previews_from_output_folder(self) -> None:
        if self.last_output_folder is None:
            self._set_plots_tab_message("Generate and export a design run to preview plots here.")
            return

        standard_plot_files = sorted(self.last_output_folder.glob("*.png"))
        pairwise_dir = self.last_output_folder / "plots" / PAIRWISE_DIRNAME
        pairwise_plot_files = sorted(pairwise_dir.glob("*.png")) if pairwise_dir.exists() else []
        all_plot_files = standard_plot_files + pairwise_plot_files

        if not all_plot_files:
            self._set_plots_tab_message("No plot files found in the last exported run folder.")
            return

        self.plot_listbox.delete(0, tk.END)
        self._plot_file_paths = all_plot_files
        for path in all_plot_files:
            rel = path.relative_to(self.last_output_folder)
            self.plot_listbox.insert(tk.END, str(rel))

        self.plot_listbox.selection_set(0)
        self._on_plot_selected(None)

    def _on_plot_selected(self, _event: tk.Event[tk.Widget] | None) -> None:
        selected = self.plot_listbox.curselection()
        if not selected:
            return
        idx = int(selected[0])
        if idx < 0 or idx >= len(self._plot_file_paths):
            return

        path = self._plot_file_paths[idx]
        try:
            photo = tk.PhotoImage(file=str(path))
        except Exception:
            self._plot_preview_image = None
            self.plot_preview_label.config(
                text=f"Preview unavailable for:\n{path.name}\n\nOpen the output folder to view full image.",
                image="",
            )
            return

        self._plot_preview_image = photo
        self.plot_preview_label.config(image=self._plot_preview_image, text="")

    def load_example(self) -> None:
        self.config = build_example_run_config()
        self.pipeline_result = None
        self.last_output_folder = None
        self._load_state_from_config(self.config)
        self._set_text(self.design_tab, "Loaded example configuration. Edit inputs and click 'Generate design'.")
        self._set_text(self.diagnostics_tab, "")
        self._set_plots_tab_message("Generate and export a design run to preview plots here.")
        self._set_text(self.export_tab, "")
        self._set_status("Ready", "Example loaded. Review inputs and generate design.", "info")

    def generate_design(self) -> None:
        try:
            self._sync_config_from_inputs()
            self.pipeline_result = run_design_pipeline(self.config)
        except Exception as exc:
            messagebox.showerror("Generate design failed", str(exc))
            self._set_status("Error", "Generate design failed. Review inputs.", "error")
            return

        design_table = []
        for batch in self.pipeline_result.design.batches:
            row = {
                "batch_id": batch.batch_id,
                "batch_name": batch.batch_name,
                "locked": batch.locked,
                "forced": batch.forced,
                "api_pure_mg_g": batch.api_pure_mg_g,
                "api_ds_total_mg_g": batch.api_ds_total_mg_g,
                "balance_mg_g": batch.balance_mg_g,
                "sum_weighed_components_mg_g": batch.sum_weighed_components_mg_g,
            }
            for component in self.config.components:
                if component.is_api:
                    continue
                row[f"{component.name}_mg_g"] = batch.component_mg_g.get(component.name, batch.balance_mg_g)
            design_table.append(row)

        self._set_text(self.design_tab, "\n".join(str(row) for row in design_table))
        self._set_text(self.diagnostics_tab, self.pipeline_result.diagnostics.summary.to_string(index=False))

        self._set_plots_tab_message(
            "Design generated.\nExport the run to create plots and browse pairwise previews in this tab."
        )

        warning_lines = [f"{w.severity}: {w.code} - {w.message}" for w in self.pipeline_result.warnings]
        self._set_text(self.export_tab, "\n".join(warning_lines) if warning_lines else "No warnings.")
        if warning_lines:
            self._set_status("Warning", "Design generated with warnings. Review diagnostics.", "warning")
        else:
            self._set_status("Success", "Design generated successfully.", "success")

    def recalculate_diagnostics(self) -> None:
        if self.pipeline_result is None:
            messagebox.showinfo("Recalculate diagnostics", "Generate a design first.")
            self._set_status("Info", "Generate a design before recalculating diagnostics.", "info")
            return

        try:
            self._sync_config_from_inputs()
        except Exception as exc:
            messagebox.showerror("Recalculate diagnostics failed", str(exc))
            self._set_status("Error", "Recalculate diagnostics failed due to invalid inputs.", "error")
            return

        diagnostics = calculate_diagnostics(batches=self.pipeline_result.design.batches, config=self.config)
        self.pipeline_result = PipelineResult(
            design=self.pipeline_result.design,
            diagnostics=diagnostics,
            assignments=self.pipeline_result.assignments,
            warnings=[*self.pipeline_result.design.warnings, *diagnostics.warnings],
        )
        self._set_text(self.diagnostics_tab, self.pipeline_result.diagnostics.summary.to_string(index=False))
        self._set_status("Success", "Diagnostics recalculated.", "success")

    def export_design(self) -> None:
        if self.pipeline_result is None:
            self.generate_design()
            if self.pipeline_result is None:
                return

        try:
            self._sync_config_from_inputs()
            self.last_output_folder = export_design_run(config=self.config, pipeline_result=self.pipeline_result)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            self._set_status("Error", "Export failed.", "error")
            return

        self._refresh_plot_previews_from_output_folder()
        self._set_text(self.export_tab, f"Exported run folder:\n{self.last_output_folder}")
        self._set_status("Success", f"Exported run: {self.last_output_folder.name}", "success")

    def open_output_folder(self) -> None:
        if self.last_output_folder is None:
            messagebox.showinfo("Open output folder", "Export a design run first.")
            self._set_status("Info", "Export a run before opening output folder.", "info")
            return

        try:
            os.startfile(str(self.last_output_folder))  # type: ignore[attr-defined]
            self._set_status("Success", "Opened output folder.", "success")
        except Exception as exc:
            messagebox.showerror("Open output folder failed", str(exc))
            self._set_status("Error", "Failed to open output folder.", "error")


def create_app_root() -> tuple[tk.Tk, CalibrationDesignerApp]:
    root = tk.Tk()
    app = CalibrationDesignerApp(root)
    return root, app


def launch_ui() -> None:
    root, _app = create_app_root()
    root.mainloop()
