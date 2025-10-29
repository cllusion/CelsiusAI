@echo off
title Celsius AI - Master Launcher
color 0A
cls

echo.
echo ========================================================================
echo            🛡️ CELSIUS AI - MASTER LAUNCHER 🛡️
echo ========================================================================
echo.
echo                Personal Cybersecurity Defense Assistant
echo                    Guardian Overwatch System
echo.
echo ========================================================================
echo.

REM Set base directory to project root
cd /d "%~dp0..\"
set CELSIUS_DIR=%cd%
set TIMESTAMP=%date:~-4,4%-%date:~-10,2%-%date:~-7,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%
set LOG_FILE=logs\celsius_master_launch_%TIMESTAMP%.log

echo [%time%] Celsius AI Master Launcher Starting... > %LOG_FILE%
echo [%time%] Working Directory: %CELSIUS_DIR% >> %LOG_FILE%

REM Create necessary directories
if not exist "logs" mkdir logs
if not exist "data" mkdir data

echo 🔍 System Check Phase...
echo [%time%] Starting system check... >> %LOG_FILE%

REM Check Python installation
echo    • Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ Python not found! Please install Python 3.8+ and ensure it's in PATH
    echo [%time%] ERROR: Python not found >> %LOG_FILE%
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo    ✅ Found Python %%i
    echo [%time%] Python version check passed >> %LOG_FILE%
)

echo.
echo 🔧 Dependency Check Phase...
echo    • Ensuring all dependencies are installed...
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo    ⚠️  Warning: Some packages may not have installed correctly
    echo [%time%] Warning: Dependency installation issues >> %LOG_FILE%
) else (
    echo    ✅ All dependencies satisfied
    echo [%time%] All dependencies satisfied >> %LOG_FILE%
)

echo.
echo ========================================================================
echo                   🚀 LAUNCHING GUARDIAN OVERWATCH
echo ========================================================================
echo.
echo The Guardian will now start and manage all Celsius AI services:
echo    • Real-Time Defender (Antivirus/Firewall Protection)
echo    • Ultimate Hub (GUI Control Center)
echo    • Enhanced Dashboard (Web Interface)
echo    • Core AI Engine
echo    • Web Learning System
echo    • Hourly Reporter (System Monitoring)
echo.
echo The Guardian monitors all services and automatically restarts them
echo if they crash or become unresponsive.
echo.
echo IMPORTANT: When you close Guardian, all services will CONTINUE RUNNING.
echo To stop services, use the Ultimate Hub or close them individually.
echo (To stop services with Guardian, use: --shutdown-services flag)
echo.
echo To stop all services, close the Guardian window or press Ctrl+C
echo.
echo ========================================================================
echo.

echo 🛡️ Starting Guardian Overwatch...
echo [%time%] Launching Guardian... >> %LOG_FILE%

REM Set environment variable for auto-login
set CELSIUS_AUTO_LOGIN=true

REM Launch the Guardian (which will manage everything else)
python src/guardian/celsius_ultimate_guardian.py

echo.
echo [%time%] Guardian shutdown complete >> %LOG_FILE%
echo.
echo ✅ Celsius AI system has been shut down gracefully.
echo.
pause
