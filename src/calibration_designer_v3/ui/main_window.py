"""Main desktop window for CalibrationDesignerV3."""

from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from calibration_designer_v3.core.diagnostics import calculate_diagnostics
from calibration_designer_v3.core.pipeline import PipelineResult, run_design_pipeline
from calibration_designer_v3.io.export import export_design_run
from calibration_designer_v3.models.config import build_example_run_config
from calibration_designer_v3.models.domain import RunConfig


class CalibrationDesignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CalibrationDesignerV3")
        self.root.geometry("1300x860")

        self.config: RunConfig = build_example_run_config()
        self.pipeline_result: PipelineResult | None = None
        self.last_output_folder: Path | None = None

        self._build_layout()
        self._populate_sections()

    def _build_layout(self) -> None:
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        top_bar = tk.Frame(self.root, bd=1, relief=tk.RIDGE)
        top_bar.grid(row=0, column=0, sticky="nsew")

        title = tk.Label(top_bar, text="CalibrationDesignerV3", font=("Segoe UI", 14, "bold"))
        title.pack(side=tk.LEFT, padx=12, pady=8)

        logo_path = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
        if logo_path.exists():
            try:
                photo = tk.PhotoImage(file=str(logo_path))
                logo_label = tk.Label(top_bar, image=photo)
                logo_label.image = photo
                logo_label.pack(side=tk.RIGHT, padx=8, pady=6)
            except Exception:
                pass

        body = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        body.grid(row=1, column=0, sticky="nsew")

        self.left_panel = tk.Frame(body)
        self.right_panel = tk.Frame(body)
        body.add(self.left_panel, minsize=440)
        body.add(self.right_panel)

        self.left_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        self._build_input_sections()
        self._build_output_panels()
        self._build_action_bar()

    def _build_input_sections(self) -> None:
        self.section_frames: dict[str, tk.LabelFrame] = {}
        section_names = [
            "1. Component setup",
            "2. Product strengths",
            "3. Component constraints",
            "4. Calibration design objective settings",
            "5. Batch number and batch size settings",
            "6. Manual design editing",
        ]

        for i, name in enumerate(section_names):
            frame = tk.LabelFrame(self.left_panel, text=name, padx=8, pady=6)
            frame.grid(row=i, column=0, sticky="nsew", padx=8, pady=5)
            self.section_frames[name] = frame

        self.component_text = tk.Text(self.section_frames[section_names[0]], height=5, wrap="word")
        self.component_text.pack(fill="both", expand=True)

        self.strength_text = tk.Text(self.section_frames[section_names[1]], height=5, wrap="word")
        self.strength_text.pack(fill="both", expand=True)

        self.constraint_text = tk.Text(self.section_frames[section_names[2]], height=6, wrap="word")
        self.constraint_text.pack(fill="both", expand=True)

        self.objective_text = tk.Text(self.section_frames[section_names[3]], height=6, wrap="word")
        self.objective_text.pack(fill="both", expand=True)

        self.batch_settings_text = tk.Text(self.section_frames[section_names[4]], height=6, wrap="word")
        self.batch_settings_text.pack(fill="both", expand=True)

        self.manual_edit_text = tk.Text(self.section_frames[section_names[5]], height=6, wrap="word")
        self.manual_edit_text.pack(fill="both", expand=True)
        self.manual_edit_text.insert(
            "1.0",
            "Manual controls supported in v1:\n- Add/edit/delete manual batch metadata via backend config\n- Lock/force batches\n- Recalculate diagnostics",
        )
        self.manual_edit_text.config(state="disabled")

    def _build_output_panels(self) -> None:
        notebook = ttk.Notebook(self.right_panel)
        notebook.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.design_tab = tk.Text(notebook, wrap="none")
        self.diagnostics_tab = tk.Text(notebook, wrap="none")
        self.plots_tab = tk.Text(notebook, wrap="word")
        self.export_tab = tk.Text(notebook, wrap="word")

        notebook.add(self.design_tab, text="Design table")
        notebook.add(self.diagnostics_tab, text="Diagnostics")
        notebook.add(self.plots_tab, text="Plots")
        notebook.add(self.export_tab, text="Export/run folder")

    def _build_action_bar(self) -> None:
        action_bar = tk.Frame(self.root, bd=1, relief=tk.GROOVE)
        action_bar.grid(row=2, column=0, sticky="ew")

        tk.Button(action_bar, text="Load example", command=self.load_example).pack(side=tk.LEFT, padx=8, pady=8)
        tk.Button(action_bar, text="Generate design", command=self.generate_design).pack(side=tk.LEFT, padx=8, pady=8)
        tk.Button(action_bar, text="Recalculate diagnostics", command=self.recalculate_diagnostics).pack(
            side=tk.LEFT, padx=8, pady=8
        )
        tk.Button(action_bar, text="Export design run", command=self.export_design).pack(side=tk.LEFT, padx=8, pady=8)
        tk.Button(action_bar, text="Open output folder", command=self.open_output_folder).pack(side=tk.LEFT, padx=8, pady=8)

    def _populate_sections(self) -> None:
        self._set_text(
            self.component_text,
            "\n".join(
                [
                    f"Component: {c.name}"
                    + (" [API]" if c.is_api else "")
                    + (" [BALANCE]" if c.is_balance else "")
                    for c in self.config.components
                ]
                + [f"API content (mg/mg): {self.config.api_content_mg_mg:.4f}"]
            ),
        )

        strength_lines = []
        for strength in self.config.product_strengths:
            strength_lines.append(f"Strength {strength.name}")
            for name, value in strength.component_targets_mg_g.items():
                strength_lines.append(f"  - {name}: {value:.3f} mg/g")
        self._set_text(self.strength_text, "\n".join(strength_lines))

        constraint_lines = [
            f"{con.component_name}: min={con.min_mg_g:.3f}, max={con.max_mg_g:.3f}, levels={con.preferred_levels}"
            for con in self.config.component_constraints
        ]
        self._set_text(self.constraint_text, "\n".join(constraint_lines))

        objective = self.config.objective_settings.model_dump()
        self._set_text(self.objective_text, "\n".join([f"{k}: {v}" for k, v in objective.items()]))

        batch_cfg = self.config.batch_settings.model_dump()
        self._set_text(self.batch_settings_text, "\n".join([f"{k}: {v}" for k, v in batch_cfg.items()]))

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        widget.config(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.config(state="disabled")

    def load_example(self) -> None:
        self.config = build_example_run_config()
        self.pipeline_result = None
        self.last_output_folder = None
        self._populate_sections()
        self._set_text(self.design_tab, "Loaded example configuration. Click 'Generate design'.")
        self._set_text(self.diagnostics_tab, "")
        self._set_text(self.plots_tab, "")
        self._set_text(self.export_tab, "")

    def generate_design(self) -> None:
        try:
            self.pipeline_result = run_design_pipeline(self.config)
        except Exception as exc:
            messagebox.showerror("Generate design failed", str(exc))
            return

        design_table = []
        for batch in self.pipeline_result.design.batches:
            design_table.append(
                {
                    "batch_id": batch.batch_id,
                    "api_pure_mg_g": batch.api_pure_mg_g,
                    "api_ds_total_mg_g": batch.api_ds_total_mg_g,
                    "balance_mg_g": batch.balance_mg_g,
                    "sum_weighed_components_mg_g": batch.sum_weighed_components_mg_g,
                }
            )

        self._set_text(self.design_tab, "\n".join(str(row) for row in design_table))
        self._set_text(self.diagnostics_tab, self.pipeline_result.diagnostics.summary.to_string(index=False))

        plot_notes = [
            "Plots are generated on export:",
            "- api_range_coverage.png",
            "- api_vs_each_excipient.png",
            "- component_correlation_heatmap.png",
            "- material_consumption.png",
            "- batch_reuse_map.png",
        ]
        self._set_text(self.plots_tab, "\n".join(plot_notes))

        warning_lines = [f"{w.severity}: {w.code} - {w.message}" for w in self.pipeline_result.warnings]
        self._set_text(self.export_tab, "\n".join(warning_lines) if warning_lines else "No warnings.")

    def recalculate_diagnostics(self) -> None:
        if self.pipeline_result is None:
            messagebox.showinfo("Recalculate diagnostics", "Generate a design first.")
            return

        diagnostics = calculate_diagnostics(batches=self.pipeline_result.design.batches, config=self.config)
        self.pipeline_result = PipelineResult(
            design=self.pipeline_result.design,
            diagnostics=diagnostics,
            assignments=self.pipeline_result.assignments,
            warnings=[*self.pipeline_result.design.warnings, *diagnostics.warnings],
        )
        self._set_text(self.diagnostics_tab, self.pipeline_result.diagnostics.summary.to_string(index=False))

    def export_design(self) -> None:
        if self.pipeline_result is None:
            self.generate_design()
            if self.pipeline_result is None:
                return

        try:
            self.last_output_folder = export_design_run(config=self.config, pipeline_result=self.pipeline_result)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return

        self._set_text(self.export_tab, f"Exported run folder:\n{self.last_output_folder}")

    def open_output_folder(self) -> None:
        if self.last_output_folder is None:
            messagebox.showinfo("Open output folder", "Export a design run first.")
            return

        try:
            os.startfile(str(self.last_output_folder))  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror("Open output folder failed", str(exc))


def create_app_root() -> tuple[tk.Tk, CalibrationDesignerApp]:
    root = tk.Tk()
    app = CalibrationDesignerApp(root)
    return root, app


def launch_ui() -> None:
    root, _app = create_app_root()
    root.mainloop()