@echo off
echo Building Celsius AI APK for Samsung Galaxy S25 Ultra...
echo ========================================================

REM Check if Android SDK is available
if "%ANDROID_HOME%"=="" (
    echo Error: ANDROID_HOME not set. Please install Android SDK.
    echo Download from: https://developer.android.com/studio
    pause
    exit /b 1
)

REM Build the APK
echo Compiling Android project...
call gradlew.bat assembleDebug

if %ERRORLEVEL% == 0 (
    echo ✅ APK built successfully!
    echo 📱 Location: app\build\outputs\apk\debug\app-debug.apk
    echo 📋 Install on Samsung S25 Ultra:
    echo    1. Enable Unknown Sources in Settings
    echo    2. Transfer APK to phone
    echo    3. Tap to install
    echo    4. Grant permissions
    echo 🔗 Server: Make sure PC is running Celsius AI on 192.168.1.100:5000
) else (
    echo ❌ Build failed. Check Android Studio setup.
)
pause