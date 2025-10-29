@echo off
title Celsius AI - Ultimate Launcher
color 0B
cls

echo.
echo ========================================================================
echo                      🛡️  CELSIUS AI - ULTIMATE LAUNCHER  🛡️
echo ========================================================================
echo.
echo                    Personal Cybersecurity Defense Assistant
echo                         Complete System Initialization
echo.
echo ========================================================================
echo.

REM Set base directory to project root
cd /d "%~dp0..\"
set CELSIUS_DIR=%cd%
set TIMESTAMP=%date:~-4,4%-%date:~-10,2%-%date:~-7,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%
set LOG_FILE=logs\celsius_launch_%TIMESTAMP%.log

echo [%time%] Celsius AI Ultimate Launcher Starting... > %LOG_FILE%
echo [%time%] Working Directory: %CELSIUS_DIR% >> %LOG_FILE%

REM Create necessary directories
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
if not exist "temp" mkdir temp

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

REM Check critical files
echo    • Checking critical system files...
set CRITICAL_FILES=src\hub\celsius_ultimate_hub.py src\core\main.py src\dashboard\enhanced_mobile_dashboard.py src\guardian\celsius_ultimate_guardian.py
for %%f in (%CRITICAL_FILES%) do (
    if exist "%CELSIUS_DIR%%%f" (
        echo    ✅ Found %%f
        echo [%time%] Found critical file: %%f >> %LOG_FILE%
    ) else (
        echo    ❌ Missing critical file: %%f
        echo [%time%] ERROR: Missing critical file: %%f >> %LOG_FILE%
        set MISSING_FILES=1
    )
)

if defined MISSING_FILES (
    echo.
    echo ❌ Critical files missing! Cannot continue.
    echo [%time%] Launch aborted due to missing files >> %LOG_FILE%
    pause
    exit /b 1
)

REM Check and install Python dependencies
echo.
echo 🔧 Dependency Check Phase...
echo [%time%] Starting dependency check... >> %LOG_FILE%

echo    • Installing/updating required packages from requirements.txt...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo    ❌ Failed to install packages from requirements.txt. Please check the file and your connection.
    echo [%time%] ERROR: Failed to install packages from requirements.txt >> %LOG_FILE%
    pause
    exit /b 1
) else (
    echo    ✅ All dependencies satisfied
    echo [%time%] All dependencies satisfied >> %LOG_FILE%
)

REM Service startup selection menu
echo.
echo ========================================================================
echo                        🚀 LAUNCH OPTIONS MENU
echo ========================================================================
echo.
echo    1) 🛡️  Ultimate Hub (Recommended)   - Full GUI control center
echo    2) 🖥️  Enhanced Dashboard           - Web-based monitoring UI
echo    3) 🤖  Core AI Engine               - Main AI logic handler
echo    4) 👁️  Guardian System              - Background service monitor
echo    5) 🌐  Web Learning System          - AI knowledge acquisition
echo    6) 🧪  System Diagnostics           - Run the ultimate test suite
echo    7) 🚀  Full Ecosystem Startup       - Launch all components
echo    8) Custom Selection
echo.
echo ========================================================================
echo.

set /p choice="Enter your choice (1-8): "
echo [%time%] User input: %choice% >> %LOG_FILE%

if "%choice%"=="1" (
    echo 🚀 Launching Ultimate Hub...
    echo [%time%] User selected: Launch Ultimate Hub >> %LOG_FILE%
    start "Celsius Ultimate Hub" python src/hub/celsius_ultimate_hub.py
) else if "%choice%"=="2" (
    echo 🚀 Launching Enhanced Dashboard...
    echo [%time%] User selected: Launch Enhanced Dashboard >> %LOG_FILE%
    start "Celsius Web Dashboard" python src/dashboard/enhanced_mobile_dashboard.py
) else if "%choice%"=="3" (
    echo 🚀 Launching Core AI Engine...
    echo [%time%] User selected: Launch Core AI Engine >> %LOG_FILE%
    start "Celsius Core AI" python src/core/main.py
) else if "%choice%"=="4" (
    echo 🚀 Launching Guardian System...
    echo [%time%] User selected: Launch Guardian System >> %LOG_FILE%
    start "Celsius Guardian" python src/guardian/celsius_ultimate_guardian.py
) else if "%choice%"=="5" (
    echo 🚀 Launching Web Learning System...
    echo [%time%] User selected: Launch Web Learning System >> %LOG_FILE%
    start "Celsius Web Learning" python src/learning/web_learning_system.py
) else if "%choice%"=="6" (
    echo 🚀 Launching System Diagnostics...
    echo [%time%] User selected: Launch System Diagnostics >> %LOG_FILE%
    start "Celsius Diagnostics" python tests/ultimate_test_suite.py --gui
) else if "%choice%"=="7" (
    echo 🚀 Launching Full Ecosystem...
    echo [%time%] User selected: Launch Full Ecosystem >> %LOG_FILE%
    start "Celsius Full System" cmd /c "scripts/Start_Complete_System.bat"
) else if "%choice%"=="8" (
    echo 🚀 Launching Custom Selection...
    echo [%time%] User selected: Custom Selection >> %LOG_FILE%
    echo 🚧 Custom selection script not yet implemented.
    pause
) else (
    echo ❌ Invalid option. Exiting.
    echo [%time%] Invalid option selected: %choice% >> %LOG_FILE%
)

echo.
echo [%time%] Launch command issued.
echo.
pause
exit /b 0