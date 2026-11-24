# -*- coding: utf-8 -*-
<#
    查看定时任务状态 + 最近抓取结果。
    用法：pwsh -File scripts\status_task.ps1 [-Name eMagzines-Daily]
#>
param([string]$Name = "", [int]$TailLines = 20)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Resolve-Python {
    foreach ($cand in @('python', 'python3', 'py')) {
        $c = Get-Command $cand -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
    }
    return $null
}

if (-not $Name) {
    $py = Resolve-Python
    if ($py) {
        $n = & $py -c "import yaml,sys;c=yaml.safe_load(open(sys.argv[1],encoding='utf-8')) or {};print((c.get('schedule') or {}).get('task_name','eMagzines-Daily'))" (Join-Path $root 'config.yaml') 2>$null
        if ($n) { $Name = $n.Trim() }
    }
    if (-not $Name) { $Name = 'eMagzines-Daily' }
}

function Show-Table($title) { Write-Host ""; Write-Host "=== $title ===" -ForegroundColor Cyan }

Show-Table "计划任务"
try {
    $t = Get-ScheduledTask -TaskName $Name -ErrorAction Stop
    $i = Get-ScheduledTaskInfo -TaskName $Name
    $stateColor = if ($t.State -eq 'Disabled') { 'Yellow' } else { 'Green' }
    Write-Host ("任务名   : " + $t.TaskName)
    Write-Host ("状态     : " + $t.State) -ForegroundColor $stateColor
    $resText = if ($i.LastTaskResult -eq 0) { '(成功)' } else { '(非 0，见日志)' }
    Write-Host ("上次运行 : " + $i.LastRunTime)
    Write-Host ("上次结果 : " + $i.LastTaskResult + "  " + $resText)
    Write-Host ("下次运行 : " + $i.NextRunTime)
    $act = $t.Actions | Select-Object -First 1
    Write-Host ("触发     : " + (($t.Triggers | ForEach-Object { $_.StartBoundary }) -join ', '))
    Write-Host ("动作     : " + $act.Execute + " " + $act.Arguments)
} catch {
    Write-Host ("没有找到名为 " + $Name + " 的计划任务。") -ForegroundColor Yellow
    Write-Host "注册：scripts\设置定时任务.bat" -ForegroundColor Gray
}

Show-Table "本机所有 eMagzines 相关任务"
$all = Get-ScheduledTask -TaskName 'eMagzines*' -ErrorAction SilentlyContinue
if ($all) {
    $all | Select-Object TaskName, State | Format-Table -AutoSize | Out-String | Write-Host
} else {
    Write-Host "（无）"
}

Show-Table "本地库"
if (Test-Path (Join-Path $root 'library')) {
    $dirs = Get-ChildItem (Join-Path $root 'library') -Directory | ForEach-Object {
        Get-ChildItem $_.FullName -Directory | Sort-Object Name -Descending | Select-Object -First 1
    } | Where-Object { $_ }
    if ($dirs) {
        $dirs | ForEach-Object {
            $files = Get-ChildItem $_.FullName -File | Where-Object { $_.Extension -in '.pdf', '.epub', '.md' }
            $mb = [math]::Round((($files | Measure-Object Length -Sum).Sum) / 1MB, 2)
            Write-Host ("{0,-20} {1,-12} {2} 个文件 / {3} MB  ->  {4}" -f $_.Parent.Name, $_.Name, $files.Count, $mb, $_.FullName)
        }
    } else {
        Write-Host "（还没有抓过东西）"
    }
} else {
    Write-Host "（library 目录还不存在，先跑一次 立即抓取.bat）"
}

Show-Table "最近日志（$TailLines 行）"
$logs = Get-ChildItem (Join-Path $root 'logs') -Filter 'emagzines-*.log' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($logs) {
    Write-Host ("文件: " + $logs.FullName + "  (更新于 " + $logs.LastWriteTime + ")") -ForegroundColor DarkGray
    Get-Content $logs.FullName -Tail $TailLines -Encoding UTF8 | Write-Host
} else {
    Write-Host "（还没有日志）"
}
Write-Host ""
