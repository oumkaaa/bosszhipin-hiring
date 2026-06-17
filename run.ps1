#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$RuntimeDir = "D:\boss-hiring-runtime\default"
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

try {
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Console]::OutputEncoding
} catch {}

if (-not (Test-Path -LiteralPath $RuntimeDir -PathType Container)) {
    Write-Host "Runtime directory does not exist: $RuntimeDir" -ForegroundColor Red
    exit 1
}

Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "Boss Zhipin Hiring Assistant - Starting" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "Runtime directory: $RuntimeDir" -ForegroundColor Yellow

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommandPath
Push-Location $ScriptDir

try {
    python -m boss_hr_recruiter "$RuntimeDir"
    $ExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($ExitCode -eq 0) {
    Write-Host "Completed successfully" -ForegroundColor Green
} else {
    Write-Host "Failed with exit code: $ExitCode" -ForegroundColor Red
}

exit $ExitCode
