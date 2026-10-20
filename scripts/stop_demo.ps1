$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $projectRoot 'artifacts/reports/demo/processes.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Host 'No hay procesos de demo registrados.'; exit 0 }
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ([System.IO.Path]::GetFullPath($state.root) -ne [System.IO.Path]::GetFullPath($projectRoot)) { throw 'El registro pertenece a otro proyecto.' }
foreach ($record in $state.processes) {
    $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $record.startTicks) {
        # El Python del entorno puede crear otro interprete y un conhost.
        # Se termina solo el arbol del PID registrado, tras comprobar su fecha.
        & taskkill.exe /PID $record.id /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $remaining = Get-Process -Id $record.id -ErrorAction SilentlyContinue
            if ($remaining -and $remaining.StartTime.ToUniversalTime().Ticks -eq $record.startTicks) {
                throw "No se pudo detener $($record.kind)."
            }
        }
        Write-Host "Detenido: $($record.kind)"
    }
}
Remove-Item -LiteralPath $statePath
