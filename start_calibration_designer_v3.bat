@echo off
setlocal

cd /d "%~dp0"

set "LOG_FILE=%~dp0launch_error.log"
if exist "%LOG_FILE%" del "%LOG_FILE%" >nul 2>&1

where uv >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: uv is not installed or not available on PATH.
    echo Please install uv first:
    echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    pause
    exit /b 1
)

echo.
echo Syncing CalibrationDesignerV3 environment with uv...
uv sync 1>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: uv sync failed.
    echo Details:
    type "%LOG_FILE%"
    pause
    exit /b 1
)

echo.
echo Starting CalibrationDesignerV3...
uv run python calibration_designer_v3.py %* 1>>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: CalibrationDesignerV3 exited with an error.
    echo Details:
    type "%LOG_FILE%"
    pause
    exit /b 1
)

endlocal
