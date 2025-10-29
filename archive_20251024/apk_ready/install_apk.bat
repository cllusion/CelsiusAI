@echo off
echo Installing Celsius AI Universal APK
echo ===================================

echo Connecting to Samsung Galaxy S25 Ultra...
adb devices

echo Installing APK...
adb install -r "CelsiusAI-S25Ultra.apk"

echo ✅ Installation complete!
echo 📱 Look for "Celsius AI Universal" in your app drawer
pause
