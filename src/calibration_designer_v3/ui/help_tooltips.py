"""Tooltip helpers and help-text content for UI guidance."""

from __future__ import annotations

import tkinter as tk

HELP_TEXTS: dict[str, str] = {
    "component_count": (
        "Defines how many formulation components are included in the calibration design. Include API and all formulation "
        "components that contribute to the weighed powder blend."
    ),
    "component_name": (
        "User-defined component name used throughout the app, plots, diagnostics, and output files. Use clear material names "
        "because these labels are used in exported design documentation."
    ),
    "api_component_selector": (
        "Selects which component is the active pharmaceutical ingredient. The API component is the calibration target variable, "
        "and correlations are evaluated against this component."
    ),
    "balance_component_selector": (
        "Selects which component is calculated as the balance component so the weighed blend sums to 1000 mg/g. This should "
        "normally be a major excipient with enough room to absorb formulation changes."
    ),
    "component_type": (
        "Classifies each component as API, major excipient, minor excipient, or glidant/lubricant. The design engine uses this "
        "to decide which components can vary and which component is suitable as the calculated balance component."
    ),
    "api_content_mg_mg": (
        "Defines the amount of pure API per mg of API drug substance. The calibration target is pure API mg/g, but weighing "
        "and formulation totals use API drug substance mg/g calculated as pure API divided by API content."
    ),
    "strength_count": (
        "Defines how many nominal product-strength formulations are entered. Each strength can later be used as the basis for "
        "a strength-specific PLS calibration model."
    ),
    "strength_name": (
        "Name or label for the target-strength formulation, for example 1%, 3%, 6%, Low, Medium, or High. This name is used "
        "in plots, diagnostics, and batch assignment."
    ),
    "component_concentration_mg_g": (
        "Nominal concentration of this component in the target-strength formulation. Values are entered in mg/g. For the API, "
        "enter pure API mg/g. The app corrects the weighed API drug substance amount using API content."
    ),
    "api_ds_mg_g_display": (
        "Calculated API drug-substance concentration needed to deliver the pure API target. This is calculated from pure API "
        "mg/g divided by API content mg/mg."
    ),
    "weighed_total_status": (
        "The weighed formulation total must equal 1000 mg/g, corresponding to 100% w/w. The total uses API drug substance "
        "mg/g, not only pure API mg/g."
    ),
    "api_range_mode": (
        "Defines whether API calibration levels are generated as percent of each target strength or as absolute mg/g values. "
        "Percent of target is often useful when several strengths use the same relative calibration span."
    ),
    "api_lower_level": (
        "Lower API level for the calibration design. In percent mode this is relative to target, for example 60% of target. "
        "In absolute mode it is entered directly as pure API mg/g."
    ),
    "api_upper_level": (
        "Upper API level for the calibration design. In percent mode this is relative to target, for example 140% of target. "
        "The upper level should normally extend beyond the intended monitoring range."
    ),
    "api_level_count": (
        "Defines how many API concentration levels are generated across the calibration range. More levels improve API range "
        "coverage but may increase the number of calibration batches."
    ),
    "include_target_api_level": (
        "Controls whether the exact target API concentration is forced into the generated API levels. Target points can be "
        "useful as anchors, but they are not always statistically required."
    ),
    "apply_same_api_range": (
        "Uses the same relative or absolute API range settings for all target strengths. This is convenient for multi-strength "
        "projects but can be changed if different strengths need different calibration spans."
    ),
    "variation_preset": (
        "Controls how far flexible non-API components are allowed to vary around their nominal target-strength values. "
        "Conservative keeps excipient variation close to target; Aggressive gives the design engine more freedom to reduce "
        "API-excipient correlation but may create less product-like calibration batches."
    ),
    "allow_variation_by_component": (
        "Determines whether the design engine may vary this component across calibration batches. Allow variation for "
        "components that may interfere with the API NIR signal or should be decorrelated from API. Keep fixed for components "
        "that are not relevant or should remain constant."
    ),
    "keep_glidant_lubricant_fixed": (
        "Keeps small functional excipients such as glidants or lubricants at their nominal level. This is usually appropriate "
        "because these components are low-level, have narrow formulation ranges, and are not good choices for balancing the total composition."
    ),
    "auto_select_balance_component": (
        "Allows the app to choose a suitable major excipient as the calculated balance component so each calibration batch sums "
        "to 1000 mg/g. This avoids asking the user to manually choose a balance component and reduces infeasible designs."
    ),
    "manual_balance_override": (
        "Allows an advanced user to manually select which component is calculated as the balance component. Use with caution. "
        "The balance component should normally be a major excipient with enough formulation range to absorb changes in API and other components."
    ),
    "custom_variation_percentages": (
        "Defines how far this component may vary around its nominal target value when custom variation is used. Very narrow "
        "ranges may limit feasible designs; wider ranges can reduce correlation but may create less product-like samples."
    ),
    "use_constrained_mixture_design": (
        "Ensures every generated calibration batch respects the mixture constraint and sums to 1000 mg/g after API content "
        "correction. This should normally remain enabled."
    ),
    "reduce_api_excipient_correlation": (
        "Prioritizes designs where API concentration is less correlated with excipient concentrations. This helps reduce the "
        "risk that the PLS model predicts API indirectly from excipient variation."
    ),
    "improve_api_specificity": (
        "Prioritizes calibration batches that help distinguish API spectral information from excipient and formulation effects. "
        "This is important for low-dose NIR reflectance models."
    ),
    "use_d_optimal_or_approximate_d_optimal_selection": (
        "Uses an information-based selection routine to choose a subset of feasible candidate batches. This helps create a design "
        "with better spread and lower redundancy, but the final design should still be reviewed using diagnostics."
    ),
    "include_target_strengths_in_calibration_design": (
        "Forces exact nominal target-strength compositions into the calibration design. This can be useful as an anchor or for "
        "stakeholder confidence, but it may increase correlation if target recipes lie on a strongly correlated recipe line."
    ),
    "allow_reuse_across_strength_models": (
        "Allows one calibration batch to support more than one strength-specific PLS model when its composition is relevant for "
        "overlapping calibration ranges. This can reduce material use and redundant batches."
    ),
    "reduce_redundant_overlap_between_strengths": (
        "Penalizes unnecessary duplicate or near-duplicate batches across target strengths. This helps the final design use "
        "material more efficiently."
    ),
    "minimize_api_material_consumption": (
        "Adds preference for designs that use less API drug substance. This can be useful when API material is expensive or "
        "limited, but it should not override scientific calibration quality."
    ),
    "prefer_fewer_calibration_batches": (
        "Adds preference for smaller designs. Use this when material or time is limited, but ensure the selected design still "
        "has adequate API range coverage and acceptable correlation diagnostics."
    ),
    "allow_non_nominal_excipient_ratios": (
        "Allows excipient ratios to deviate from the nominal target recipe. This is usually important for reducing API-excipient "
        "correlation and improving API specificity."
    ),
    "desired_batches": (
        "Target number of batches the design engine should select. The final number may differ if the feasible candidate space "
        "is too small or if forced target points are included."
    ),
    "min_batches": (
        "Minimum acceptable number of selected calibration batches. If the app cannot generate at least this many feasible "
        "batches, it should warn or block the design."
    ),
    "max_batches": (
        "Maximum allowed number of selected calibration batches. This prevents the app from creating a design that is too large "
        "for practical laboratory execution."
    ),
    "default_batch_size": (
        "Default amount of each calibration batch to prepare. This is used to calculate material consumption and weighing sheets."
    ),
    "batch_size_unit": (
        "Unit used for batch size calculations, for example kg or g. Material consumption outputs are calculated from this setting."
    ),
    "allow_different_batch_sizes": (
        "Allows individual calibration batches to have different preparation sizes. This may be useful when some batches are reused "
        "or when material availability differs."
    ),
    "min_batch_size": (
        "Smallest allowed batch size. Use this to avoid impractical or poorly mixed small batches."
    ),
    "max_batch_size": (
        "Largest allowed batch size. Use this to stay within equipment capacity or material availability."
    ),
    "include_replicates": (
        "Adds replicated calibration batches. Replicates can help estimate preparation and measurement repeatability, but they "
        "increase material consumption."
    ),
    "replicate_count": (
        "Number of replicate batches to include if replicates are enabled. Replicates should be chosen deliberately and not at "
        "the expense of API range or specificity."
    ),
    "replicate_type": (
        "Defines how replicate batches are selected, for example exact target replicates, app-suggested replicates, or manually "
        "selected replicates."
    ),
    "seed": (
        "Seed used to make the design selection reproducible. With the same inputs and seed, the app should generate the same design."
    ),
}

REQUIRED_INPUT_HELP_KEYS = tuple(HELP_TEXTS.keys())
EXCIPIENT_VARIATION_HELP_TEXTS = HELP_TEXTS


class HoverTooltip:
    """Small hover tooltip attached to a Tk widget."""

    def __init__(self, widget: tk.Widget, text: str, *, delay_ms: int = 220, wraplength: int = 360) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.wraplength = wraplength
        self._after_id: str | None = None
        self._tip_window: tk.Toplevel | None = None

        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._on_leave, add="+")
        self.widget.bind("<Destroy>", self._on_destroy, add="+")

    def _on_enter(self, _event: tk.Event[tk.Widget]) -> None:
        self._schedule_show()

    def _on_leave(self, _event: tk.Event[tk.Widget]) -> None:
        self._cancel_scheduled_show()
        self.hide()

    def _on_destroy(self, _event: tk.Event[tk.Widget]) -> None:
        self._cancel_scheduled_show()
        self.hide()

    def _schedule_show(self) -> None:
        self._cancel_scheduled_show()
        self._after_id = self.widget.after(self.delay_ms, self.show)

    def _cancel_scheduled_show(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def show(self) -> None:
        self._after_id = None
        if self._tip_window is not None:
            return
        if not self.text or not self.widget.winfo_exists():
            return

        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 10
        y = self.widget.winfo_rooty() + 2

        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tip.attributes("-topmost", True)

        label = tk.Label(
            tip,
            text=self.text,
            justify="left",
            anchor="w",
            wraplength=self.wraplength,
            bg="#FFFCEB",
            fg="#0B1F33",
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=6,
            font=("Segoe UI", 9),
        )
        label.pack(fill="both", expand=True)
        self._tip_window = tip

    def hide(self) -> None:
        if self._tip_window is None:
            return
        try:
            self._tip_window.destroy()
        except tk.TclError:
            pass
        self._tip_window = None
