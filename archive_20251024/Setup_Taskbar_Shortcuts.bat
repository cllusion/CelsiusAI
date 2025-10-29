@echo off
title Create Celsius AI Taskbar Shortcuts

echo ================================================
echo   CREATE CELSIUS AI TASKBAR SHORTCUTS
echo ================================================
echo.
echo This will create desktop and Start Menu shortcuts
echo for Celsius AI Server Hub and Taskbar Launcher.
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

echo.
echo Creating shortcuts...

powershell -ExecutionPolicy Bypass -File "%~dp0CreateShortcuts.ps1"

echo.
echo Done! Check your desktop for the new shortcuts.
echo You can now pin them to your taskbar.
echo.
pause