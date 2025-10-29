# Celsius AI Persistent Guardian Installation Script
# This script sets up hardcore persistence for Celsius AI

Write-Host "[INSTALL] Celsius AI Persistent Guardian Installation" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green

$CelsiusPath = "C:\Users\micro\Celsius AI"
$GuardianScript = "$CelsiusPath\start_guardian.bat"
$RegistryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RegistryName = "CelsiusGuardian"

try {
    # Check if Celsius AI directory exists
    if (!(Test-Path $CelsiusPath)) {
        Write-Host "[ERROR] Celsius AI directory not found: $CelsiusPath" -ForegroundColor Red
        exit 1
    }

    # Check if guardian script exists
    if (!(Test-Path $GuardianScript)) {
        Write-Host "[ERROR] Guardian script not found: $GuardianScript" -ForegroundColor Red
        exit 1
    }

    Write-Host "[INFO] Installing persistent guardian to Windows startup..." -ForegroundColor Yellow

    # Add to Windows startup registry
    Set-ItemProperty -Path $RegistryPath -Name $RegistryName -Value $GuardianScript -Force
    
    Write-Host "[SUCCESS] Guardian installed to Windows startup registry" -ForegroundColor Green

    # Verify installation
    $RegistryValue = Get-ItemProperty -Path $RegistryPath -Name $RegistryName -ErrorAction SilentlyContinue
    if ($RegistryValue) {
        Write-Host "[VERIFY] Registry entry confirmed: $($RegistryValue.CelsiusGuardian)" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Could not verify registry installation" -ForegroundColor Yellow
    }

    # Create desktop shortcut for manual guardian control
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = "$DesktopPath\Celsius Guardian.lnk"
    
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $GuardianScript
    $Shortcut.WorkingDirectory = $CelsiusPath
    $Shortcut.Description = "Celsius AI Persistent Guardian"
    $Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,17"
    $Shortcut.Save()
    
    Write-Host "[SUCCESS] Desktop shortcut created: $ShortcutPath" -ForegroundColor Green

    # Offer to start guardian immediately
    Write-Host "`n[OPTION] Start guardian now? (Y/N)" -ForegroundColor Cyan -NoNewline
    $Response = Read-Host " "
    
    if ($Response -eq "Y" -or $Response -eq "y" -or $Response -eq "") {
        Write-Host "[STARTING] Launching Celsius Persistent Guardian..." -ForegroundColor Yellow
        
        # Start guardian
        Start-Process -FilePath $GuardianScript -WorkingDirectory $CelsiusPath
        
        Write-Host "[SUCCESS] Guardian started!" -ForegroundColor Green
        Start-Sleep -Seconds 2
        
        # Show status
        Write-Host "`n[STATUS] Guardian processes:" -ForegroundColor Cyan
        Get-Process | Where-Object { $_.ProcessName -like "*python*" -and $_.CommandLine -like "*celsius*" } | 
            Select-Object Id, ProcessName, @{Name="CommandLine";Expression={$_.CommandLine}} | 
            Format-Table -AutoSize
    }

    Write-Host "`n[COMPLETE] Persistent Guardian Installation Complete!" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "[INFO] Guardian will start automatically with Windows" -ForegroundColor Cyan
    Write-Host "[INFO] Use desktop shortcut to manually start guardian" -ForegroundColor Cyan
    Write-Host "[INFO] Guardian monitors: Server Hub, Mobile Server, Core AI" -ForegroundColor Cyan
    Write-Host "`n[HARDCORE] True persistence enabled - services will restart automatically!" -ForegroundColor Magenta

} catch {
    Write-Host "[ERROR] Installation failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}