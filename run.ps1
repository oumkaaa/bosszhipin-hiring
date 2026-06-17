# Boss直聘招聘助手 - Windows启动脚本
# 用法: .\run.ps1 "D:\path\to\runtime_dir"

param(
    [string]$RuntimeDir = "D:\boss-hiring-runtime\default"
)

# 设置UTF-8编码（解决GBK问题）
$env:PYTHONIOENCODING = 'utf-8'

# 验证运行时目录
if (-not (Test-Path $RuntimeDir)) {
    Write-Host "✗ 运行时目录不存在: $RuntimeDir" -ForegroundColor Red
    exit 1
}

Write-Host "=" * 60 -ForegroundColor Green
Write-Host "Boss直聘招聘助手启动" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "运行时目录: $RuntimeDir" -ForegroundColor Yellow
Write-Host ""

# 进入脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommandPath
Push-Location $ScriptDir

# 运行主程序
python -m boss_hr_recruiter.main "$RuntimeDir"

$ExitCode = $LASTEXITCODE
Pop-Location

if ($ExitCode -eq 0) {
    Write-Host ""
    Write-Host "✓ 执行完成" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ 执行失败 (退出码: $ExitCode)" -ForegroundColor Red
}

exit $ExitCode
