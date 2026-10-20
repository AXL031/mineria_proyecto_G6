$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $PSScriptRoot 'control_demo.ps1'
$powershellPath = (Get-Command powershell.exe).Source
$iconPath = Join-Path $projectRoot 'dashboard/assets/noto-emoji/bankshield.ico'
$shortcutShell = New-Object -ComObject WScript.Shell
foreach ($entry in @(
    @{ name='Abrir BankShield'; action='Open'; description='Inicia BankShield y abre la demo en el navegador.' },
    @{ name='Cerrar BankShield'; action='Close'; description='Detiene la API, el panel y sus procesos hijos para liberar recursos.' }
)) {
    $shortcutPath = Join-Path $projectRoot "$($entry.name).lnk"
    $shortcut = $shortcutShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $powershellPath
    $shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`" -Action $($entry.action)"
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.WindowStyle = 7
    $shortcut.Description = $entry.description
    $shortcut.IconLocation = "$iconPath,0"
    $shortcut.Save()
    Write-Host "Creado: $shortcutPath"
}
