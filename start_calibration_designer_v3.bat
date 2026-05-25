@echo off
setlocal

cd /d "%~dp0"

set "PY_CMD="
set "PY_ARGS="
set "LOG_FILE=%~dp0launch_error.log"
set "ANACONDA_PY=%USERPROFILE%\anaconda3\python.exe"

if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else if exist "%ANACONDA_PY%" (
    set "PY_CMD=%ANACONDA_PY%"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py"
        set "PY_ARGS=-3"
    ) else (
        where python >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD=python"
        )
    )
)

if "%PY_CMD%"=="" (
    echo Python was not found. > "%LOG_FILE%"
    echo Create the virtual environment first: >> "%LOG_FILE%"
    echo   C:\Users\Erik\anaconda3\python.exe -m venv .venv >> "%LOG_FILE%"
    echo   .\.venv\Scripts\Activate.ps1 >> "%LOG_FILE%"
    echo   python -m pip install -e ".[dev]" >> "%LOG_FILE%"
    type "%LOG_FILE%"
    pause
    exit /b 1
)

if exist "%LOG_FILE%" del "%LOG_FILE%" >nul 2>&1

%PY_CMD% %PY_ARGS% -m calibration_designer_v3 %* 1>"%LOG_FILE%" 2>&1
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Launch failed with code %EXIT_CODE%.
    echo Details:
    type "%LOG_FILE%"
    echo.
    echo Full log saved to: %LOG_FILE%
    pause
)

exit /b %EXIT_CODE%