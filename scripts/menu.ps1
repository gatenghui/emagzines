# -*- coding: utf-8 -*-
# 总菜单：抓取 / 定时任务 / 依赖 / 打开产物
. "$PSScriptRoot\_ui.ps1"
Set-Location $Root

while ($true) {
    Clear-Host
    Write-Title "eMagzines — 三种期刊本地抓取（The Economist / The New Yorker / TIME）"

    Write-Host "  产物目录 : $Root\library"
    Write-Host "  配置文件 : $Root\config.yaml"

    if (Test-Path (Join-Path $Root 'library')) {
        Get-ChildItem (Join-Path $Root 'library') -Directory | ForEach-Object {
            $latest = Get-ChildItem $_.FullName -Directory | Sort-Object Name -Descending | Select-Object -First 1
            if ($latest) { Write-Host ("  最近一期 : {0,-18} {1}" -f $_.Name, $latest.Name) }
        }
        if (-not (Test-Path (Join-Path $Root 'library\INDEX.md'))) { }
    } else {
        Write-Host "  最近一期 : 还没有抓取过" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "  ----------------------------------------------------------"
    Write-Host "    [1] 立即抓取（手动跑一次）"
    Write-Host "    [2] 设置每天定时抓取"
    Write-Host "    [3] 查看定时任务状态 / 最近日志"
    Write-Host "    [4] 删除定时任务"
    Write-Host "    [5] 安装 / 修复 Python 依赖"
    Write-Host "    [6] 打开产物目录"
    Write-Host "    [7] 打开总索引 INDEX.md"
    Write-Host "    [0] 退出"
    Write-Host "  ----------------------------------------------------------"
    Write-Host ""

    $ch = Read-Host "  请选择"
    switch ($ch) {
        '1' { & "$PSScriptRoot\menu_fetch.ps1" }
        '2' { & "$PSScriptRoot\ui_setup.ps1" }
        '3' { & "$PSScriptRoot\status_task.ps1"; Wait-AnyKey }
        '4' { & "$PSScriptRoot\ui_remove.ps1" }
        '5' { & "$PSScriptRoot\ui_deps.ps1" }
        '6' {
            if (Test-Path (Join-Path $Root 'library')) { Start-Process explorer.exe (Join-Path $Root 'library') }
            else { Write-Host "  还没有产物，先抓一次。" -ForegroundColor Yellow; Wait-AnyKey }
        }
        '7' {
            $idx = Join-Path $Root 'library\INDEX.md'
            if (Test-Path $idx) { Start-Process $idx } else { Write-Host "  还没有索引，先抓一次。" -ForegroundColor Yellow; Wait-AnyKey }
        }
        '0' { return }
        default { }
    }
}
