$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = Join-Path $desktop 'Ziad Invoices Professional.lnk'
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($shortcut)
$s.TargetPath = Join-Path $root 'start-desktop.bat'
$s.WorkingDirectory = $root
$s.Description = 'Ziad Invoices Professional v2.0.0'
$s.Save()
Write-Host "Desktop shortcut created: $shortcut"
