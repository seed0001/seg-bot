@echo off
cd /d "%~dp0"

REM Use the Python launcher if available, otherwise fall back to python on PATH
where py >nul 2>nul
if %errorlevel%==0 (
    py app.py
) else (
    python app.py
)

pause
