# Celsius AI Persistent Service Installer
# This script sets up Celsius AI to run automatically on Windows startup

Write-Host "🌡️ Celsius AI Persistent Service Installer" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "❌ This script requires Administrator privileges" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

$celsiusPath = "C:\Users\micro\Celsius AI"
$taskName = "CelsiusAI-PersistentService"

Write-Host "📋 Installation Options:" -ForegroundColor Green
Write-Host "1. Install Task Scheduler (Recommended)"
Write-Host "2. Install as Windows Service"  
Write-Host "3. Create Startup Shortcut"
Write-Host "4. Remove All Installations"
Write-Host "0. Exit"
Write-Host ""

$choice = Read-Host "Choose installation method (0-4)"

switch ($choice) {
    "1" {
        Write-Host "🔧 Installing Task Scheduler..." -ForegroundColor Yellow
        
        try {
            # Import the task
            Register-ScheduledTask -Xml (Get-Content "$celsiusPath\celsius_ai_task.xml" | Out-String) -TaskName $taskName -Force
            
            Write-Host "✅ Task Scheduler installed successfully" -ForegroundColor Green
            Write-Host "🚀 Celsius AI will now start automatically on boot" -ForegroundColor Green
            
            # Ask to start now
            $startNow = Read-Host "Start Celsius AI now? (y/n)"
            if ($startNow -eq "y" -or $startNow -eq "Y") {
                Start-ScheduledTask -TaskName $taskName
                Write-Host "✅ Celsius AI started" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "❌ Failed to install task: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    "2" {
        Write-Host "🔧 Installing as Windows Service..." -ForegroundColor Yellow
        
        try {
            $serviceName = "CelsiusAI"
            $serviceDisplay = "Celsius AI Persistent Service"
            $serviceDesc = "Celsius AI with automatic ngrok tunnel"
            $servicePath = "`"$celsiusPath\.venv\Scripts\python.exe`" `"$celsiusPath\persistent_celsius_service.py`""
            
            # Remove existing service if it exists
            if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
                Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
                sc.exe delete $serviceName
                Start-Sleep 2
            }
            
            # Create new service
            New-Service -Name $serviceName -BinaryPathName $servicePath -DisplayName $serviceDisplay -Description $serviceDesc -StartupType Automatic
            
            Write-Host "✅ Windows Service installed successfully" -ForegroundColor Green
            
            # Ask to start now
            $startNow = Read-Host "Start service now? (y/n)"
            if ($startNow -eq "y" -or $startNow -eq "Y") {
                Start-Service -Name $serviceName
                Write-Host "✅ Service started" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "❌ Failed to install service: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    "3" {
        Write-Host "🔧 Creating Startup Shortcut..." -ForegroundColor Yellow
        
        try {
            $startupFolder = [Environment]::GetFolderPath("Startup")
            $shortcutPath = "$startupFolder\Celsius AI.lnk"
            
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut($shortcutPath)
            $Shortcut.TargetPath = "$celsiusPath\service_manager.bat"
            $Shortcut.WorkingDirectory = $celsiusPath
            $Shortcut.Description = "Celsius AI Persistent Service"
            $Shortcut.Save()
            
            Write-Host "✅ Startup shortcut created" -ForegroundColor Green
            Write-Host "📁 Location: $shortcutPath" -ForegroundColor Gray
        }
        catch {
            Write-Host "❌ Failed to create shortcut: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    "4" {
        Write-Host "🗑️ Removing all installations..." -ForegroundColor Yellow
        
        # Remove Task Scheduler
        try {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
            Write-Host "✅ Task Scheduler removed" -ForegroundColor Green
        }
        catch {}
        
        # Remove Windows Service
        try {
            Stop-Service -Name "CelsiusAI" -Force -ErrorAction SilentlyContinue
            sc.exe delete "CelsiusAI" 2>$null
            Write-Host "✅ Windows Service removed" -ForegroundColor Green
        }
        catch {}
        
        # Remove startup shortcut
        try {
            $startupFolder = [Environment]::GetFolderPath("Startup")
            $shortcutPath = "$startupFolder\Celsius AI.lnk"
            if (Test-Path $shortcutPath) {
                Remove-Item $shortcutPath -Force
                Write-Host "✅ Startup shortcut removed" -ForegroundColor Green
            }
        }
        catch {}
        
        Write-Host "🧹 All installations removed" -ForegroundColor Green
    }
    
    "0" {
        Write-Host "👋 Goodbye!" -ForegroundColor Cyan
        exit 0
    }
    
    default {
        Write-Host "❌ Invalid choice" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "• Check logs in: $celsiusPath\logs\celsius_service.log"
Write-Host "• View current URL: $celsiusPath\current_url.json" 
Write-Host "• Manage services with: $celsiusPath\service_manager.bat"
Write-Host ""

Read-Host "Press Enter to exit"