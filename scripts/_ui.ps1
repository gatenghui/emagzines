# -*- coding: utf-8 -*-
# 所有 UI 脚本共用的控制台初始化（由其它脚本 dot-source 引入）

try { chcp 65001 > $null } catch { }
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
try { $Host.UI.RawUI.WindowTitle = 'eMagzines' } catch { }

$script:Root = Split-Path -Parent $PSScriptRoot

function Resolve-Python {
    foreach ($cand in @('python', 'python3', 'py')) {
        $c = Get-Command $cand -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
    }
    return $null
}

function Wait-AnyKey {
    Write-Host ""
    Write-Host "  按任意键继续..." -ForegroundColor DarkGray
    try { $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') } catch { Start-Sleep -Seconds 1 }
}

function Write-Title($text) {
    Write-Host ""
    Write-Host ("  " + ("=" * 56)) -ForegroundColor DarkCyan
    Write-Host ("    " + $text) -ForegroundColor Cyan
    Write-Host ("  " + ("=" * 56)) -ForegroundColor DarkCyan
    Write-Host ""
}
