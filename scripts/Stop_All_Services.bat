@echo off
:: ============================================================================
:: Celsius AI - Stop All Services
:: ============================================================================
:: Safely stops all running Celsius AI services
:: ============================================================================

title Celsius AI - Stop All Services
color 0C
cls

echo.
echo ========================================================================
echo              CELSIUS AI - STOP ALL SERVICES
echo ========================================================================
echo.
echo This will stop all running Celsius AI services:
echo   - Real-Time Defender
echo   - Ultimate Hub
echo   - Enhanced Dashboard
echo   - Core AI Engine
echo   - Web Learning System
echo   - Hourly Reporter
echo   - Guardian (if running)
echo.
echo ========================================================================
echo.

set /p confirm="Are you sure you want to stop all services? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo.
    echo Operation cancelled.
    pause
    exit /b 0
)

echo.
echo Stopping all Celsius AI services...
echo.

:: Stop all Python processes that match Celsius patterns
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /NH 2^>nul') do (
    echo Checking PID %%a...
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /i "celsius" >nul
    if not errorlevel 1 (
        echo   Stopping Celsius service (PID: %%a)
        taskkill /PID %%a /F >nul 2>&1
    )
)

echo.
echo Checking for pythonw.exe processes...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq pythonw.exe" /NH 2^>nul') do (
    echo Checking PID %%a...
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /i "celsius" >nul
    if not errorlevel 1 (
        echo   Stopping Celsius service (PID: %%a)
        taskkill /PID %%a /F >nul 2>&1
    )
)

echo.
echo ========================================================================
echo                    ALL SERVICES STOPPED
echo ========================================================================
echo.
echo All Celsius AI services have been stopped.
echo You can restart them using Start_Master_System.bat
echo.
pause
