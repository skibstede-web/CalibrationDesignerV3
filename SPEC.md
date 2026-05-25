# SPEC.md — CalibrationDesignerV3 v1 Specification

## 1. Product goal

CalibrationDesignerV3 v1 is a desktop application for designing calibration batch compositions for low-dose powder NIR reflectance PLS methods.

The app is not a PLS modeling tool. It does not import spectra or HPLC results in v1. It designs calibration batch compositions and exports scientifically useful diagnostics and preparation files.

## 2. Scientific problem

Low-dose API NIR reflectance calibration can be weak if calibration samples are prepared randomly or only along nominal recipe lines. The design may accidentally create high correlation between API and excipients, allowing a PLS model to predict API indirectly from SNAC, niacinamide, balance, strength identity, or other correlated matrix signals.

v1 must therefore prioritize:

1. constrained mixture feasibility;
2. API-specific calibration information;
3. reduced API-excipient correlation;
4. practical batch preparation outputs.

## 3. Units and composition basis

Use `mg/g` everywhere in the user-facing app.

- `1000 mg/g` = `100% w/w`
- `10 mg/g` = `1% w/w`
- `30 mg/g` = `3% w/w`

API target concentrations are entered as **pure API mg/g**.

API content is entered as `mg/mg`:

```text
api_content_mg_mg = mg pure API / mg API drug substance
```

Calculate:

```text
api_ds_total_mg_g = api_pure_mg_g / api_content_mg_mg
api_impurity_mg_g = api_ds_total_mg_g - api_pure_mg_g
```

The weighed-material composition must sum to:

```text
api_ds_total_mg_g + snac_mg_g + niacinamide_mg_g + glidant_mg_g + balance_mg_g = 1000 mg/g
```

Component names are user-defined. Do not hard-code SNAC, niacinamide, or glidant as mandatory. However, if components named SNAC and/or Niacinamide are present, show specific API-SNAC and API-Niacinamide diagnostics.

For generic formulations, use "API vs each non-API non-balance component" diagnostics.

## 4. v1 scope

### In scope

- Component setup
- API selection
- API content correction
- Calculated balance component
- Product strengths / nominal recipes
- Component constraints
- Preferred number of levels per component
- Candidate composition generation
- Constrained calibration design selection
- Optional inclusion of target-strength batches
- API-excipient correlation diagnostics
- API VIF diagnostic
- API specificity scatter plots
- Batch reuse across product-strength models
- Manual design editing
- Batch weighing calculations
- CSV outputs
- PNG plots
- Timestamped output folders
- `run_configuration.json`
- Beta ZIP packaging script

### Out of scope for v1

- PLS model building
- NIR spectral import
- HPLC/reference result import
- validation design
- robustness design
- spectral preprocessing
- RMSEP/SEP/bias calculation
- regulatory reporting
- database integration
- instrument connection
- dynamic LIW feeder profiles

## 5. User input sections

### Section 1 — Component setup

Inputs:

1. Number of components
2. Component names
3. Select API component
4. API content mg/mg
5. Select calculated balance component

Rules:

- Exactly one API component must be selected.
- Exactly one balance component must be selected.
- API content must be > 0 and normally <= 1.0, but values > 1.0 should be allowed with a warning rather than a hard fail.
- Component names must be unique and non-empty.

### Section 2 — Product strengths

Inputs:

1. Number of target strengths
2. Strength name
3. Nominal component concentrations in mg/g for each strength

Rules:

- API nominal value is pure API mg/g.
- If a balance component is selected, its nominal value should be calculated from the other components and API drug-substance correction.
- The app should display both `api_pure_mg_g` and `api_ds_total_mg_g`.

Example:

```text
Strength: 3%
API pure: 30 mg/g
API content: 0.80 mg/mg
API DS total: 37.5 mg/g
```

### Section 3 — Component constraints

Inputs:

1. Minimum and maximum level for each component
2. Preferred number of levels for each component

Rules:

- API constraints are on pure API mg/g.
- Non-API constraints are on actual component mg/g.
- Balance constraints are on calculated balance mg/g.
- Preferred number of levels guides candidate generation but is not a hard constraint.
- Minimum must be <= maximum.
- Preferred number of levels must be integer >= 1.

Candidate generation:

- For each non-balance component, generate levels using evenly spaced values from min to max based on preferred number of levels.
- API levels are pure API levels.
- For each candidate, calculate API DS total and calculated balance.
- Retain candidate only if calculated balance is within balance min/max and total weighed composition equals 1000 mg/g within numerical tolerance.

### Section 4 — Calibration design objective settings

Use toggles.

Inputs:

1. Use constrained mixture design
2. Reduce API-excipient correlation
3. Improve API specificity
4. Include target strengths in calibration design
5. Allow calibration batches to be reused across product-strength models
6. Reduce redundant overlap between product strengths
7. Minimize API material consumption
8. Prefer fewer calibration batches
9. Allow non-nominal excipient ratios

Default values:

```text
Use constrained mixture design: ON
Reduce API-excipient correlation: ON
Improve API specificity: ON
Include target strengths: OFF
Allow reuse across strength-specific PLS models: ON
Reduce redundant overlap between strengths: ON
Minimize API material consumption: OFF
Prefer fewer calibration batches: OFF
Allow non-nominal excipient ratios: ON
```

### Section 5 — Batch number and batch size settings

Inputs:

1. Desired number of calibration batches
2. Minimum number of calibration batches
3. Maximum number of calibration batches
4. Default batch size
5. Batch size unit: g or kg
6. Allow different batch sizes
7. Minimum batch size
8. Maximum batch size
9. Include replicate batches
10. Number of replicate batches
11. Replicate type

Rules:

- Desired number must be within min/max.
- Batch size must be > 0.
- Replicates are optional.
- Replicates may be exact duplicate compositions but should receive unique batch IDs and clear roles.

### Section 6 — Manual design editing

Actions:

1. Add manual batch
2. Edit generated batch
3. Delete batch
4. Lock batch
5. Mark batch as forced
6. Mark batch as reusable across strengths
7. Assign batch to one or more product-strength models
8. Mark batch as derived / mixed batch
9. Recalculate diagnostics

Rules:

- Manual edits must immediately revalidate composition feasibility.
- Locked batches must not be removed or changed by the design engine.
- Forced batches must remain in the design even if they worsen correlation; diagnostics should warn rather than remove them.

## 6. Core calculations

### API content correction

```text
api_ds_total_mg_g = api_pure_mg_g / api_content_mg_mg
api_impurity_mg_g = api_ds_total_mg_g - api_pure_mg_g
```

### Balance calculation

```text
balance_mg_g = 1000 - api_ds_total_mg_g - sum(other_non_api_non_balance_components_mg_g)
```

### Feasibility

A candidate is feasible if:

```text
abs(sum_weighed_components_mg_g - 1000) <= tolerance
all components within min/max
balance >= 0
```

Use tolerance such as `1e-6` for calculations and a display tolerance such as `0.001 mg/g`.

### Correlation diagnostics

Calculate pairwise Pearson correlations using the final design matrix.

Primary design matrix columns:

- API pure mg/g
- all non-API non-balance components mg/g
- balance mg/g

If API content is constant, do not include API DS total in the primary correlation matrix because it is perfectly linearly related to API pure.

Report:

- full correlation matrix;
- API vs each component;
- maximum absolute API-excipient correlation;
- specific API-SNAC and API-Niacinamide correlations if those names are present.

### VIF diagnostic

Calculate API VIF by regressing API pure mg/g against selected non-API non-balance components.

Do not include calculated balance in the default VIF calculation because mixture closure can create artificial perfect collinearity.

Formula:

```text
VIF_API = 1 / (1 - R2_API_from_excipients)
```

If `R2 >= 0.999999`, report VIF as infinite or very high.

Default thresholds:

```text
abs(correlation) > 0.80 = WARNING
abs(correlation) > 0.90 = CRITICAL
VIF_API > 5 = WARNING
VIF_API > 10 = CRITICAL
```

### Specificity diagnostics

At minimum, count and report:

- number of batches;
- number of API unique levels;
- number of non-API component unique levels;
- API range;
- whether API changes while at least one key excipient remains approximately constant;
- whether key excipients change while API remains approximately constant.

Approximate constancy tolerance may default to `1e-6` for exact generated grids and may be user-adjustable later.

### Design selection engine

v1 should implement a deterministic constrained candidate design approach.

Required behavior:

1. Generate feasible candidate compositions.
2. Include forced target-strength candidates if toggle is ON.
3. Include locked/manual batches.
4. Select additional candidates until desired batch count is reached.
5. Prefer candidates that improve:
   - API range coverage;
   - component level diversity;
   - low API-excipient correlations;
   - low API VIF;
   - API specificity contrasts;
   - model reuse efficiency;
   - practical material consumption if selected.

A simple deterministic greedy algorithm is acceptable for v1.

Do not implement a black-box stochastic optimizer as the only method. If randomness is used for candidate subsampling, use a fixed seed and store it in `run_configuration.json`.

## 7. Batch assignment and reuse logic

Each batch can be assigned to one or more strength-specific PLS models.

v1 should support:

- user assignment;
- automatic assignment based on API concentration proximity to target strengths;
- optional reuse across strength models.

A simple v1 approach is acceptable:

- assign each batch to the nearest strength by API pure mg/g;
- if reuse is enabled, also assign to neighboring strengths when API pure mg/g falls within an overlapping concentration window or is close to both target ranges.

The app must make assignments editable in the manual design editor.

## 8. Outputs

### Required CSV outputs

1. `calibration_design_table.csv`
2. `batch_weighing_sheet.csv`
3. `model_assignment_table.csv`
4. `correlation_matrix.csv`
5. `design_diagnostics_summary.csv`
6. `material_consumption_summary.csv`
7. `warnings.csv`

### Required PNG plots

1. `api_range_coverage.png`
2. `api_vs_each_excipient.png` or separate API-vs-component plots
3. `component_correlation_heatmap.png`
4. `material_consumption.png`
5. `batch_reuse_map.png`

Optional but preferred:

6. `batch_composition_stacked_bar.png`
7. `composition_pca_plot.png`

### `calibration_design_table.csv`

One row per batch.

Required columns:

```text
batch_id
batch_name
batch_role
source
locked
forced
derived_batch
parent_batch_a
parent_batch_b
fraction_from_a
assigned_strength_models
preparation_route
batch_size_kg
api_pure_mg_g
api_content_mg_mg
api_ds_total_mg_g
api_impurity_mg_g
<component>_mg_g columns for each non-API component
balance_mg_g
sum_weighed_components_mg_g
```

### `batch_weighing_sheet.csv`

Long format: one row per component per batch.

Required columns:

```text
batch_id
batch_size_kg
component_name
component_type
component_concentration_mg_g
component_mass_g
component_mass_kg
weighing_basis
api_content_mg_mg
```

### `model_assignment_table.csv`

Long format preferred.

Required columns:

```text
batch_id
strength_model
included
role_in_model
```

### `design_diagnostics_summary.csv`

Required columns:

```text
metric
value
threshold
status
interpretation
```

### `material_consumption_summary.csv`

Required columns:

```text
component
total_mass_g
total_mass_kg
```

For API include:

```text
API pure equivalent
API drug substance weighed
API impurity/material fraction
```

### `warnings.csv`

Required columns:

```text
severity
code
message
affected_batch_id
suggested_action
```

## 9. UI requirements

The UI must be usable by a scientist without editing JSON.

Use six input sections listed above.

Use output tabs or panels:

1. Design table
2. Diagnostics
3. Plots
4. Export/run folder

Minimum required buttons:

- Generate design
- Recalculate diagnostics
- Export design run
- Open output folder

The normal workflow should be simple and visible. Advanced diagnostic thresholds can be hidden or hard-coded in v1.

## 10. Packaging

Provide a script:

```text
scripts/make_beta_zip.py
```

The ZIP should include:

- `src/`
- `tests/`
- `examples/`
- `README.md`
- `BETA_INSTALLATION_GUIDE.md`
- `pyproject.toml`
- launch script if created

Exclude:

- `.venv/`
- `.git/`
- `__pycache__/`
- `.pytest_cache/`
- `outputs/`
- `dist/`
- `build/`
- `*.egg-info/`

## 11. Acceptance criteria for v1

The app is acceptable when:

1. A user can define components, API, API content, balance component, strengths, constraints, and batch counts.
2. The app generates feasible calibration batch compositions summing to 1000 mg/g on weighed-material basis.
3. API content correction is applied correctly.
4. Correlation and VIF diagnostics are calculated.
5. Target-strength inclusion toggle works.
6. Manual editing works at basic level.
7. Required CSV files are exported.
8. Required PNG plots are exported.
9. Tests pass.
10. A beta ZIP can be created.
