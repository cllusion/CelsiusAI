@echo off
REM ============================================================================
REM Celsius AI - Persistent Guardian Launcher
REM ============================================================================
REM This script ensures the Guardian stays running and restarts it if it crashes
REM ============================================================================

echo.
echo ========================================================================
echo    CELSIUS AI - PERSISTENT GUARDIAN LAUNCHER
echo ========================================================================
echo.

cd /d "%~dp0"

REM Check if Guardian is already running
echo Checking for existing Guardian processes...
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq celsius_ultimate_guardian*" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ⚠️  WARNING: Guardian appears to already be running!
    echo.
    choice /C YN /M "Do you want to stop the existing Guardian and start a new one"
    if errorlevel 2 goto :end
    if errorlevel 1 (
        echo Stopping existing Guardian processes...
        taskkill /F /FI "WINDOWTITLE eq *celsius_ultimate_guardian*" /T 2>NUL
        timeout /t 3 /nobreak >NUL
    )
)

echo This script will keep the Guardian running continuously.
echo The Guardian monitors and automatically restarts all Celsius services.
echo.
echo Press Ctrl+C to stop the Guardian (it will clean up gracefully)
echo.
echo ========================================================================
echo.

REM Find Python executable
set PYTHON_EXE=
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
) else if exist "C:\Users\micro\AppData\Local\Microsoft\WindowsApps\python.exe" (
    set PYTHON_EXE=C:\Users\micro\AppData\Local\Microsoft\WindowsApps\python.exe
) else (
    set PYTHON_EXE=python
)

echo Using Python: %PYTHON_EXE%
echo.

REM Keep Guardian running in a loop
:guardian_loop

echo [%date% %time%] Starting Guardian...
"%PYTHON_EXE%" "src\guardian\celsius_ultimate_guardian.py"

REM Check exit code
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [%date% %time%] Guardian exited normally.
    echo.
    goto :end
) else (
    echo.
    echo [%date% %time%] WARNING: Guardian crashed with error code %ERRORLEVEL%
    echo [%date% %time%] Restarting in 5 seconds...
    echo.
    timeout /t 5 /nobreak
    goto guardian_loop
)

:end
echo.
echo Guardian shutdown complete.
pause
