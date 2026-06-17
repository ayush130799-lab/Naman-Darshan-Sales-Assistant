# run.ps1 — Naman Darshan Sales AI launcher
# The myenv was built on a different machine so its Scripts/ launcher is broken.
# This script uses Python directly with PYTHONPATH instead.
#
# Usage (from project folder):
#   .\run.ps1

$PROJECT      = Split-Path -Parent $MyInvocation.MyCommand.Path
$SITE_PKG     = "$PROJECT\myenv\Lib\site-packages"
$PYTHON       = "C:\Python314\python.exe"

if (-not (Test-Path $PYTHON)) {
    Write-Error "Python 3.14 not found at $PYTHON. Edit the `$PYTHON line in run.ps1 to match your install path."
    exit 1
}

$env:PYTHONPATH                      = $SITE_PKG
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

Write-Host "Starting Naman Darshan Sales AI on http://localhost:8501 ..." -ForegroundColor Cyan
Set-Location $PROJECT
& $PYTHON -m streamlit run app.py
