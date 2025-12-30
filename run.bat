@echo off
setlocal enabledelayedexpansion

REM One-click runner for Slide-Voice-Maker (Windows)
REM - Creates .venv if missing
REM - Installs requirements
REM - Runs src\main.py with optimized settings

cd /d "%~dp0"

REM High-speed video encoding settings
set USE_VP8=1
set VP9_CPU_USED=8
set VP9_CRF=40
set OUTPUT_FPS=15
set OUTPUT_MAX_WIDTH=1280
set SLIDE_RENDER_SCALE=1.5

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating virtual environment: .venv
  py -3.10 -m venv .venv
  if errorlevel 1 (
    echo [WARN] py launcher failed. Trying: python -m venv .venv
    python -m venv .venv
  )
)

echo [INFO] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  pause
  exit /b 1
)

echo [INFO] Running video generator (high-speed mode)...
echo [INFO] Input folder: input\
echo [INFO] Output folder: output\
".venv\Scripts\python.exe" "src\main.py"

echo.
echo [INFO] Done.
pause
