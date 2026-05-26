# BETA_INSTALLATION_GUIDE.md

## 1) Requirements

- Windows 10/11
- Internet access for the first `uv sync`
- `uv` installed and available on `PATH`

Install `uv` if needed:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 2) Install And Launch

1. Unzip the beta package.
2. Open the unzipped `CalibrationDesignerV3` folder.
3. Double-click:

```text
start_calibration_designer_v3.bat
```

The launcher runs `uv sync` and starts the app with `uv run python calibration_designer_v3.py`.

## 3) Manual Commands

From the project root:

```powershell
uv sync
uv run python calibration_designer_v3.py
```

Run tests:

```powershell
uv run python -m pytest
```

Run smoke checks:

```powershell
uv run python calibration_designer_v3.py --smoke-test
uv run python calibration_designer_v3.py --input-smoke-test
```

## 4) Troubleshooting

If startup errors mention `C:\Users\Erik\anaconda3`, the app was not launched through uv. Use `start_calibration_designer_v3.bat` or the manual `uv run` command above.

If a beta issue occurs, send back:

- `launch_error.log`, if present
- a screenshot of the error
- `run_configuration.json`, if a run folder was created
- `warnings.csv`, if a run folder was created
- a short description of the inputs used

## 5) Example Configuration

Example config file:

```text
examples/example_run_config.json
```

## 6) Output Folder

Each export creates a new folder under:

```text
outputs/design_run_YYYYMMDD_HHMMSS
```

## 7) Beta ZIP

Create a beta package:

```powershell
uv run python scripts\make_beta_zip.py
```

Zip output:

```text
dist/CalibrationDesignerV3_beta_YYYYMMDD_HHMMSS.zip
```
