# BUILD_PLAN.md — CalibrationDesignerV3 Build Plan

## Build strategy

Build the app milestone by milestone. Core scientific calculations must be implemented and tested before UI.

It is acceptable to ask Codex to execute all milestones in one session, but Codex must run tests after each milestone and fix failures before proceeding.

## Milestone 0 — Project scaffold

Goal: Create a clean Python project structure.

Tasks:

1. Create `pyproject.toml`.
2. Create package structure under `src/calibration_designer_v3/`.
3. Create test folder `tests/`.
4. Create scripts folder `scripts/`.
5. Create examples folder `examples/`.
6. Add `.gitignore`.
7. Add package `__init__.py`.
8. Add minimal CLI smoke entry point if useful.

Expected structure:

```text
CalibrationDesignerV3/
├─ AGENTS.md
├─ SPEC.md
├─ BUILD_PLAN.md
├─ TEST_PLAN.md
├─ README.md
├─ pyproject.toml
├─ src/
│  └─ calibration_designer_v3/
│     ├─ __init__.py
│     ├─ app.py
│     ├─ core/
│     ├─ io/
│     ├─ models/
│     ├─ plotting/
│     └─ ui/
├─ tests/
├─ scripts/
└─ examples/
```

Tests:

```text
python -m pytest
```

Acceptance:

- Project imports without errors.
- Empty or initial tests pass.

## Milestone 1 — Data models and validation

Goal: Implement validated configuration and domain models.

Suggested modules:

```text
src/calibration_designer_v3/models/config.py
src/calibration_designer_v3/models/domain.py
src/calibration_designer_v3/core/validation.py
```

Models should cover:

- ComponentSpec
- ProductStrength
- ComponentConstraint
- DesignObjectiveSettings
- BatchSettings
- CalibrationBatch
- RunConfig

Validation rules:

- exactly one API component;
- exactly one balance component;
- API content > 0;
- unique component names;
- min <= max;
- preferred levels >= 1;
- desired batch count within min/max.

Tests:

- valid config accepted;
- missing API rejected;
- missing balance rejected;
- duplicate component names rejected;
- invalid API content rejected;
- invalid constraints rejected.

Acceptance:

- Data models pass unit tests.
- No UI code depends on unvalidated dictionaries.

## Milestone 2 — Composition calculations and feasibility engine

Goal: Implement fundamental scientific calculations.

Suggested modules:

```text
src/calibration_designer_v3/core/composition.py
src/calibration_designer_v3/core/feasibility.py
```

Functions:

- `calculate_api_ds_total(api_pure_mg_g, api_content_mg_mg)`
- `calculate_api_impurity(api_pure_mg_g, api_content_mg_mg)`
- `calculate_balance(...)`
- `calculate_weighed_sum(...)`
- `is_feasible_candidate(...)`
- `calculate_component_masses(batch, batch_size_kg)`

Tests:

- 10 mg/g pure API with API content 0.80 gives 12.5 mg/g API DS.
- Calculated balance produces total 1000 mg/g.
- Negative balance is infeasible.
- Component outside min/max is infeasible.
- Component masses are correct for a known batch size.

Acceptance:

- All calculation tests pass.
- Numeric tolerance is explicit.

## Milestone 3 — Candidate composition generation

Goal: Generate feasible candidate compositions from constraints and preferred levels.

Suggested module:

```text
src/calibration_designer_v3/core/candidate_generation.py
```

Behavior:

1. Generate level grids for API pure and all non-API non-balance components.
2. Calculate API DS total.
3. Calculate balance.
4. Retain feasible candidates.
5. Deduplicate candidates.
6. Cap candidate count if needed using deterministic thinning.

Tests:

- Expected number of candidates for simple constraints.
- Infeasible candidates removed.
- Balance constraints respected.
- Candidate generation deterministic.

Acceptance:

- Candidate generation handles at least 3 to 8 components.
- Candidate generation does not crash if one component has one preferred level.

## Milestone 4 — Design selection engine

Goal: Select calibration batches from feasible candidates.

Suggested module:

```text
src/calibration_designer_v3/core/design_engine.py
```

Required behavior:

1. Include locked/manual batches.
2. Include target-strength batches if toggle is ON.
3. Select additional candidates to reach desired batch count.
4. Use a deterministic greedy score.
5. Prefer low API-excipient correlation, API range coverage, component diversity, and practical feasibility.
6. Assign batch IDs such as `CAL-001`.

Design scoring can be simple but must be documented in code comments.

Tests:

- Design contains desired number of batches when enough candidates exist.
- Target strengths are included when toggle is ON.
- Target strengths are not forced when toggle is OFF.
- Locked batches persist.
- Same inputs give same design.

Acceptance:

- Engine returns a design object with batches, diagnostics placeholders, warnings.

## Milestone 5 — Correlation, VIF, and API specificity diagnostics

Goal: Implement diagnostic calculations.

Suggested module:

```text
src/calibration_designer_v3/core/diagnostics.py
```

Diagnostics:

- pairwise correlation matrix;
- API vs each excipient correlation;
- API VIF excluding calculated balance by default;
- maximum absolute API-excipient correlation;
- unique levels by component;
- API range;
- warning generation based on thresholds.

Tests:

- known correlation cases return expected values;
- collinear design gives high VIF;
- non-collinear design gives lower VIF;
- high correlation produces warning/critical warning;
- constant component handled gracefully.

Acceptance:

- Diagnostics produce tables ready for export and UI display.

## Milestone 6 — Batch assignment and reuse logic

Goal: Assign calibration batches to product-strength PLS models.

Suggested module:

```text
src/calibration_designer_v3/core/assignment.py
```

Behavior:

- Assign each batch to nearest strength by API pure mg/g.
- If reuse toggle ON, allow assignment to neighboring strength models using deterministic overlap logic.
- Create a long-format model assignment table.
- Allow manual assignment metadata in batch model.

Tests:

- nearest-strength assignment works.
- reuse toggle changes assignment count.
- model assignment table exports correctly.

Acceptance:

- Every batch is assigned to at least one model.

## Milestone 7 — Output writer and plots

Goal: Export full design run package.

Suggested modules:

```text
src/calibration_designer_v3/io/export.py
src/calibration_designer_v3/plotting/plots.py
```

Required CSV files:

- `calibration_design_table.csv`
- `batch_weighing_sheet.csv`
- `model_assignment_table.csv`
- `correlation_matrix.csv`
- `design_diagnostics_summary.csv`
- `material_consumption_summary.csv`
- `warnings.csv`

Required PNG plots:

- `api_range_coverage.png`
- `api_vs_each_excipient.png`
- `component_correlation_heatmap.png`
- `material_consumption.png`
- `batch_reuse_map.png`

Also save:

- `run_configuration.json`

Tests:

- export creates timestamped folder;
- all required CSV files exist;
- all required PNG files exist;
- `run_configuration.json` exists and includes seed/settings;
- exported composition table sums to 1000 mg/g.

Acceptance:

- A complete run folder can be generated without launching UI.

## Milestone 8 — Desktop UI

Goal: Build simple desktop UI.

Suggested module:

```text
src/calibration_designer_v3/ui/main_window.py
src/calibration_designer_v3/app.py
```

UI sections:

1. Component setup
2. Product strengths
3. Component constraints
4. Calibration design objective settings
5. Batch number and batch size settings
6. Manual design editing

Output panels:

- Design table
- Diagnostics
- Plots
- Export/run folder

Required buttons:

- Generate design
- Recalculate diagnostics
- Export design run
- Open output folder

Rules:

- Keep calculation logic out of UI files.
- UI must call validated models and core functions.
- App must not crash on missing logo.

Tests:

- At minimum, import/smoke tests for UI.
- If GUI testing is difficult, create non-interactive smoke tests for app construction.

Acceptance:

- App can be launched locally.
- User can generate a design from example/default inputs.

## Milestone 9 — UX polish and examples

Goal: Make the app comfortable for beta use.

Tasks:

1. Add example project/input configuration.
2. Add "Load example" action if simple.
3. Improve warning messages.
4. Keep bottom action bar visible.
5. Ensure plots have readable labels and legends outside data area where needed.
6. Add BETA_INSTALLATION_GUIDE.md.

Tests:

- Example config generates design and output folder.
- Full test suite passes.

Acceptance:

- A new user can run the app and generate an example design.

## Milestone 10 — Beta packaging

Goal: Create a beta ZIP package.

Tasks:

1. Create `scripts/make_beta_zip.py`.
2. Exclude `.venv`, `.git`, `outputs`, `dist`, caches, build artifacts.
3. Include source, tests, examples, README, beta guide, pyproject, launch script if present.
4. Create ZIP in `dist/`.

Tests:

- Run package script.
- Confirm ZIP exists.
- Confirm excluded folders are not included.

Acceptance:

- `dist/CalibrationDesignerV3_beta_YYYYMMDD_HHMMSS.zip` exists.
- Full test suite passes before package creation.

## Final acceptance command sequence

Codex should run equivalent commands:

```text
python -m pytest
python -m calibration_designer_v3 --smoke-test
python scripts/make_beta_zip.py
```

If `python -m calibration_designer_v3 --smoke-test` is not implemented, implement an equivalent smoke command and document it.
