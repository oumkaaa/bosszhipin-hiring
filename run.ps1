#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$RuntimeDir = "D:\boss-hiring-runtime\default",
    [switch]$Live
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
if ($Live) {
    Write-Host "Mode: LIVE" -ForegroundColor Yellow
} else {
    Write-Host "Mode: DRY-RUN" -ForegroundColor Yellow
}

$ScriptPath = if ($PSCommandPath) { $PSCommandPath } elseif ($MyInvocation.MyCommandPath) { $MyInvocation.MyCommandPath } else { $PWD.Path }
$ScriptDir = Split-Path -Parent $ScriptPath
Push-Location $ScriptDir

try {
    $ArgsList = @("-m", "boss_hr_recruiter", "$RuntimeDir")
    if ($Live) {
        $ArgsList += "--live"
    }
    python @ArgsList
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
