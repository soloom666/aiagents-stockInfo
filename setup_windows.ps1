param(
    [string]$PythonCmd = "python",
    [switch]$InstallQuant
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "Project root: $ProjectRoot"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment at .venv ..."
    & $PythonCmd -m venv $VenvPath
}
else {
    Write-Host "Using existing virtual environment at .venv ..."
}

Write-Host "Upgrading pip inside .venv ..."
& $VenvPython -m pip install --upgrade pip

Write-Host "Installing main dependencies ..."
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

if ($InstallQuant) {
    Write-Host "Installing optional quant dependencies ..."
    & $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements-quant.txt")
}

Write-Host ""
Write-Host "Done."
Write-Host "Activate with: .\.venv\Scripts\Activate.ps1"
Write-Host "Run with:      .\.venv\Scripts\python.exe -m streamlit run app.py"
