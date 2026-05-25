# CODEX_START_PROMPT.md — Paste this into Codex

You are working in the root folder of this project:

```text
C:\Users\Erik\Documents\Projects\CalibrationDesignerV3
```

Read these files first:

- AGENTS.md
- SPEC.md
- BUILD_PLAN.md
- TEST_PLAN.md
- README.md

Build **CalibrationDesignerV3** from end to end by executing all milestones in BUILD_PLAN.md.

Important rules:

1. Follow AGENTS.md and SPEC.md strictly.
2. Implement milestones sequentially.
3. After each milestone, run the relevant tests.
4. Fix failing tests before continuing.
5. Do not implement out-of-scope features:
   - no PLS model training;
   - no spectral import;
   - no HPLC import;
   - no robustness module;
   - no validation module;
   - no regulatory report generator.
6. Keep scientific calculation logic out of UI files.
7. Use deterministic behavior: same inputs must give same design.
8. Save outputs in timestamped run folders.
9. Create a beta ZIP at the end.

Expected final deliverables:

- working Python project;
- desktop app;
- tests passing with `python -m pytest`;
- example input/configuration;
- CSV outputs;
- PNG plots;
- `run_configuration.json`;
- `scripts/make_beta_zip.py`;
- beta ZIP in `dist/`.

When you need to install dependencies, create and use a local virtual environment in the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

At the end, run:

```powershell
python -m pytest
python -m calibration_designer_v3 --smoke-test
python scripts\make_beta_zip.py
```

If the smoke-test command does not exist yet, implement it.

Final response must summarize:

1. files created or changed;
2. test commands run;
3. test results;
4. app launch command;
5. beta ZIP path;
6. known limitations.
