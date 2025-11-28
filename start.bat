@echo off
title ComfyUI CivitAI Downloader
echo Launching ComfyUI CivitAI Downloader...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

REM Check/Install dependencies
python -c "import yaml; import rich" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM Run the script
echo.
python download.py %*

REM Pause only if there was an error (exit code != 0)
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The script encountered an error.
    pause
)

if %errorlevel% neq 0 (
    pause
)
