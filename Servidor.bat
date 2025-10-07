@echo off
cd /d "%~dp0"
setlocal
set "VENV_DIR=%~dp0.venv"
set "PYW=%VENV_DIR%\Scripts\pythonw.exe"
start "" "%PYW%" "%~dp0Launcher.pyw"
exit /b 0