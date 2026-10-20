param(
    [Parameter(Mandatory=$true)][ValidateSet('Open','Close')][string]$Action,
    [switch]$NoBrowser,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$reportRoot = Join-Path $projectRoot 'artifacts/reports/demo'
$statePath = Join-Path $reportRoot 'processes.json'
New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null
$lockHash = [System.Security.Cryptography.SHA256]::Create()
$lockBytes = $lockHash.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($projectRoot.ToLowerInvariant()))
$lockName = 'Local\BankShieldDemo-' + ([BitConverter]::ToString($lockBytes)).Replace('-','').Substring(0,24)
$lockHash.Dispose()
$mutex = New-Object System.Threading.Mutex($false, $lockName)
$acquired = $false

function Test-DemoState {
    param($State)
    if (-not $State -or [System.IO.Path]::GetFullPath($State.root) -ne $projectRoot) { return $false }
    if (@($State.processes).Count -ne 2) { return $false }
    foreach ($record in $State.processes) {
        $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
        if (-not $process -or $process.StartTime.ToUniversalTime().Ticks -ne $record.startTicks) { return $false }
    }
    try {
        $api = Invoke-RestMethod "$($State.apiUrl)/" -TimeoutSec 3
        $panel = Invoke-RestMethod "$($State.dashboardUrl)/_stcore/health" -TimeoutSec 3
        return $api.status -eq 'online' -and $api.modules.Count -eq 6 -and $panel -eq 'ok'
    } catch { return $false }
}

try {
    # Impide que pulsaciones simultaneas creen dos instancias.
    try { $acquired = $mutex.WaitOne(5000) } catch [System.Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) { throw 'Ya hay un inicio o cierre en curso. Espera unos segundos.' }
    if ($Action -eq 'Close') {
        & "$PSScriptRoot/stop_demo.ps1"
        if (-not $Quiet) {
            $notification = New-Object -ComObject WScript.Shell
            $null = $notification.Popup('BankShield está cerrado. La API y el panel ya no consumen recursos.', 3, 'BankShield', 64)
        }
    } else {
        $state = $null
        if (Test-Path -LiteralPath $statePath) {
            $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        }
        if (Test-DemoState $state) {
            Write-Host 'BankShield ya estaba iniciado; se reutiliza la instancia.'
        } else {
            if ($state) { & "$PSScriptRoot/stop_demo.ps1" }
            & "$PSScriptRoot/start_demo.ps1"
            $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
            if (-not (Test-DemoState $state)) { throw 'El sistema no quedó disponible. Revisa los logs de la demo.' }
        }
        if (-not $NoBrowser) {
            # Ventana interactiva solicitada por el usuario: abre su navegador habitual.
            Start-Process -FilePath $state.dashboardUrl
        }
    }
} catch {
    $message = $_.Exception.Message
    Add-Content -LiteralPath (Join-Path $reportRoot 'launcher-errors.log') -Value "$(Get-Date -Format o) $Action : $message" -Encoding utf8
    if (-not $Quiet) {
        $notification = New-Object -ComObject WScript.Shell
        $null = $notification.Popup($message, 0, 'BankShield: no se pudo completar la acción', 16)
    }
    Write-Error $message
    exit 1
} finally {
    if ($acquired) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
