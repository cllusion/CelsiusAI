@echo off
:: ============================================================================
:: Celsius AI - Defender Service Installer
:: ============================================================================
:: Installs Celsius Defender as a Windows startup service
:: Requires: Administrator privileges
:: ============================================================================

echo.
echo ===============================================================================
echo               CELSIUS AI - DEFENDER SERVICE INSTALLER
echo ===============================================================================
echo.

:: Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges.
    echo Please right-click and select "Run as Administrator"
    pause
    exit /b 1
)

echo [INFO] Installing Celsius AI Defender as Windows startup service...
echo.

:: Get the current directory
set "CELSIUS_DIR=%~dp0.."
cd /d "%CELSIUS_DIR%"

:: Install required Python packages
echo [1/5] Installing required Python packages...
python -m pip install --upgrade pip
python -m pip install psutil watchdog pystray Pillow pywin32 aiosqlite
echo.

:: Create startup registry entry
echo [2/5] Creating Windows startup registry entry...
set "DEFENDER_PATH=%CELSIUS_DIR%\src\protection\celsius_realtime_defender.py"
set "PYTHON_PATH=%SYSTEMROOT%\py.exe"

reg add "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run" /v "CelsiusDefender" /t REG_SZ /d "\"%PYTHON_PATH%\" \"%DEFENDER_PATH%\"" /f >nul 2>&1

if %errorLevel% equ 0 (
    echo [SUCCESS] Startup entry created successfully
) else (
    echo [WARNING] Could not create startup entry automatically
    echo You can manually add it through Task Scheduler
)
echo.

:: Create Windows Firewall rules
echo [3/5] Configuring Windows Firewall rules...
netsh advfirewall firewall add rule name="Celsius AI Defender" dir=in action=allow program="%PYTHON_PATH%" enable=yes >nul 2>&1
netsh advfirewall firewall add rule name="Celsius AI Defender Out" dir=out action=allow program="%PYTHON_PATH%" enable=yes >nul 2>&1
echo [SUCCESS] Firewall rules configured
echo.

:: Create scheduled task for persistence
echo [4/5] Creating scheduled task...
schtasks /create /tn "CelsiusDefender" /tr "\"%PYTHON_PATH%\" \"%DEFENDER_PATH%\"" /sc onlogon /rl highest /f >nul 2>&1
if %errorLevel% equ 0 (
    echo [SUCCESS] Scheduled task created
) else (
    echo [WARNING] Could not create scheduled task
)
echo.

:: Start the defender now
echo [5/5] Starting Celsius Defender...
start "Celsius AI Defender" "%PYTHON_PATH%" "%DEFENDER_PATH%"
timeout /t 2 >nul
echo [SUCCESS] Defender started
echo.

echo ===============================================================================
echo                    INSTALLATION COMPLETE!
echo ===============================================================================
echo.
echo Celsius AI Defender is now:
echo   - Running in the background
echo   - Will start automatically on system boot
echo   - Monitoring your system for threats
echo   - Accessible via system tray icon
echo.
echo Features enabled:
echo   [X] Real-time file monitoring (Downloads, Desktop, Documents)
echo   [X] Process behavior analysis
echo   [X] Network traffic monitoring
echo   [X] Machine learning threat detection
echo   [X] Automatic quarantine
echo   [X] Windows notifications
echo.
echo Check the system tray for the Celsius shield icon.
echo Logs: %CELSIUS_DIR%\logs\defender.log
echo.
pause
