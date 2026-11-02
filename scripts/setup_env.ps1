param(
    # Ruta o nombre de un intérprete Python 3.12; si se omite, usa py -3.12.
    [string]$PythonExecutable = "",
    [switch]$UseLock,
    [string]$EnvironmentDirectory = ".venv-pruebas",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$environmentRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $EnvironmentDirectory))
$environmentPython = Join-Path $environmentRoot "Scripts/python.exe"

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falló '$Executable' (código $LASTEXITCODE). Revisa la salida anterior."
    }
}

Push-Location $projectRoot
try {
    if ($UseLock -and -not (Test-Path -LiteralPath 'requirements/lock-py312-windows.txt')) {
        throw 'Falta requirements/lock-py312-windows.txt; no se sustituye silenciosamente por rangos.'
    }
    if (-not (Test-Path -LiteralPath $environmentPython)) {
        if ($PythonExecutable) {
            Invoke-Checked $PythonExecutable @("-c", "import sys; assert sys.version_info[:2] == (3, 12), 'Se requiere Python 3.12'")
            Invoke-Checked $PythonExecutable @("-m", "venv", $environmentRoot)
        } else {
            Invoke-Checked "py" @("-3.12", "-m", "venv", $environmentRoot)
        }
    }

    Invoke-Checked $environmentPython @("-c", "import sys; assert sys.version_info[:2] == (3, 12), 'El entorno existente debe usar Python 3.12'")
    if ($UseLock) {
        # setuptools/wheel forman parte del lock; no crear otro entorno de build.
        Invoke-Checked $environmentPython @("-m", "pip", "install", "-r", "requirements/lock-py312-windows.txt")
        Invoke-Checked $environmentPython @("-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", ".")
    } else {
        Invoke-Checked $environmentPython @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-Checked $environmentPython @("-m", "pip", "install", "-r", "requirements/common.txt")
    }
    Invoke-Checked $environmentPython @("-m", "pip", "check")

    if (-not $SkipTests) {
        Invoke-Checked $environmentPython @("-m", "unittest", "discover", "-s", "tests/unit", "-v")
    }
    Write-Host "Entorno preparado. Usa $environmentPython para ejecutar el proyecto."
    if ($SkipTests) {
        Write-Host "Las pruebas se omitieron; ejecuta la suite antes de declarar validado el entorno."
    }
} finally {
    Pop-Location
}
