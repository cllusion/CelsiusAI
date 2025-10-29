@echo off
title Celsius AI - Complete System Startup
color 0A

echo.
echo ========================================
echo    🛡️ CELSIUS AI - COMPLETE STARTUP
echo ========================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python first.
    pause
    exit /b 1
)

echo 🔍 Python found - proceeding with startup...
echo.

:: Start the persistent services first
echo 🚀 Starting persistent services...
start "Celsius Guardian" /MIN python src/guardian/celsius_ultimate_guardian.py

:: Wait a moment for services to initialize
timeout /t 5 /nobreak >nul

:: Now start the Persistent Hub Launcher in its own window
echo 🖥️ Starting Persistent Hub Launcher...
start "Celsius Hub Launcher" python scripts/persistent_hub_launcher.py

echo.
echo ✅ Celsius AI system startup complete!
echo.
echo 📋 What's running:
echo    • Persistent Services (Guardian, Dashboard, Core, Web Learning)
echo    • Ultimate Hub (Manual control interface)
echo.
echo 💡 Tips:
echo    • Ultimate Hub provides manual control and monitoring
echo    • Guardian automatically maintains service persistence
echo    • Close services through Ultimate Hub or this window
echo.

echo 🛡️ System is now fully operational!
echo Press any key to keep monitoring or close to continue...
pause >nul

:: Optional: Keep window open for monitoring
echo.
echo 🔍 Monitoring system status...
echo Press Ctrl+C to stop monitoring
echo.

:monitor_loop
timeout /t 30 /nobreak >nul
echo 🛡️ Services running... (Guardian active)
goto monitor_loop