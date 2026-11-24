# -*- coding: utf-8 -*-
<#
    删除定时任务。
    用法：pwsh -File scripts\remove_task.ps1 [-Name eMagzines-Daily]
#>
param([string]$Name = "")

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot

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

try {
    Get-ScheduledTask -TaskName $Name -ErrorAction Stop | Out-Null
} catch {
    Write-Host ("没有找到任务 " + $Name + "，无需删除。") -ForegroundColor Yellow
    exit 0
}

try {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction Stop
    Write-Host ("[OK] 已删除计划任务: " + $Name) -ForegroundColor Green
    exit 0
} catch {
    Write-Host ("[!] 删除失败：" + $_.Exception.Message) -ForegroundColor Yellow
    & schtasks.exe /Delete /F /TN $Name | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host ("[OK] 已用 schtasks 删除: " + $Name) -ForegroundColor Green
        exit 0
    }
    Write-Host "[X] 删除失败（可能需要管理员权限）" -ForegroundColor Red
    exit 1
}
