# -*- coding: utf-8 -*-
<#
    注册 Windows 计划任务：每天固定时间跑一次抓取。

    用法：
      pwsh -File scripts\setup_task.ps1                 # 用 config.yaml 里的 schedule.daily_time
      pwsh -File scripts\setup_task.ps1 -Time 07:30
      pwsh -File scripts\setup_task.ps1 -Time 07:30 -Only te,ny
      pwsh -File scripts\setup_task.ps1 -Remove         # 等价于 remove_task.ps1
#>
param(
    [string]$Time = "",
    [string]$Only = "",
    [string]$Name = "",
    [string]$ConfigPath = "",
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Resolve-Python {
    foreach ($cand in @('python', 'python3', 'py')) {
        $c = Get-Command $cand -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
    }
    return $null
}

$py = Resolve-Python
if (-not $py) {
    Write-Host "[X] 没有找到 Python，请先安装 Python 3.10+ 并勾选 Add to PATH" -ForegroundColor Red
    exit 127
}

# 从 config.yaml 读默认值
$cfgFile = if ($ConfigPath) { $ConfigPath } else { Join-Path $root 'config.yaml' }
if (-not $Time -or -not $Name) {
    $probe = & $py -c "import yaml,sys;c=yaml.safe_load(open(sys.argv[1],encoding='utf-8')) or {};s=c.get('schedule') or {};print(s.get('daily_time','08:30'));print(s.get('task_name','eMagzines-Daily'))" $cfgFile
    if ($LASTEXITCODE -eq 0 -and $probe) {
        if (-not $Time) { $Time = ($probe -split "`n")[0].Trim() }
        if (-not $Name) { $Name = ($probe -split "`n")[1].Trim() }
    }
}
if (-not $Time) { $Time = '08:30' }
if (-not $Name) { $Name = 'eMagzines-Daily' }

if ($Remove) {
    & (Join-Path $PSScriptRoot 'remove_task.ps1') -Name $Name
    exit $LASTEXITCODE
}

if ($Time -notmatch '^\d{1,2}:\d{2}$') {
    Write-Host "[X] 时间格式要 HH:mm，例如 08:30" -ForegroundColor Red
    exit 2
}

$shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { (Get-Command pwsh).Source } else { (Get-Command powershell).Source }
$script = Join-Path $PSScriptRoot 'run_fetch.ps1'
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`" -Scheduled"
if ($Only) { $argLine += " -Only $Only" }

Write-Host "任务名称 : $Name"
Write-Host "执行时间 : 每天 $Time"
Write-Host "运行目录 : $root"
Write-Host "命令     : $shell $argLine"
Write-Host ""

$ok = $false
try {
    $action = New-ScheduledTaskAction -Execute $shell -Argument $argLine -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -Daily -At $Time
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
        -MultipleInstances IgnoreNew
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings `
        -Principal $principal -Description "eMagzines 每日抓取三种期刊最新一期" -Force | Out-Null
    $ok = $true
} catch {
    Write-Host "[!] Register-ScheduledTask 失败：$($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "    改用 schtasks 回退方案 ..." -ForegroundColor Yellow
    $tr = "`"$shell`" $argLine"
    & schtasks.exe /Create /F /SC DAILY /ST $Time /TN $Name /TR $tr | Out-Null
    if ($LASTEXITCODE -eq 0) { $ok = $true }
}

if ($ok) {
    Write-Host "[OK] 定时任务已注册" -ForegroundColor Green
    Write-Host "     查看状态：scripts\查看定时任务.bat" -ForegroundColor Gray
    Write-Host "     立即测试：schtasks /Run /TN `"$Name`"" -ForegroundColor Gray
    Write-Host "     取消任务：scripts\删除定时任务.bat" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "[X] 定时任务注册失败" -ForegroundColor Red
    exit 1
}
