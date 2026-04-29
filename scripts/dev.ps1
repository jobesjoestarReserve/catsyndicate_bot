param(
    [switch]$NoCode,
    [switch]$NoCheck,
    [switch]$Bot
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path $Python)) {
    throw "Local Python was not found at $Python. Create .venv first, then rerun this script."
}

function Start-VSCode {
    $CodeCommand = Get-Command code -ErrorAction SilentlyContinue
    if ($CodeCommand) {
        & $CodeCommand.Source $ProjectRoot
        return
    }

    $CommonCodePaths = @(
        "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe",
        "$env:ProgramFiles\Microsoft VS Code\Code.exe",
        "${env:ProgramFiles(x86)}\Microsoft VS Code\Code.exe"
    )

    foreach ($Path in $CommonCodePaths) {
        if ($Path -and (Test-Path $Path)) {
            Start-Process -FilePath $Path -ArgumentList "`"$ProjectRoot`""
            return
        }
    }

    Write-Warning "VS Code was not found in PATH or common install locations. Open the project manually: $ProjectRoot"
}

if (-not $NoCode) {
    Start-VSCode
}

if (-not $NoCheck) {
    & $Python -m unittest discover
    & $Python -m compileall main.py data database handlers services
}

if ($Bot) {
    & $Python main.py
}
