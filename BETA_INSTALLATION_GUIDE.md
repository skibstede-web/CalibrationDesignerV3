# BETA_INSTALLATION_GUIDE.md

## 1) Requirements

- Windows 10/11
- Python 3.10+
- Internet access for initial dependency install

## 2) Install

From project root:

```powershell
cd C:\Users\Erik\Documents\Projects\CalibrationDesignerV3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 3) Run tests

```powershell
python -m pytest
```

## 4) Launch app

```powershell
python -m calibration_designer_v3
```

## 5) Run smoke check

```powershell
python -m calibration_designer_v3 --smoke-test
```

## 6) Example configuration

Example config file is provided at:

- `examples/example_run_config.json`

## 7) Output folder

Each export creates a new folder under:

- `outputs/design_run_YYYYMMDD_HHMMSS`

## 8) Beta zip

Create a beta package:

```powershell
python scripts\make_beta_zip.py
```

Zip output:

- `dist/CalibrationDesignerV3_beta_YYYYMMDD_HHMMSS.zip`