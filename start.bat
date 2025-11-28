@echo off
echo Launching ComfyUI CivitAI Downloader...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Check/Install dependencies
python -c "import yaml; import rich" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Run the script
python download.py %*
if %errorlevel% neq 0 (
    pause
)
