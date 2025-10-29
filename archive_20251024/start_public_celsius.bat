@echo off
title Celsius AI + ngrok Public Access
echo.
echo 🌡️ Celsius AI + ngrok Public Access
echo ===================================
echo.
echo This will start Celsius AI and create a public URL
echo that works from anywhere in the world!
echo.

cd "C:\Users\micro\Celsius AI"

echo Starting Celsius AI on port 5000...
echo.

REM Start Celsius AI in the background
start "Celsius AI Server" /min "C:\Users\micro\Celsius AI\.venv\Scripts\python.exe" -c "from enhanced_mobile_dashboard import app; app.run(host='0.0.0.0', port=5000, debug=False)"

REM Wait a moment for the server to start
timeout /t 3 /nobreak > nul

echo Starting ngrok tunnel...
echo.
echo 🚀 Creating public URL for Celsius AI...
echo.

REM Start ngrok to expose port 5000
ngrok.exe http 5000

echo.
echo Tunnel closed. Celsius AI is still running locally.
pause