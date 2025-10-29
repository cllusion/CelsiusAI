@echo off
title Celsius AI - Server Hub (Fast Mode)
echo.
echo ====================================
echo   Celsius AI Server Hub - Fast Mode  
echo ====================================
echo.
echo Starting with optimizations:
echo - Reduced status checking frequency
echo - Automatic server startup enabled
echo - UI responsiveness improvements  
echo.
echo Please wait while the hub loads...
echo.

cd /d "C:\Users\micro\Celsius AI"

REM Set environment variable for fast mode
set CELSIUS_FAST_MODE=1

REM Start the server hub
python celsius_server_hub.py

echo.
echo Server Hub has closed.
pause