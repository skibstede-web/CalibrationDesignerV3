# TEST_PLAN.md — CalibrationDesignerV3 Test Plan

## Test philosophy

The scientific calculation engine must be testable without launching the desktop UI.

Use `pytest`.

Tests should be deterministic and should not depend on internet access.

## 1. Data model tests

Test file suggestion:

```text
tests/test_models.py
```

Required tests:

1. Valid configuration is accepted.
2. Duplicate component names are rejected.
3. No API selected is rejected.
4. More than one API selected is rejected.
5. No balance component selected is rejected.
6. More than one balance component selected is rejected.
7. API content <= 0 is rejected.
8. Constraint min > max is rejected.
9. Preferred number of levels < 1 is rejected.
10. Desired batch count outside min/max is rejected.

## 2. API content and composition tests

Test file suggestion:

```text
tests/test_composition.py
```

Required tests:

1. `api_pure_mg_g = 10` and `api_content = 0.80` gives `api_ds_total = 12.5`.
2. API impurity is `2.5 mg/g` in the same example.
3. Calculated balance gives total `1000 mg/g`.
4. Negative calculated balance is infeasible.
5. Candidate outside component min/max is infeasible.
6. Weighing masses are correct:
   - 10 kg batch
   - 12.5 mg/g API DS gives 125 g API DS.

## 3. Candidate generation tests

Test file suggestion:

```text
tests/test_candidate_generation.py
```

Required tests:

1. Candidate generation returns feasible candidates.
2. All candidates sum to 1000 mg/g on weighed-material basis.
3. API levels use pure API basis.
4. Balance constraint is respected.
5. One-level fixed components are handled.
6. Candidate generation is deterministic.
7. Duplicate candidates are removed.

## 4. Design engine tests

Test file suggestion:

```text
tests/test_design_engine.py
```

Required tests:

1. Design contains desired number of batches when enough candidates exist.
2. If fewer candidates exist than desired, app returns available candidates with warning.
3. Target strengths are included when toggle is ON.
4. Target strengths are not forced when toggle is OFF.
5. Locked/manual batches are preserved.
6. Forced batches are preserved.
7. Same inputs produce same selected batch IDs and compositions.
8. Design engine does not select infeasible candidates.

## 5. Correlation and VIF diagnostics tests

Test file suggestion:

```text
tests/test_diagnostics.py
```

Required tests:

1. Pairwise correlation matrix has correct shape.
2. API-excipient correlation is detected.
3. High correlation produces warning.
4. Critical correlation produces critical warning.
5. API VIF is high for a deliberately collinear design.
6. API VIF is lower for a more orthogonal design.
7. Constant components do not crash diagnostics.
8. Calculated balance is excluded from default API VIF.

## 6. Batch assignment and reuse tests

Test file suggestion:

```text
tests/test_assignment.py
```

Required tests:

1. Each batch is assigned to nearest strength model.
2. Reuse ON increases or maintains assignment count.
3. Reuse OFF assigns only nearest model unless manually assigned.
4. Model assignment table is long format and contains expected columns.
5. Manual assignment metadata is respected.

## 7. Output tests

Test file suggestion:

```text
tests/test_exports.py
```

Required tests:

1. Export creates timestamped run folder.
2. Required CSV files are created:
   - `calibration_design_table.csv`
   - `batch_weighing_sheet.csv`
   - `model_assignment_table.csv`
   - `correlation_matrix.csv`
   - `design_diagnostics_summary.csv`
   - `material_consumption_summary.csv`
   - `warnings.csv`
3. Required PNG plots are created:
   - `api_range_coverage.png`
   - `api_vs_each_excipient.png`
   - `component_correlation_heatmap.png`
   - `material_consumption.png`
   - `batch_reuse_map.png`
4. `run_configuration.json` is created.
5. Exported compositions sum to 1000 mg/g.
6. Exported API DS total uses API content correction.
7. Material consumption summary includes API pure equivalent and API drug substance weighed.

## 8. UI smoke tests

Test file suggestion:

```text
tests/test_ui_smoke.py
```

Required tests:

1. UI module imports.
2. Main app object can be constructed without launching blocking mainloop, if possible.
3. Missing logo does not crash UI.
4. Example/default input can generate a design through non-UI backend.

## 9. Packaging tests

Test file suggestion:

```text
tests/test_packaging.py
```

Required tests:

1. `scripts/make_beta_zip.py` can be imported or run.
2. ZIP is created in `dist/`.
3. ZIP excludes:
   - `.venv`
   - `.git`
   - `__pycache__`
   - `.pytest_cache`
   - `outputs`
   - `dist`
   - `build`
   - `*.egg-info`
4. ZIP includes:
   - `src`
   - `tests`
   - `examples`
   - `README.md`
   - `BETA_INSTALLATION_GUIDE.md`
   - `pyproject.toml`

## 10. Full regression command

Use:

```text
python -m pytest
```

Before beta packaging:

```text
python -m pytest
python scripts/make_beta_zip.py
```

## 11. Manual acceptance checks

After tests pass, manually check:

1. App launches on Windows.
2. Example design can be generated.
3. Output folder opens.
4. Plots are readable.
5. CSV files open in Excel.
6. Warnings are understandable.
7. No UI section is overwhelming for v1.
