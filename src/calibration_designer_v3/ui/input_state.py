"""Conversion helpers between editable UI values and validated RunConfig."""

from __future__ import annotations

from dataclasses import dataclass, field

from calibration_designer_v3.core.composition import (
    calculate_api_ds_total,
    calculate_api_impurity,
    calculate_balance,
)
from calibration_designer_v3.core.guided_workflow import (
    auto_select_balance_component,
    default_allow_variation_map,
)
from calibration_designer_v3.models.domain import (
    ApiCalibrationRangeSettings,
    BatchSettings,
    CalibrationBatch,
    ComponentConstraint,
    ComponentSpec,
    DesignObjectiveSettings,
    ExcipientVariationSettings,
    ProductStrength,
    RunConfig,
)

STRENGTH_TOTAL_TARGET_MG_G = 1000.0
STRENGTH_TOTAL_TOLERANCE_MG_G = 0.001


@dataclass
class ComponentInputRow:
    name: str
    is_api: bool = False
    is_balance: bool = False
    component_type: str = "major_excipient"


@dataclass
class StrengthInputRow:
    name: str
    targets_mg_g: list[float]


@dataclass
class ConstraintInputRow:
    min_mg_g: float
    max_mg_g: float
    preferred_levels: int


@dataclass
class ManualBatchInputRow:
    batch_name: str
    api_pure_mg_g: float
    non_api_non_balance_mg_g: list[float]
    locked: bool = False
    forced: bool = False
    reusable_across_strengths: bool = True


@dataclass
class AppInputState:
    components: list[ComponentInputRow]
    api_content_mg_mg: float
    strengths: list[StrengthInputRow]
    constraints: list[ConstraintInputRow]
    objective_settings: DesignObjectiveSettings
    batch_settings: BatchSettings
    api_calibration_range_settings: ApiCalibrationRangeSettings = field(default_factory=ApiCalibrationRangeSettings)
    excipient_variation_settings: ExcipientVariationSettings = field(default_factory=ExcipientVariationSettings)
    manual_batches: list[ManualBatchInputRow] = field(default_factory=list)
    seed: int = 123
    tolerance_mg_g: float = 1e-6


@dataclass
class StrengthTotalValidation:
    strength_name: str
    api_pure_mg_g: float
    api_ds_total_mg_g: float
    weighed_total_mg_g: float
    delta_from_target_mg_g: float
    is_valid: bool
    status: str


def evaluate_strength_totals(
    *,
    components: list[ComponentInputRow],
    strengths: list[StrengthInputRow],
    api_content_mg_mg: float,
    tolerance_mg_g: float = STRENGTH_TOTAL_TOLERANCE_MG_G,
) -> list[StrengthTotalValidation]:
    if api_content_mg_mg <= 0:
        raise ValueError("API content must be > 0 for target-strength total validation")

    api_indices = [idx for idx, component in enumerate(components) if component.is_api]
    if len(api_indices) != 1:
        raise ValueError("Exactly one API component must be selected for target-strength validation")
    api_index = api_indices[0]

    validations: list[StrengthTotalValidation] = []
    for row_index, strength in enumerate(strengths, start=1):
        if len(strength.targets_mg_g) != len(components):
            raise ValueError("Each strength must provide one target mg/g value per component")

        api_pure_mg_g = float(strength.targets_mg_g[api_index])
        api_ds_total_mg_g = float(
            calculate_api_ds_total(api_pure_mg_g=api_pure_mg_g, api_content_mg_mg=api_content_mg_mg)
        )
        non_api_total_mg_g = float(
            sum(float(value) for idx, value in enumerate(strength.targets_mg_g) if idx != api_index)
        )
        weighed_total_mg_g = float(api_ds_total_mg_g + non_api_total_mg_g)
        delta_from_target_mg_g = float(weighed_total_mg_g - STRENGTH_TOTAL_TARGET_MG_G)
        is_valid = abs(delta_from_target_mg_g) <= tolerance_mg_g

        validations.append(
            StrengthTotalValidation(
                strength_name=strength.name.strip() or f"Strength {row_index}",
                api_pure_mg_g=api_pure_mg_g,
                api_ds_total_mg_g=api_ds_total_mg_g,
                weighed_total_mg_g=weighed_total_mg_g,
                delta_from_target_mg_g=delta_from_target_mg_g,
                is_valid=is_valid,
                status="PASS" if is_valid else "FAIL",
            )
        )

    return validations


def app_input_state_from_run_config(config: RunConfig) -> AppInputState:
    component_index = {component.name: idx for idx, component in enumerate(config.components)}
    api_index = next(idx for idx, component in enumerate(config.components) if component.is_api)
    balance_index = next(idx for idx, component in enumerate(config.components) if component.is_balance)

    components = [
        ComponentInputRow(
            name=component.name,
            is_api=component.is_api,
            is_balance=component.is_balance,
            component_type=component.component_type,
        )
        for component in config.components
    ]

    strengths: list[StrengthInputRow] = []
    for strength in config.product_strengths:
        targets = [0.0] * len(config.components)
        for component_name, value in strength.component_targets_mg_g.items():
            if component_name in component_index:
                targets[component_index[component_name]] = float(value)
        balance_name = config.components[balance_index].name
        if balance_name not in strength.component_targets_mg_g and config.api_content_mg_mg > 0:
            api_pure = float(targets[api_index])
            api_ds_total = float(
                calculate_api_ds_total(api_pure_mg_g=api_pure, api_content_mg_mg=config.api_content_mg_mg)
            )
            non_api_non_balance_total = float(
                sum(value for idx, value in enumerate(targets) if idx not in {api_index, balance_index})
            )
            targets[balance_index] = float(STRENGTH_TOTAL_TARGET_MG_G - api_ds_total - non_api_non_balance_total)
        strengths.append(StrengthInputRow(name=strength.name, targets_mg_g=targets))

    constraint_map = {constraint.component_name: constraint for constraint in config.component_constraints}
    constraints: list[ConstraintInputRow] = []
    for component in config.components:
        constraint = constraint_map[component.name]
        constraints.append(
            ConstraintInputRow(
                min_mg_g=float(constraint.min_mg_g),
                max_mg_g=float(constraint.max_mg_g),
                preferred_levels=int(constraint.preferred_levels),
            )
        )

    non_api_non_balance_names = [
        component.name for component in config.components if not component.is_api and not component.is_balance
    ]
    manual_batches: list[ManualBatchInputRow] = []
    for batch in config.manual_batches:
        non_api_levels = [float(batch.component_mg_g.get(name, 0.0)) for name in non_api_non_balance_names]
        manual_batches.append(
            ManualBatchInputRow(
                batch_name=batch.batch_name,
                api_pure_mg_g=float(batch.api_pure_mg_g),
                non_api_non_balance_mg_g=non_api_levels,
                locked=bool(batch.locked),
                forced=bool(batch.forced),
                reusable_across_strengths=bool(batch.reusable_across_strengths),
            )
        )

    return AppInputState(
        components=components,
        api_content_mg_mg=float(config.api_content_mg_mg),
        strengths=strengths,
        constraints=constraints,
        api_calibration_range_settings=config.api_calibration_range_settings.model_copy(deep=True),
        excipient_variation_settings=config.excipient_variation_settings.model_copy(deep=True),
        objective_settings=config.objective_settings.model_copy(deep=True),
        batch_settings=config.batch_settings.model_copy(deep=True),
        manual_batches=manual_batches,
        seed=int(config.seed),
        tolerance_mg_g=float(config.tolerance_mg_g),
    )


def _build_manual_batches(
    *,
    manual_inputs: list[ManualBatchInputRow],
    components: list[ComponentSpec],
    api_content_mg_mg: float,
    batch_settings: BatchSettings,
    tolerance_mg_g: float,
) -> list[CalibrationBatch]:
    if not manual_inputs:
        return []

    balance_name = next(component.name for component in components if component.is_balance)
    non_api_non_balance_names = [
        component.name for component in components if not component.is_api and not component.is_balance
    ]

    batch_size_kg = float(batch_settings.default_batch_size)
    if batch_settings.batch_size_unit == "g":
        batch_size_kg = batch_size_kg / 1000.0

    manual_batches: list[CalibrationBatch] = []
    for index, manual in enumerate(manual_inputs, start=1):
        if len(manual.non_api_non_balance_mg_g) != len(non_api_non_balance_names):
            raise ValueError(
                "Manual batch component vector length does not match non-API non-balance component count"
            )

        non_api_map = {
            name: float(value)
            for name, value in zip(non_api_non_balance_names, manual.non_api_non_balance_mg_g, strict=True)
        }

        api_pure = float(manual.api_pure_mg_g)
        api_ds = calculate_api_ds_total(api_pure_mg_g=api_pure, api_content_mg_mg=api_content_mg_mg)
        api_impurity = calculate_api_impurity(api_pure_mg_g=api_pure, api_content_mg_mg=api_content_mg_mg)
        balance_mg_g = calculate_balance(
            api_ds_total_mg_g=api_ds,
            non_api_non_balance_components_mg_g=non_api_map,
        )

        component_mg_g = dict(non_api_map)
        component_mg_g[balance_name] = float(balance_mg_g)

        sum_total = float(api_ds + sum(non_api_map.values()) + balance_mg_g)
        if abs(sum_total - 1000.0) > max(1e-9, tolerance_mg_g * 10.0):
            raise ValueError("Manual batch does not satisfy 1000 mg/g weighed-material closure")

        manual_batches.append(
            CalibrationBatch(
                batch_id=f"MAN-{index:03d}",
                batch_name=manual.batch_name,
                source="manual",
                locked=bool(manual.locked),
                forced=bool(manual.forced),
                reusable_across_strengths=bool(manual.reusable_across_strengths),
                batch_size_kg=batch_size_kg,
                api_pure_mg_g=api_pure,
                api_content_mg_mg=float(api_content_mg_mg),
                api_ds_total_mg_g=float(api_ds),
                api_impurity_mg_g=float(api_impurity),
                component_mg_g=component_mg_g,
                balance_mg_g=float(balance_mg_g),
                sum_weighed_components_mg_g=sum_total,
            )
        )

    return manual_batches


def build_run_config_from_app_input_state(state: AppInputState) -> RunConfig:
    components = [
        ComponentSpec(
            name=row.name,
            is_api=bool(row.is_api),
            is_balance=bool(row.is_balance),
            component_type=row.component_type,  # type: ignore[arg-type]
        )
        for row in state.components
    ]

    if not components:
        raise ValueError("At least one component is required")

    constraints = []
    if len(state.constraints) != len(components):
        raise ValueError("Constraint count must match component count")

    for component, constraint in zip(components, state.constraints, strict=True):
        constraints.append(
            ComponentConstraint(
                component_name=component.name,
                min_mg_g=float(constraint.min_mg_g),
                max_mg_g=float(constraint.max_mg_g),
                preferred_levels=int(constraint.preferred_levels),
            )
        )

    if not any(component.is_balance for component in components):
        variation = state.excipient_variation_settings.model_copy(deep=True)
        if not variation.allow_variation_by_component:
            variation.allow_variation_by_component = default_allow_variation_map(components)
        chosen_balance = auto_select_balance_component(
            components=components,
            strength=ProductStrength(
                name=state.strengths[0].name if state.strengths else "Strength 1",
                component_targets_mg_g={
                    comp.name: state.strengths[0].targets_mg_g[i] if state.strengths else 0.0
                    for i, comp in enumerate(components)
                },
            ),
            allow_variation_by_component=variation.allow_variation_by_component,
            keep_glidant_lubricant_fixed=variation.keep_glidant_lubricant_fixed,
            manual_override=(
                variation.manual_balance_component_override if not variation.auto_select_balance_component else None
            ),
        )
        for component in components:
            component.is_balance = component.name == chosen_balance

    strengths: list[ProductStrength] = []
    for strength in state.strengths:
        if len(strength.targets_mg_g) != len(components):
            raise ValueError("Each strength must provide one target value per component")

        targets: dict[str, float] = {}
        for component, target in zip(components, strength.targets_mg_g, strict=True):
            targets[component.name] = float(target)

        strengths.append(ProductStrength(name=strength.name, component_targets_mg_g=targets))

    strength_validations = evaluate_strength_totals(
        components=state.components,
        strengths=state.strengths,
        api_content_mg_mg=float(state.api_content_mg_mg),
        tolerance_mg_g=STRENGTH_TOTAL_TOLERANCE_MG_G,
    )
    invalid_strengths = [validation for validation in strength_validations if not validation.is_valid]
    if invalid_strengths:
        details = ", ".join(
            f"{entry.strength_name} total={entry.weighed_total_mg_g:.6f} mg/g (delta {entry.delta_from_target_mg_g:+.6f})"
            for entry in invalid_strengths
        )
        raise ValueError(
            f"Target-strength composition totals must be {STRENGTH_TOTAL_TARGET_MG_G:.3f} mg/g "
            f"+/- {STRENGTH_TOTAL_TOLERANCE_MG_G:.3f}. Invalid: {details}"
        )

    manual_batches = _build_manual_batches(
        manual_inputs=state.manual_batches,
        components=components,
        api_content_mg_mg=float(state.api_content_mg_mg),
        batch_settings=state.batch_settings,
        tolerance_mg_g=float(state.tolerance_mg_g),
    )

    return RunConfig(
        components=components,
        api_content_mg_mg=float(state.api_content_mg_mg),
        product_strengths=strengths,
        component_constraints=constraints,
        api_calibration_range_settings=state.api_calibration_range_settings.model_copy(deep=True),
        excipient_variation_settings=state.excipient_variation_settings.model_copy(deep=True),
        objective_settings=state.objective_settings.model_copy(deep=True),
        batch_settings=state.batch_settings.model_copy(deep=True),
        manual_batches=manual_batches,
        seed=int(state.seed),
        tolerance_mg_g=float(state.tolerance_mg_g),
    )
