$ErrorActionPreference = "Stop"

function Resolve-CodexCli {
    $command = Get-Command codex -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $bundledRoot = Join-Path $env:LOCALAPPDATA "OpenAI\Codex\bin"
    if (Test-Path -LiteralPath $bundledRoot) {
        $bundled = Get-ChildItem -LiteralPath $bundledRoot -Recurse -File -Filter "codex.exe" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($bundled) {
            return $bundled.FullName
        }
    }

    throw @"
Codex CLI was not found in PATH or Codex Desktop.
Install it from the official guide: https://developers.openai.com/codex/cli
Then reopen PowerShell and run this script again.
"@
}

$codexCli = Resolve-CodexCli
$codexDirectory = Split-Path -Parent $codexCli
if (($env:Path -split ";") -notcontains $codexDirectory) {
    $env:Path = "$codexDirectory;$env:Path"
}

& $codexCli login status
if ($LASTEXITCODE -eq 0) {
    Write-Host "Codex is already signed in." -ForegroundColor Green
    return
}

Write-Host "Starting Codex ChatGPT sign-in..." -ForegroundColor Cyan
& $codexCli login
if ($LASTEXITCODE -ne 0) {
    throw "Codex login did not complete successfully."
}

& $codexCli login status
if ($LASTEXITCODE -ne 0) {
    throw "Codex still reports that it is not signed in."
}
Write-Host "Codex login complete." -ForegroundColor Green
