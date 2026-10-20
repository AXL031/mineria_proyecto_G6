param([int]$ApiPort = 8000, [int]$DashboardPort = 8501)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$demoPython = Join-Path $projectRoot '.venv-pruebas/Scripts/python.exe'
$reportRoot = Join-Path $projectRoot 'artifacts/reports/demo'
$statePath = Join-Path $reportRoot 'processes.json'
$required = @(
    'artifacts/models/fraud-silver/model.joblib', 'artifacts/models/fraud-silver/patterns.json',
    'artifacts/models/credit/model.joblib', 'data/gold/forecast/transactions_hourly.parquet',
    'artifacts/reports/forecast_monitoring.json', 'data/gold/segments/account_segments.parquet',
    'artifacts/reports/segments.json', 'artifacts/models/complaints/model.joblib',
    'data/silver/complaints/complaints.parquet', 'artifacts/reports/complaints/error_examples.json'
)
if (-not (Test-Path -LiteralPath $demoPython)) { throw 'Ejecuta scripts/setup_env.ps1 para preparar Python.' }
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $relative))) {
        throw "Falta $relative. Ejecuta .venv-pruebas/Scripts/python.exe scripts/prepare_demo.py"
    }
}
foreach ($port in @($ApiPort, $DashboardPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "El puerto $port está ocupado. Si es esta demo, detenla con scripts/stop_demo.ps1."
    }
}
New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null
$env:OMP_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
$env:MKL_NUM_THREADS = '2'
$env:BANKSHIELD_FRAUD_MODEL = Join-Path $projectRoot 'artifacts/models/fraud-silver/model.joblib'
$env:BANKSHIELD_API_URL = "http://127.0.0.1:$ApiPort"
$env:BANKSHIELD_GRAPH_SAMPLE = '10000'
foreach ($name in @('BANKSHIELD_CREDIT_MODEL', 'BANKSHIELD_FORECAST_GOLD', 'BANKSHIELD_FORECAST_MONITORING', 'BANKSHIELD_SEGMENTS_PARQUET', 'BANKSHIELD_SEGMENTS_REPORT', 'BANKSHIELD_COMPLAINTS_MODEL', 'BANKSHIELD_COMPLAINTS_SILVER', 'BANKSHIELD_COMPLAINTS_EXAMPLES')) {
    Remove-Item "Env:$name" -ErrorAction SilentlyContinue
}
$started = @()
try {
    $api = Start-Process -FilePath $demoPython -ArgumentList @('-m','uvicorn','api.main:app','--host','127.0.0.1','--port',"$ApiPort") -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $reportRoot 'api.stdout.log') -RedirectStandardError (Join-Path $reportRoot 'api.stderr.log') -PassThru
    $started += @{ kind='api'; id=$api.Id; startTicks=$api.StartTime.ToUniversalTime().Ticks }
    $deadline = (Get-Date).AddSeconds(45)
    $ready = $false
    do {
        if ($api.HasExited) { throw 'La API terminó; revisar artifacts/reports/demo/api.stderr.log' }
        try { $health = Invoke-RestMethod "$env:BANKSHIELD_API_URL/" -TimeoutSec 2; $ready = $health.modules.Count -eq 6 } catch { }
        if (-not $ready) { Start-Sleep -Milliseconds 300 }
    } while (-not $ready -and (Get-Date) -lt $deadline)
    if (-not $ready) { throw 'La API no quedó disponible.' }
    $dashboard = Start-Process -FilePath $demoPython -ArgumentList @('-m','streamlit','run','dashboard/app.py','--server.address','127.0.0.1','--server.port',"$DashboardPort",'--server.headless','true','--browser.gatherUsageStats','false') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $reportRoot 'dashboard.stdout.log') -RedirectStandardError (Join-Path $reportRoot 'dashboard.stderr.log') -PassThru
    $started += @{ kind='dashboard'; id=$dashboard.Id; startTicks=$dashboard.StartTime.ToUniversalTime().Ticks }
    @{ root=$projectRoot; apiUrl=$env:BANKSHIELD_API_URL; dashboardUrl="http://127.0.0.1:$DashboardPort"; processes=$started } | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 -LiteralPath $statePath
    $deadline = (Get-Date).AddSeconds(30)
    $ready = $false
    do {
        if ($dashboard.HasExited) { throw 'El panel terminó; revisar artifacts/reports/demo/dashboard.stderr.log' }
        try { $health = Invoke-RestMethod "http://127.0.0.1:$DashboardPort/_stcore/health" -TimeoutSec 2; $ready = $health -eq 'ok' } catch { }
        if (-not $ready) { Start-Sleep -Milliseconds 300 }
    } while (-not $ready -and (Get-Date) -lt $deadline)
    if (-not $ready) { throw 'El panel no quedó disponible.' }
    Write-Host "Demo iniciada: http://127.0.0.1:$DashboardPort"
    Write-Host "API: $env:BANKSHIELD_API_URL/docs"
    Write-Host 'Para detener: powershell -ExecutionPolicy Bypass -File scripts/stop_demo.ps1'
} catch {
    foreach ($record in $started) {
        $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $record.startTicks) {
            & taskkill.exe /PID $record.id /T /F | Out-Null
        }
    }
    throw
}
