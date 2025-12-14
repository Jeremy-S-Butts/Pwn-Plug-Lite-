<#
.SYNOPSIS
    Detects use of HKCU:\Environment\UserInitMprLogonScript for persistence.

.DESCRIPTION
    Reads the UserInitMprLogonScript registry value and reports:
    - Whether it is configured
    - The file path it points to
    - Whether the file exists
    - Basic file metadata
    Optionally offers to clear the value if suspicious.
#>

$regPath  = 'HKCU:\Environment'
$valueName = 'UserInitMprLogonScript'

Write-Host "=== Logon Script Persistence Check ===`n"

try {
    $props = Get-ItemProperty -Path $regPath -Name $valueName -ErrorAction Stop
    $scriptPath = $props.$valueName

    if ([string]::IsNullOrWhiteSpace($scriptPath)) {
        Write-Host "[+] UserInitMprLogonScript value exists but is empty."
        exit 0
    }

    Write-Host "[!] Logon script value is configured:"
    Write-Host "    Registry path : $regPath"
    Write-Host "    Value name    : $valueName"
    Write-Host "    Script path   : $scriptPath`n"

    if (Test-Path -LiteralPath $scriptPath) {
        $file = Get-Item -LiteralPath $scriptPath
        Write-Host "    File exists: YES"
        Write-Host "    Size       : $($file.Length) bytes"
        Write-Host "    Created    : $($file.CreationTime)"
        Write-Host "    Modified   : $($file.LastWriteTime)"
    }
    else {
        Write-Host "    File exists: NO (path is dead / orphaned)"
    }

    Write-Host "`n[!] This key is commonly abused for persistence."
    $answer = Read-Host "Do you want to clear UserInitMprLogonScript now? (y/N)"

    if ($answer -match '^[Yy]') {
        Remove-ItemProperty -Path $regPath -Name $valueName -ErrorAction Stop
        Write-Host "[+] Registry value removed."
    }
    else {
        Write-Host "[*] No changes were made."
    }
}
catch [System.Management.Automation.ItemNotFoundException] {
    Write-Host "[+] UserInitMprLogonScript is NOT configured for the current user."
}
catch {
    Write-Host "[!] Error accessing registry: $($_.Exception.Message)"
}
