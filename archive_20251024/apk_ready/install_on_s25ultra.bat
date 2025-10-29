@echo off
echo Installing Celsius AI on Samsung Galaxy S25 Ultra...
echo ====================================================

REM Check if ADB is available
where adb >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing via file transfer method...
    goto MANUAL_INSTALL
)

REM Try ADB install
echo Attempting ADB installation...
adb install CelsiusAI-S25Ultra.apk
if %ERRORLEVEL% EQU 0 (
    echo Installation successful via ADB!
    goto SUCCESS
)

:MANUAL_INSTALL
echo Manual Installation Instructions:
echo ====================================
echo 1. Copy CelsiusAI-S25Ultra.apk to your Samsung S25 Ultra
echo 2. Enable "Unknown Sources" in Settings
echo 3. Tap the APK file to install
echo 4. Grant all permissions when prompted
echo 5. Launch Celsius AI from app drawer
echo.
echo Server Connection: http://192.168.1.100:5000
echo.
goto END

:SUCCESS
echo Celsius AI installed successfully!
echo Launch the app and it will connect to your PC server.

:END
pause
