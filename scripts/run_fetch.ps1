# -*- coding: utf-8 -*-
<#
    统一抓取入口。手动双击（立即抓取.bat）和定时任务都调用它。
    例：
      pwsh -File scripts\run_fetch.ps1
      pwsh -File scripts\run_fetch.ps1 -Only te,ny
      pwsh -File scripts\run_fetch.ps1 -Limit 10 -NoPdf
      pwsh -File scripts\run_fetch.ps1 -Scheduled
#>
param(
    [switch]$Scheduled,
    [string]$Only = "",
    [string]$Date = "",
    [int]$Limit = 0,
    [switch]$NoPdf,
    [switch]$NoEpub,
    [switch]$NoMd,
    [switch]$Open,
    [switch]$YesPdf
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logDir = Join-Path $root 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

function Resolve-Python {
    foreach ($cand in @('python', 'python3', 'py')) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

$py = Resolve-Python
if (-not $py) {
    Write-Host "[X] 没有找到 Python，请先安装 Python 3.10+ 并勾选 Add to PATH" -ForegroundColor Red
    exit 127
}

# 依赖自检一次（只检查，不自动联网装）
& $py -c "import requests, bs4, lxml, yaml, PIL" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] 依赖不全，正在安装 requirements.txt ..." -ForegroundColor Yellow
    & $py -m pip install -r (Join-Path $root 'requirements.txt') --disable-pip-version-check
}

$argsList = @('main.py')
if ($Only)    { $argsList += @('--only', $Only) }
if ($Date)    { $argsList += @('--date', $Date) }
if ($Limit -gt 0) { $argsList += @('--limit', "$Limit") }
if ($NoPdf)   { $argsList += '--no-pdf' }
if ($NoEpub)  { $argsList += '--no-epub' }
if ($NoMd)    { $argsList += '--no-md' }
if ($Open)    { $argsList += '--open' }
if ($Scheduled) { $argsList += '--scheduled' }

if (-not $Scheduled) {
    Write-Host ""
    Write-Host "================ eMagzines 抓取开始 ================" -ForegroundColor Cyan
    Write-Host ("python " + ($argsList -join ' ')) -ForegroundColor DarkGray
    Write-Host ""
}

$env:PYTHONIOENCODING = 'utf-8'
& $py @argsList
$code = $LASTEXITCODE

if (-not $Scheduled) {
    Write-Host ""
    if ($code -eq 0) {
        Write-Host "================ 完成，产物在 library\ ================" -ForegroundColor Green
    } else {
        Write-Host "================ 结束，但有期刊抓取失败（见上方日志） ================" -ForegroundColor Yellow
    }
}
exit $code
