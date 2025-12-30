# One-click runner for Slide-Voice-Maker (PowerShell)
# - Creates .venv if missing
# - Installs requirements
# - Runs src\main.py with optimized settings

$ErrorActionPreference = 'Stop'

Set-Location -LiteralPath $PSScriptRoot

# High-speed video encoding settings
$env:USE_VP8 = "1"
$env:VP9_CPU_USED = "8"
$env:VP9_CRF = "40"
$env:OUTPUT_FPS = "15"
$env:OUTPUT_MAX_WIDTH = "1280"
$env:SLIDE_RENDER_SCALE = "1.5"

$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $pythonExe)) {
  Write-Host "[INFO] Creating virtual environment: .venv"
  try {
    py -3.10 -m venv .venv
  } catch {
    python -m venv .venv
  }
}

Write-Host "[INFO] Installing dependencies..."
& $pythonExe -m pip install --quiet -r .\requirements.txt

Write-Host "[INFO] Running video generator (high-speed mode)..."
Write-Host "[INFO] Input folder: input\"
Write-Host "[INFO] Output folder: output\"
& $pythonExe .\src\main.py

Write-Host "[INFO] Done."
