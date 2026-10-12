param(
    [string]$PythonExecutable = "",
    [switch]$SkipInstall,
    [string]$OutputRoot = "artifacts/reports/fraud-reproduction"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$environmentPython = Join-Path $projectRoot ".venv-pruebas/Scripts/python.exe"

function Invoke-FraudStep {
    param([string[]]$Arguments)
    & $environmentPython @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Falló el paso: $($Arguments -join ' ')" }
}

Push-Location $projectRoot
try {
    if (-not $SkipInstall) {
        if ($PythonExecutable) {
            & "$PSScriptRoot/setup_env.ps1" -PythonExecutable $PythonExecutable
        } else {
            & "$PSScriptRoot/setup_env.ps1"
        }
    }
    if (-not (Test-Path -LiteralPath $environmentPython)) {
        throw "No existe el entorno. Ejecuta sin -SkipInstall para prepararlo."
    }
    $outputPath = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputRoot))
    New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
    $profilePath = Join-Path $outputPath "profile.json"
    $silverPath = Join-Path $outputPath "transactions.parquet"
    $qualityPath = Join-Path $outputPath "silver-quality.json"
    $modelRoot = Join-Path $outputPath "model"
    $modelPath = Join-Path $modelRoot "model.joblib"

    Invoke-FraudStep @("-m", "pip", "check")
    Invoke-FraudStep @("scripts/profile_fraud.py", "--output", $profilePath)
    Invoke-FraudStep @("scripts/build_silver.py", "--output", $silverPath,
        "--quality-json", $qualityPath, "--quality-markdown", (Join-Path $outputPath "silver-quality.md"))
    Invoke-FraudStep @("scripts/train_fraud.py", "--input-format", "silver", "--input", $silverPath,
        "--silver-quality", $qualityPath, "--profile", $profilePath, "--output", $modelRoot,
        "--markdown", (Join-Path $outputPath "training.md"))
    Invoke-FraudStep @("scripts/analyze_fraud_errors.py", "--input", $silverPath, "--model", $modelPath,
        "--output", (Join-Path $outputPath "errors.json"))
    Invoke-FraudStep @("scripts/analyze_fraud_patterns.py", "--input", $silverPath, "--model", $modelPath,
        "--output", (Join-Path $modelRoot "patterns.json"), "--markdown", (Join-Path $outputPath "patterns.md"))
    Invoke-FraudStep @("scripts/verify_fraud_delivery.py", "--model", $modelPath,
        "--output", (Join-Path $outputPath "delivery-check.json"))
    Write-Host "Reproducción completa. Modelo: $modelPath"
    Write-Host "Para la API configura BANKSHIELD_FRAUD_MODEL con esa ruta. Reportes: $outputPath"
} finally {
    Pop-Location
}
