@echo off
REM Starts the Grocery Shop Management System backend server on Windows.
REM Double-click this file, or run it from Command Prompt / PowerShell.

cd /d "%~dp0backend"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Starting server with: python server.py
    python server.py
    goto :end
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Starting server with: python3 server.py
    python3 server.py
    goto :end
)

echo Python was not found on this system.
echo Please install Python 3.8+ from https://python.org (check "Add Python to PATH" during setup) and try again.
pause

:end
pause
