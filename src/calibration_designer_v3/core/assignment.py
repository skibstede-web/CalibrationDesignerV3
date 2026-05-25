"""Batch-to-strength assignment logic."""

from __future__ import annotations

import pandas as pd

from calibration_designer_v3.models.domain import CalibrationBatch, ProductStrength, RunConfig


def _api_target_for_strength(strength: ProductStrength, api_component_name: str) -> float:
    if api_component_name not in strength.component_targets_mg_g:
        raise ValueError(f"Strength {strength.name} missing API target for {api_component_name}")
    return float(strength.component_targets_mg_g[api_component_name])


def assign_batches_to_strength_models(
    batches: list[CalibrationBatch],
    config: RunConfig,
) -> pd.DataFrame:
    api_name = config.api_component_name
    strengths = config.product_strengths
    reuse_enabled = config.objective_settings.allow_reuse_across_strength_models

    if not strengths:
        raise ValueError("At least one strength model is required")

    targets = {strength.name: _api_target_for_strength(strength, api_name) for strength in strengths}

    sorted_strength_names = [name for name, _ in sorted(targets.items(), key=lambda kv: kv[1])]
    sorted_targets = [targets[name] for name in sorted_strength_names]

    gaps = [abs(sorted_targets[i + 1] - sorted_targets[i]) for i in range(len(sorted_targets) - 1)]
    overlap_window = (min(gaps) * 0.35) if gaps else 0.0

    rows: list[dict[str, object]] = []

    for batch in batches:
        if batch.assigned_strength_models:
            assigned = list(dict.fromkeys(batch.assigned_strength_models))
        else:
            distance_pairs = sorted(
                [(name, abs(batch.api_pure_mg_g - targets[name])) for name in sorted_strength_names],
                key=lambda x: (x[1], x[0]),
            )
            assigned = [distance_pairs[0][0]]
            if reuse_enabled:
                for strength_name, distance in distance_pairs[1:]:
                    if distance <= overlap_window:
                        assigned.append(strength_name)

        assigned = list(dict.fromkeys(assigned))
        if not assigned:
            assigned = [sorted_strength_names[0]]

        for i, strength_name in enumerate(assigned):
            rows.append(
                {
                    "batch_id": batch.batch_id or batch.batch_name,
                    "strength_model": strength_name,
                    "included": True,
                    "role_in_model": "primary" if i == 0 else "reused",
                }
            )

    return pd.DataFrame(rows)