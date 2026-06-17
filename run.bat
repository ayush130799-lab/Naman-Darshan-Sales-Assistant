@echo off
REM run.bat — Naman Darshan Sales AI launcher
REM Double-click this file OR run it from the project folder.

set PROJECT=%~dp0
set SITE_PKG=%PROJECT%myenv\Lib\site-packages
set PYTHON=C:\Python314\python.exe

if not exist "%PYTHON%" (
    echo ERROR: Python 3.14 not found at %PYTHON%
    echo Edit the PYTHON= line in run.bat to match your install path.
    pause
    exit /b 1
)

set PYTHONPATH=%SITE_PKG%
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

echo Starting Naman Darshan Sales AI on http://localhost:8501 ...
cd /d "%PROJECT%"
"%PYTHON%" -m streamlit run app.py
pause