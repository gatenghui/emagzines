# -*- coding: utf-8 -*-
# 交互式删除定时任务
. "$PSScriptRoot\_ui.ps1"
Set-Location $Root

Clear-Host
Write-Title "删除每日自动抓取任务"

$y = Read-Host "  确认删除？[y/N]"
if ($y -notmatch '^(y|Y)$') {
    Write-Host "  已取消。" -ForegroundColor Yellow
    Wait-AnyKey
    return
}

& "$PSScriptRoot\remove_task.ps1"
Wait-AnyKey
