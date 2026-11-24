# -*- coding: utf-8 -*-
# 立即抓取菜单
. "$PSScriptRoot\_ui.ps1"
Set-Location $Root

Clear-Host
Write-Title "立即抓取 — 产物会写进 library\"

Write-Host "    1. 三种都抓（默认，推荐）"
Write-Host "    2. 只抓 The Economist"
Write-Host "    3. 只抓 The New Yorker"
Write-Host "    4. 只抓 TIME"
Write-Host "    5. 三种都抓，但不生成 PDF（更快）"
Write-Host "    0. 返回"
Write-Host ""

$ch = Read-Host "  请选择 [1]"
if ([string]::IsNullOrWhiteSpace($ch)) { $ch = '1' }

$params = @{}
switch ($ch) {
    '1' { }
    '2' { $params['Only'] = 'te' }
    '3' { $params['Only'] = 'ny' }
    '4' { $params['Only'] = 'time' }
    '5' { $params['NoPdf'] = $true }
    '0' { return }
    default { $params['Only'] = '' }
}
$params['Open'] = $true

& "$PSScriptRoot\run_fetch.ps1" @params
Wait-AnyKey
