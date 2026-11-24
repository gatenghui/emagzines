# -*- coding: utf-8 -*-
# 交互式设置定时任务
. "$PSScriptRoot\_ui.ps1"
Set-Location $Root

Clear-Host
Write-Title "设置每天自动抓取（Windows 计划任务）"

$py = Resolve-Python
$defaultTime = '08:30'
$defaultName = 'eMagzines-Daily'
if ($py) {
    $probe = & $py -c "import yaml,sys;c=yaml.safe_load(open(sys.argv[1],encoding='utf-8')) or {};s=c.get('schedule') or {};print(s.get('daily_time','08:30'));print(s.get('task_name','eMagzines-Daily'))" (Join-Path $Root 'config.yaml') 2>$null
    if ($probe) {
        $defaultTime = ($probe -split "`n")[0].Trim()
        $defaultName = ($probe -split "`n")[1].Trim()
    }
}

Write-Host "  直接回车 = 用 config.yaml 里的时间：$defaultTime"
Write-Host "  也可以输入 HH:mm，例如 07:30"
Write-Host ""
$t = Read-Host "  每天几点跑 [$defaultTime]"
if ([string]::IsNullOrWhiteSpace($t)) { $t = $defaultTime }
if ($t -notmatch '^\d{1,2}:\d{2}$') {
    Write-Host "  [X] 时间格式要 HH:mm" -ForegroundColor Red
    Wait-AnyKey
    return
}

& "$PSScriptRoot\setup_task.ps1" -Time $t -Name $defaultName
Wait-AnyKey
