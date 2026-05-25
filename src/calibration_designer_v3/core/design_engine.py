"""Deterministic calibration design selection engine."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from calibration_designer_v3.core.candidate_generation import generate_candidate_compositions
from calibration_designer_v3.core.feasibility import is_feasible_candidate
from calibration_designer_v3.models.domain import CalibrationBatch, RunConfig, WarningEntry


@dataclass
class DesignSelectionResult:
    batches: list[CalibrationBatch]
    warnings: list[WarningEntry]
    selected_candidates: pd.DataFrame


def _candidate_signature(row: pd.Series) -> tuple[float, ...]:
    keys = sorted(k for k in row.index if k.endswith("_mg_g") or k.startswith("api_"))
    return tuple(float(round(float(row[k]), 8)) for k in keys)


def _manual_signature(batch: CalibrationBatch) -> tuple[float, ...]:
    keys = sorted(batch.component_mg_g)
    values = [round(float(batch.api_pure_mg_g), 8), round(float(batch.api_ds_total_mg_g), 8)]
    values.extend(round(float(batch.component_mg_g[k]), 8) for k in keys)
    values.append(round(float(batch.balance_mg_g), 8))
    return tuple(values)


def _to_batch(row: pd.Series, config: RunConfig, index: int, source: str = "generated") -> CalibrationBatch:
    api_name = config.api_component_name
    balance_name = config.balance_component_name

    component_mg_g: dict[str, float] = {}
    for component in config.components:
        if component.name == api_name:
            continue
        key = f"{component.name}_mg_g"
        if component.name == balance_name:
            component_mg_g[component.name] = float(row["balance_mg_g"])
        elif key in row:
            component_mg_g[component.name] = float(row[key])

    return CalibrationBatch(
        batch_id=f"CAL-{index:03d}",
        batch_name=f"Calibration {index:03d}",
        source=source,
        batch_size_kg=float(config.batch_settings.default_batch_size)
        if config.batch_settings.batch_size_unit == "kg"
        else float(config.batch_settings.default_batch_size) / 1000.0,
        api_pure_mg_g=float(row["api_pure_mg_g"]),
        api_content_mg_mg=float(row["api_content_mg_mg"]),
        api_ds_total_mg_g=float(row["api_ds_total_mg_g"]),
        api_impurity_mg_g=float(row["api_impurity_mg_g"]),
        component_mg_g=component_mg_g,
        balance_mg_g=float(row["balance_mg_g"]),
        sum_weighed_components_mg_g=float(row["sum_weighed_components_mg_g"]),
    )


def _score_candidate(selected: pd.DataFrame, candidate: pd.Series, excipient_cols: list[str]) -> float:
    if selected.empty:
        return 1_000_000.0

    combined = pd.concat([selected, candidate.to_frame().T], ignore_index=True)

    api_range = float(combined["api_pure_mg_g"].max() - combined["api_pure_mg_g"].min())

    diversity = 0.0
    for col in excipient_cols:
        diversity += float(combined[col].nunique())

    corr_penalty = 0.0
    if len(combined) >= 3 and excipient_cols:
        for col in excipient_cols:
            if combined["api_pure_mg_g"].nunique() <= 1 or combined[col].nunique() <= 1:
                continue
            corr = combined["api_pure_mg_g"].corr(combined[col])
            if not pd.isna(corr):
                corr_penalty = max(corr_penalty, abs(float(corr)))

    return (api_range * 10.0) + diversity - (corr_penalty * 25.0)


def _is_row_feasible_by_config(row: pd.Series, config: RunConfig) -> bool:
    constraint_map = config.constraint_map()
    api_name = config.api_component_name
    balance_name = config.balance_component_name

    api_constraint = constraint_map[api_name]
    api_pure = float(row["api_pure_mg_g"])
    if api_pure < api_constraint.min_mg_g - config.tolerance_mg_g:
        return False
    if api_pure > api_constraint.max_mg_g + config.tolerance_mg_g:
        return False

    candidate_component_mg_g: dict[str, float] = {}
    for component in config.components:
        if component.is_api:
            continue
        if component.is_balance:
            candidate_component_mg_g[component.name] = float(row["balance_mg_g"])
            continue
        key = f"{component.name}_mg_g"
        if key not in row:
            return False
        candidate_component_mg_g[component.name] = float(row[key])

    non_api_constraints = {
        name: constraint for name, constraint in constraint_map.items() if name != api_name
    }
    return is_feasible_candidate(
        candidate_component_mg_g=candidate_component_mg_g,
        constraint_map=non_api_constraints,
        api_ds_total_mg_g=float(row["api_ds_total_mg_g"]),
        balance_mg_g=float(row["balance_mg_g"]),
        tolerance_mg_g=config.tolerance_mg_g,
    )


def select_calibration_design(
    config: RunConfig,
    candidates: pd.DataFrame | None = None,
) -> DesignSelectionResult:
    warnings: list[WarningEntry] = []

    if candidates is None:
        candidates = generate_candidate_compositions(config)

    if candidates.empty:
        warnings.append(
            WarningEntry(
                severity="FAIL",
                code="NO_FEASIBLE_CANDIDATES",
                message="No feasible candidates were generated from the current constraints.",
                suggested_action="Review component ranges and API content settings.",
            )
        )
        return DesignSelectionResult(batches=[], warnings=warnings, selected_candidates=pd.DataFrame())

    selected_rows: list[pd.Series] = []
    selected_signatures: set[tuple[float, ...]] = set()

    # 1) Include locked/forced manual batches first.
    for manual_batch in config.manual_batches:
        if not (manual_batch.locked or manual_batch.forced):
            continue
        selected_signatures.add(_manual_signature(manual_batch))

    # 2) Include target-strength nearest candidates when toggle is ON.
    if config.objective_settings.include_target_strengths_in_calibration_design:
        api_name = config.api_component_name
        used_row_idx: set[int] = set()
        for strength in config.product_strengths:
            target_api = strength.component_targets_mg_g.get(api_name)
            if target_api is None:
                continue
            distances = (candidates["api_pure_mg_g"] - float(target_api)).abs()
            nearest_idx = int(distances.sort_values(kind="mergesort").index[0])
            if nearest_idx in used_row_idx:
                continue
            row = candidates.loc[nearest_idx]
            signature = _candidate_signature(row)
            if signature not in selected_signatures:
                selected_rows.append(row)
                selected_signatures.add(signature)
                used_row_idx.add(nearest_idx)

    # 3) Greedy deterministic fill.
    desired = config.batch_settings.desired_batches
    excipient_cols = sorted(col for col in candidates.columns if col.endswith("_mg_g") and col not in {"balance_mg_g"})

    pool = candidates.sort_values(by=sorted(candidates.columns), kind="mergesort").reset_index(drop=True)
    pool = pool[pool.apply(lambda row: _is_row_feasible_by_config(row, config), axis=1)].reset_index(drop=True)

    while len(selected_rows) + len([b for b in config.manual_batches if b.locked or b.forced]) < desired:
        working_selected = pd.DataFrame(selected_rows) if selected_rows else pd.DataFrame(columns=candidates.columns)
        best_index: int | None = None
        best_score: float | None = None

        for i, row in pool.iterrows():
            signature = _candidate_signature(row)
            if signature in selected_signatures:
                continue
            score = _score_candidate(selected=working_selected, candidate=row, excipient_cols=excipient_cols)
            if best_score is None or score > best_score:
                best_score = score
                best_index = i

        if best_index is None:
            break

        best_row = pool.loc[best_index]
        selected_rows.append(best_row)
        selected_signatures.add(_candidate_signature(best_row))

    manual_locked_forced = [batch for batch in config.manual_batches if batch.locked or batch.forced]

    if len(selected_rows) + len(manual_locked_forced) < desired:
        warnings.append(
            WarningEntry(
                severity="WARNING",
                code="INSUFFICIENT_BATCHES",
                message="Fewer feasible batches were available than desired batch count.",
                suggested_action="Expand component ranges or reduce desired batch count.",
            )
        )

    selected_df = pd.DataFrame(selected_rows).reset_index(drop=True) if selected_rows else pd.DataFrame()

    batches: list[CalibrationBatch] = []

    for manual_batch in manual_locked_forced:
        batches.append(manual_batch.model_copy(update={"batch_id": f"CAL-{len(batches) + 1:03d}"}))

    if not selected_df.empty:
        for _, row in selected_df.iterrows():
            batches.append(_to_batch(row=row, config=config, index=len(batches) + 1))

    return DesignSelectionResult(batches=batches, warnings=warnings, selected_candidates=selected_df)
