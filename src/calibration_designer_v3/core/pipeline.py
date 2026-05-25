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
    assignments = assign_batches_to_strength_models(batches=design.batches, config=config)

    warnings = [*design.warnings, *diagnostics.warnings]

    return PipelineResult(
        design=design,
        diagnostics=diagnostics,
        assignments=assignments,
        warnings=warnings,
    )