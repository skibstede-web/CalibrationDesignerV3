"""Pydantic domain models for CalibrationDesignerV3."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ComponentSpec(BaseModel):
    name: str
    is_api: bool = False
    is_balance: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Component name must be non-empty")
        return name


class ProductStrength(BaseModel):
    name: str
    component_targets_mg_g: dict[str, float]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Strength name must be non-empty")
        return name

    @field_validator("component_targets_mg_g")
    @classmethod
    def validate_component_targets(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("Strength must include component targets")
        normalized: dict[str, float] = {}
        for key, amount in value.items():
            component_name = key.strip()
            if not component_name:
                raise ValueError("Component target name must be non-empty")
            if amount < 0:
                raise ValueError("Component targets must be >= 0 mg/g")
            normalized[component_name] = float(amount)
        return normalized


class ComponentConstraint(BaseModel):
    component_name: str
    min_mg_g: float
    max_mg_g: float
    preferred_levels: int = 3

    @field_validator("component_name")
    @classmethod
    def validate_component_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Constraint component name must be non-empty")
        return name

    @field_validator("preferred_levels")
    @classmethod
    def validate_preferred_levels(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Preferred levels must be >= 1")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> "ComponentConstraint":
        if self.min_mg_g > self.max_mg_g:
            raise ValueError("Constraint min_mg_g must be <= max_mg_g")
        return self


class DesignObjectiveSettings(BaseModel):
    use_constrained_mixture_design: bool = True
    reduce_api_excipient_correlation: bool = True
    improve_api_specificity: bool = True
    include_target_strengths_in_calibration_design: bool = False
    allow_reuse_across_strength_models: bool = True
    reduce_redundant_overlap_between_strengths: bool = True
    minimize_api_material_consumption: bool = False
    prefer_fewer_calibration_batches: bool = False
    allow_non_nominal_excipient_ratios: bool = True


class BatchSettings(BaseModel):
    desired_batches: int = 12
    min_batches: int = 8
    max_batches: int = 20
    default_batch_size: float = 1.0
    batch_size_unit: Literal["g", "kg"] = "kg"
    allow_different_batch_sizes: bool = False
    min_batch_size: float = 1.0
    max_batch_size: float = 1.0
    include_replicates: bool = False
    replicate_count: int = 0
    replicate_type: str = "exact"

    @model_validator(mode="after")
    def validate_batch_values(self) -> "BatchSettings":
        if self.min_batches < 1:
            raise ValueError("min_batches must be >= 1")
        if self.min_batches > self.max_batches:
            raise ValueError("min_batches must be <= max_batches")
        if not (self.min_batches <= self.desired_batches <= self.max_batches):
            raise ValueError("desired_batches must be within min_batches and max_batches")
        if self.default_batch_size <= 0:
            raise ValueError("default_batch_size must be > 0")
        if self.min_batch_size <= 0 or self.max_batch_size <= 0:
            raise ValueError("Batch size limits must be > 0")
        if self.min_batch_size > self.max_batch_size:
            raise ValueError("min_batch_size must be <= max_batch_size")
        if self.include_replicates and self.replicate_count < 1:
            raise ValueError("replicate_count must be >= 1 when include_replicates is True")
        return self


class CalibrationBatch(BaseModel):
    batch_id: str | None = None
    batch_name: str
    batch_role: str = "calibration"
    source: str = "generated"
    locked: bool = False
    forced: bool = False
    derived_batch: bool = False
    parent_batch_a: str | None = None
    parent_batch_b: str | None = None
    fraction_from_a: float | None = None
    assigned_strength_models: list[str] = Field(default_factory=list)
    reusable_across_strengths: bool = True
    preparation_route: str = "direct"
    batch_size_kg: float = 1.0
    api_pure_mg_g: float
    api_content_mg_mg: float
    api_ds_total_mg_g: float
    api_impurity_mg_g: float
    component_mg_g: dict[str, float]
    balance_mg_g: float
    sum_weighed_components_mg_g: float


class WarningEntry(BaseModel):
    severity: Literal["PASS", "INFO", "WARNING", "CRITICAL", "FAIL"]
    code: str
    message: str
    affected_batch_id: str = ""
    suggested_action: str = ""


class RunConfig(BaseModel):
    components: list[ComponentSpec]
    api_content_mg_mg: float
    product_strengths: list[ProductStrength]
    component_constraints: list[ComponentConstraint]
    objective_settings: DesignObjectiveSettings = Field(default_factory=DesignObjectiveSettings)
    batch_settings: BatchSettings = Field(default_factory=BatchSettings)
    manual_batches: list[CalibrationBatch] = Field(default_factory=list)
    seed: int = 123
    tolerance_mg_g: float = 1e-6

    @model_validator(mode="after")
    def validate_configuration(self) -> "RunConfig":
        api_count = sum(1 for c in self.components if c.is_api)
        balance_count = sum(1 for c in self.components if c.is_balance)
        if api_count != 1:
            raise ValueError("Exactly one API component must be selected")
        if balance_count != 1:
            raise ValueError("Exactly one balance component must be selected")
        if self.api_content_mg_mg <= 0:
            raise ValueError("API content must be > 0")

        names = [component.name for component in self.components]
        if len(names) != len(set(names)):
            raise ValueError("Component names must be unique")

        component_name_set = set(names)
        for constraint in self.component_constraints:
            if constraint.component_name not in component_name_set:
                raise ValueError(
                    f"Constraint provided for unknown component: {constraint.component_name}"
                )

        if self.batch_settings.min_batches > self.batch_settings.max_batches:
            raise ValueError("Invalid batch settings min/max")

        return self

    @property
    def api_component_name(self) -> str:
        return next(component.name for component in self.components if component.is_api)

    @property
    def balance_component_name(self) -> str:
        return next(component.name for component in self.components if component.is_balance)

    def constraint_map(self) -> dict[str, ComponentConstraint]:
        return {constraint.component_name: constraint for constraint in self.component_constraints}