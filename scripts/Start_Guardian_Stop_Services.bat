@echo off
:: ============================================================================
:: Celsius AI - Start Guardian (Stop Services on Exit Mode)
:: ============================================================================
:: Starts Guardian with --shutdown-services flag
:: When Guardian is closed, all services will also stop
:: ============================================================================

title Celsius AI - Guardian (Stop Services Mode)
color 0E
cls

echo.
echo ========================================================================
echo         CELSIUS AI - GUARDIAN (STOP SERVICES ON EXIT MODE)
echo ========================================================================
echo.
echo Starting Guardian with --shutdown-services flag...
echo.
echo In this mode, when Guardian is closed, ALL services will also stop.
echo This is the OLD behavior for those who prefer it.
echo.
echo For the NEW default behavior (services continue running), use:
echo   Start_Master_System.bat
echo.
echo ========================================================================
echo.

cd /d "%~dp0..\"

echo Starting Guardian...
echo.

python src/guardian/celsius_ultimate_guardian.py --shutdown-services

echo.
echo Guardian has stopped.
echo All services have also been stopped.
echo.
pause
