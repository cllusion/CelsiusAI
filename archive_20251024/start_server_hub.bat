@echo off
title Celsius AI Server Hub Launcher

echo ================================================
echo    CELSIUS AI SERVER HUB LAUNCHER
echo ================================================
echo.

cd /d "%~dp0"

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or later
    echo.
    pause
    exit /b 1
)

echo Python found. Starting Celsius Server Hub...
echo.
echo Login Credentials:
echo   Username: cllusion001  
echo   Password: T3qy22ny*@dyu0ppn*pG
echo.
echo Available Launch Options:
echo   [1] Server Hub Only
echo   [2] Unified Launcher (GUI) - Recommended
echo   [3] System Tray Mode
echo   [4] Activate Defense System
echo.
set /p choice="Choose launch option (1-4): "

if "%choice%"=="1" (
    echo Starting Server Hub Only...
    python celsius_server_hub.py
) else if "%choice%"=="2" (
    echo Starting Unified Launcher...
    python celsius_unified_launcher.py
) else if "%choice%"=="3" (
    echo Starting System Tray Mode...
    python celsius_unified_launcher.py --tray
) else if "%choice%"=="4" (
    echo Activating Defense System...
    python celsius_defense_manager.py
) else (
    echo Starting Unified Launcher (default)...
    python celsius_unified_launcher.py
)

echo.
echo Application has closed.
pause