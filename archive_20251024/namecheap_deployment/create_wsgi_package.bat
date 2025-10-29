@echo off
echo Creating Celsius AI Namecheap Deployment Package (WSGI Version)...
echo.

cd "C:\Users\micro\Celsius AI\namecheap_deployment"

REM Create deployment folder
if not exist "celsius-ai-wsgi" mkdir "celsius-ai-wsgi"

REM Copy essential files
copy wsgi_app.py "celsius-ai-wsgi\app.py"
copy requirements_wsgi.txt "celsius-ai-wsgi\requirements.txt"

REM Create a simple README for deployment
echo # Celsius AI - Namecheap Deployment (WSGI Version) > "celsius-ai-wsgi\README.txt"
echo. >> "celsius-ai-wsgi\README.txt"
echo 1. Upload all files to your Python app directory >> "celsius-ai-wsgi\README.txt"
echo 2. In cPanel Python App settings: >> "celsius-ai-wsgi\README.txt"
echo    - Startup File: app.py >> "celsius-ai-wsgi\README.txt"
echo    - Application Entry Point: application >> "celsius-ai-wsgi\README.txt"
echo 3. Restart the Python app >> "celsius-ai-wsgi\README.txt"
echo 4. Visit your domain to see Celsius AI >> "celsius-ai-wsgi\README.txt"
echo. >> "celsius-ai-wsgi\README.txt"
echo This version uses pure Python WSGI - no external dependencies required! >> "celsius-ai-wsgi\README.txt"

echo.
echo Package created in: celsius-ai-wsgi folder
echo Files included:
dir "celsius-ai-wsgi"
echo.
echo Ready for Namecheap deployment!
pause