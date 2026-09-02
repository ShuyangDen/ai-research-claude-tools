$ErrorActionPreference = "Stop"
$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $appRoot ".venv\Scripts\python.exe"
$frontend = Join-Path $appRoot "frontend\dist\index.html"
$loginScript = Join-Path $appRoot "login.ps1"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Workbench is not installed. Run apps\research-workbench\setup.ps1 first."
}
if (-not (Test-Path -LiteralPath $frontend)) {
    throw "Frontend build is missing. Run apps\research-workbench\setup.ps1 first."
}

if ($env:RESEARCH_WORKBENCH_STATE_ROOT) {
    New-Item -ItemType Directory -Path $env:RESEARCH_WORKBENCH_STATE_ROOT -Force | Out-Null
}

& $loginScript

& $python -m research_workbench --port 8765
