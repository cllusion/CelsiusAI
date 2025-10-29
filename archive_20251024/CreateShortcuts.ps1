# Simple PowerShell script to create Celsius AI shortcuts
Write-Host "Creating Celsius AI shortcuts..."

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$WshShell = New-Object -comObject WScript.Shell

# Get desktop path
$Desktop = [System.Environment]::GetFolderPath('Desktop')

# Create Server Hub shortcut
$Shortcut1 = $WshShell.CreateShortcut("$Desktop\Celsius AI Server Hub.lnk")
$Shortcut1.TargetPath = "python"
$Shortcut1.Arguments = """$ScriptPath\celsius_server_hub.py"""
$Shortcut1.WorkingDirectory = $ScriptPath
$Shortcut1.Save()

# Create Launcher shortcut  
$Shortcut2 = $WshShell.CreateShortcut("$Desktop\Celsius AI Launcher.lnk")
$Shortcut2.TargetPath = "python"
$Shortcut2.Arguments = """$ScriptPath\celsius_taskbar_launcher.py"""
$Shortcut2.WorkingDirectory = $ScriptPath
$Shortcut2.Save()

Write-Host "Shortcuts created on desktop!"
Write-Host "Right-click them and select 'Pin to taskbar'"
pause