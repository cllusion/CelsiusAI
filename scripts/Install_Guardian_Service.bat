@echo off
REM ============================================================================
REM Celsius AI - Install Guardian as Windows Startup Service
REM ============================================================================
REM This creates a startup shortcut so Guardian runs automatically at login
REM ============================================================================

echo.
echo ========================================================================
echo    CELSIUS AI - INSTALL GUARDIAN STARTUP SERVICE
echo ========================================================================
echo.

cd /d "%~dp0"

REM Create shortcut in Startup folder
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT=%STARTUP_FOLDER%\Celsius Guardian.lnk
set TARGET=%cd%\Start_Guardian_Persistent.bat

echo Creating startup shortcut...
echo Target: %TARGET%
echo Location: %SHORTCUT%
echo.

REM Use PowerShell to create shortcut
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUT%'); $SC.TargetPath = '%TARGET%'; $SC.WorkingDirectory = '%cd%'; $SC.WindowStyle = 7; $SC.Description = 'Celsius AI Guardian - Service Monitor'; $SC.Save()"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================================
    echo    SUCCESS! Guardian installed to startup.
    echo ========================================================================
    echo.
    echo The Guardian will now start automatically when you log in.
    echo It will monitor and restart all Celsius services.
    echo.
    echo To remove: Delete the shortcut from:
    echo %STARTUP_FOLDER%
    echo.
) else (
    echo.
    echo ERROR: Failed to create startup shortcut.
    echo.
)

pause
