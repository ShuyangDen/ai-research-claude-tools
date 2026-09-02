$ErrorActionPreference = "Stop"
$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $appRoot)
$venvPython = Join-Path $appRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    python -m venv (Join-Path $appRoot ".venv")
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $venvPython -m pip install -e (Join-Path $repoRoot "packages\research-core") -e ((Join-Path $appRoot "backend") + "[test]")
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed" }

Push-Location (Join-Path $appRoot "frontend")
try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
} finally {
    Pop-Location
}

Write-Host "Research Workbench is ready."
Write-Host "The first paper-reading handoff will create the Codex task 论文阅读 · Trevor automatically."
Write-Host "Then run apps\research-workbench\start.ps1"
