# -*- coding: utf-8 -*-
# 安装 Python 依赖
. "$PSScriptRoot\_ui.ps1"
Set-Location $Root

Clear-Host
Write-Title "安装 / 修复 Python 依赖"

$py = Resolve-Python
if (-not $py) {
    Write-Host "  [X] 没找到 Python。请先安装 Python 3.10+，安装时勾选 Add python.exe to PATH。" -ForegroundColor Red
    Start-Sleep -Seconds 3
    return
}

Write-Host "  使用的是：$py"
Write-Host ""
$env:PYTHONIOENCODING = 'utf-8'
& $py -m pip install -r (Join-Path $Root 'requirements.txt') --disable-pip-version-check
Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] 依赖就绪" -ForegroundColor Green
} else {
    Write-Host "  [!] 安装过程有报错，看上面输出" -ForegroundColor Yellow
}
Wait-AnyKey
