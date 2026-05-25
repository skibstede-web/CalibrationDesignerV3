# AGENTS.md — CalibrationDesignerV3

## Project identity

You are building **CalibrationDesignerV3**, a desktop Python app for designing calibration batches for low-dose powder analysis by near-infrared (NIR) reflectance spectroscopy and PLS model development.

The app is for scientific use in pharmaceutical development laboratories. Version 1 is deliberately simple and covers **calibration design only**. Do not implement robustness design, validation design, PLS model training, spectral preprocessing, HPLC result import, regulatory report generation, or instrument connectivity in v1.

## Scientific purpose

The app helps scientists design calibration batch compositions that:

1. respect constrained powder-mixture composition rules;
2. sum to 1000 mg/g on an actual weighed-material basis;
3. account for API content/potency in mg/mg;
4. reduce correlation between pure API concentration and excipient concentrations;
5. improve API specificity for low-dose NIR reflectance PLS calibration;
6. generate practical batch weighing sheets and output files.

## Core scientific definitions

- All formulation concentrations are in **mg/g**.
- `1000 mg/g` equals `100% w/w`.
- API targets are entered as **pure API mg/g**.
- API content is entered as **mg pure API / mg API drug substance**, unit mg/mg.
- Actual weighed API drug substance is calculated as:

```text
api_ds_total_mg_g = api_pure_mg_g / api_content_mg_mg
```

- The weighed-material mixture constraint is:

```text
api_ds_total_mg_g + sum(non_api_non_balance_components_mg_g) + balance_mg_g = 1000 mg/g
```

- The balance component is calculated, not independently varied, unless later explicitly changed in future versions.

## Architecture rules

Use a modular Python `src/` layout:

```text
src/
└─ calibration_designer_v3/
   ├─ __init__.py
   ├─ app.py
   ├─ core/
   ├─ io/
   ├─ models/
   ├─ plotting/
   └─ ui/
```

Recommended test layout:

```text
tests/
```

Recommended scripts:

```text
scripts/
```

Do not put scientific calculation logic directly in UI files. The UI collects inputs, validates them, calls tested core functions, and displays/exports results.

## Technology choices

Use Python.

Prefer common, stable packages:

- `numpy`
- `pandas`
- `matplotlib`
- `scikit-learn`
- `pydantic`
- `pytest`
- `customtkinter` for desktop UI if available; otherwise use `tkinter` fallback

Do not require proprietary software.

The app must run locally on Windows from the project folder.

## Deterministic behavior

Same inputs must produce the same design unless the user explicitly changes a seed or settings. Use a fixed default seed.

## Output philosophy

Each design run must create a timestamped output folder:

```text
outputs/
└─ design_run_YYYYMMDD_HHMMSS/
```

Each run should save:

- CSV outputs;
- PNG plots;
- `run_configuration.json`;
- `warnings.csv`;
- `design_diagnostics_summary.csv`.

Never overwrite a previous run folder.

## Warning philosophy

Do not fail the entire design because of every concern.

Use clear severity levels:

- `PASS`: acceptable
- `INFO`: informative issue
- `WARNING`: scientifically or practically concerning but not impossible
- `CRITICAL`: serious issue requiring user review
- `FAIL`: design cannot be generated or violates hard constraints

Hard failures include:

- no API component selected;
- no balance component selected;
- API content <= 0;
- infeasible component constraints;
- generated composition cannot sum to 1000 mg/g;
- negative calculated balance;
- no feasible candidates.

High API-excipient correlation is normally a warning or critical warning, not an automatic failure.

## UI/UX principles

Keep v1 simple.

Use six visible input sections:

1. Component setup
2. Product strengths
3. Component constraints
4. Calibration design objective settings
5. Batch number and batch size settings
6. Manual design editing

Use collapsible advanced panels only when needed.

Use a top bar with app name. If `src/calibration_designer_v3/assets/logo.png` exists, display it; if not, do not crash.

Use a sticky bottom action bar with primary actions:

- Generate design
- Recalculate diagnostics
- Export design run
- Open output folder

## Plotting rules

Generate plots both in the UI and as PNG files in the run folder.

Use `matplotlib`.

Do not let legends cover data points. Put legends outside the plotting area when useful:

```python
ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), borderaxespad=0.0)
fig.savefig(path, bbox_inches="tight")
```

## Testing rules

Use `pytest`.

Core calculations must have unit tests before or alongside UI implementation.

At minimum, test:

- API content correction;
- composition sums to 1000 mg/g;
- candidate generation under constraints;
- infeasible constraints;
- correlation diagnostics;
- VIF diagnostics;
- target-strength inclusion toggle;
- output file generation;
- plot file generation;
- deterministic behavior.

## Build discipline

Follow `BUILD_PLAN.md`.

Implement milestones sequentially. It is acceptable to run them in one Codex session, but do not skip tests between milestones. Fix failing tests before proceeding.

When finished, summarize:

1. files created or changed;
2. tests run;
3. test result;
4. launch instructions;
5. known limitations;
6. beta ZIP path.
