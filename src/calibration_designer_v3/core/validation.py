"""Validation orchestration and warning generation."""

from __future__ import annotations

from calibration_designer_v3.models.domain import RunConfig, WarningEntry


def validate_run_config(config: RunConfig) -> list[WarningEntry]:
    warnings: list[WarningEntry] = []

    if config.api_content_mg_mg > 1.0:
        warnings.append(
            WarningEntry(
                severity="WARNING",
                code="API_CONTENT_GT_1",
                message="API content is greater than 1.0 mg/mg. Please verify assay basis.",
                suggested_action="Confirm potency/content entry and unit basis.",
            )
        )

    return warnings