"""Core orchestration pipeline for non-UI use."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from calibration_designer_v3.core.assignment import assign_batches_to_strength_models
from calibration_designer_v3.core.design_engine import DesignSelectionResult, select_calibration_design
from calibration_designer_v3.core.diagnostics import DiagnosticsResult, calculate_diagnostics
from calibration_designer_v3.models.domain import RunConfig, WarningEntry


@dataclass
class PipelineResult:
    design: DesignSelectionResult
    diagnostics: DiagnosticsResult
    assignments: pd.DataFrame
    warnings: list[WarningEntry]


def run_design_pipeline(config: RunConfig) -> PipelineResult:
    design = select_calibration_design(config=config)
    diagnostics = calculate_diagnostics(batches=design.batches, config=config)
    additional_rows = pd.DataFrame(
        [
            {
                "metric": "raw_grid_combinations",
                "value": float(design.raw_grid_combinations),
                "threshold": "informative",
                "status": "INFO",
                "interpretation": "Number of pre-feasibility grid combinations before balance calculation filtering.",
            },
            {
                "metric": "feasible_candidates_after_balance",
                "value": float(design.feasible_candidate_count),
                "threshold": ">= minimum requested batches",
                "status": "PASS"
                if design.feasible_candidate_count >= config.batch_settings.min_batches
                else "CRITICAL",
                "interpretation": "Candidates feasible after API DS and calculated balance constraints.",
            },
            {
                "metric": "selected_balance_component",
                "value": config.balance_component_name,
                "threshold": "exactly one",
                "status": "PASS",
                "interpretation": "Component calculated to make weighed total equal 1000 mg/g.",
            },
            {
                "metric": "selected_calibration_batches",
                "value": float(len(design.batches)),
                "threshold": f">= {config.batch_settings.min_batches}",
                "status": "PASS" if len(design.batches) >= config.batch_settings.min_batches else "CRITICAL",
                "interpretation": "Number of batches selected into final calibration design.",
            },
        ]
    )
    diagnostics.summary = pd.concat([diagnostics.summary, additional_rows], ignore_index=True)
    assignments = assign_batches_to_strength_models(batches=design.batches, config=config)

    warnings = [*design.warnings, *diagnostics.warnings]

    return PipelineResult(
        design=design,
        diagnostics=diagnostics,
        assignments=assignments,
        warnings=warnings,
    )
