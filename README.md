# CalibrationDesignerV3

CalibrationDesignerV3 is a desktop Python app for designing calibration batches for low-dose powder NIR reflectance PLS methods.

Version 1 focuses only on **calibration design**. It does not build PLS models, import spectra, import HPLC data, or generate validation/robustness protocols.

## Scientific purpose

The app helps scientists create calibration batch compositions that:

- respect constrained powder-mixture composition rules;
- sum to 1000 mg/g on actual weighed-material basis;
- correct API weighing amounts for API content/potency in mg/mg;
- reduce correlation between pure API and excipient levels;
- improve API specificity for low-dose NIR reflectance calibration;
- export design tables, weighing sheets, diagnostics, plots, and a run configuration.

## Units

All concentration inputs use `mg/g`.

Examples:

```text
10 mg/g = 1% w/w
30 mg/g = 3% w/w
60 mg/g = 6% w/w
1000 mg/g = 100% w/w
```

API target concentrations are entered as **pure API mg/g**.

API drug substance weighing is corrected by API content:

```text
api_ds_total_mg_g = api_pure_mg_g / api_content_mg_mg
```

Example:

```text
API pure target = 10 mg/g
API content = 0.80 mg/mg
API drug substance to weigh = 12.5 mg/g
```

## v1 input sections

1. Component setup
2. Product strengths
3. Component constraints
4. Calibration design objective settings
5. Batch number and batch size settings
6. Manual design editing

## v1 outputs

Each design run creates a timestamped folder under `outputs/`.

Required CSV files:

- `calibration_design_table.csv`
- `batch_weighing_sheet.csv`
- `model_assignment_table.csv`
- `correlation_matrix.csv`
- `design_diagnostics_summary.csv`
- `material_consumption_summary.csv`
- `warnings.csv`

Required plots:

- `api_range_coverage.png`
- `api_vs_each_excipient.png`
- `component_correlation_heatmap.png`
- `material_consumption.png`
- `batch_reuse_map.png`

Also saved:

- `run_configuration.json`

## Suggested development workflow

This project is intended to be built with Codex using the project-control files:

- `AGENTS.md`
- `SPEC.md`
- `BUILD_PLAN.md`
- `TEST_PLAN.md`
- `README.md`

Recommended pattern:

```text
Read the control files.
Implement the milestones in BUILD_PLAN.md.
Run pytest after each milestone.
Fix failures before proceeding.
Create beta ZIP at the end.
```

## Launch With uv

CalibrationDesignerV3 is managed with `uv`. Do not launch the app with Anaconda base Python.

Install `uv` if needed:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

From the project root:

```powershell
cd C:\Users\Erik\Documents\Projects\CalibrationDesignerV3
.\start_calibration_designer_v3.bat
```

The launcher runs `uv sync` and then starts the app with `uv run`. It intentionally never calls plain `python` or Anaconda base Python.

Equivalent manual commands:

```powershell
uv sync
uv run python calibration_designer_v3.py
```

Run tests:

```powershell
uv run python -m pytest
```

Run non-GUI smoke checks:

```powershell
uv run python calibration_designer_v3.py --smoke-test
uv run python calibration_designer_v3.py --input-smoke-test
```

Troubleshooting: if errors mention `C:\Users\Erik\anaconda3`, the app was not launched through uv. Use `start_calibration_designer_v3.bat` or `uv run python calibration_designer_v3.py`.

## Beta packaging

The final build should include:

```powershell
uv run python scripts\make_beta_zip.py
```

Expected output:

```text
dist/CalibrationDesignerV3_beta_YYYYMMDD_HHMMSS.zip
```

## Known v1 limitations

v1 intentionally excludes:

- PLS model training;
- spectral preprocessing;
- HPLC/reference result import;
- validation design;
- robustness design;
- regulatory report generation;
- instrument connectivity;
- dynamic LIW feeder profiles.

These can be added later if the v1 calibration-design workflow works well.
