# ══════════════════════════════════════════════════════════════
#  페이지 파일을 고정 크기로 — 재부팅해도 커밋 한도가 안 줄게 (2026-09-29)
#
#  ⚠️ **관리자 권한 PowerShell** 에서 실행한다:
#     시작 → PowerShell 오른쪽 클릭 → 「관리자 권한으로 실행」 →
#     & "C:\Users\mrblue\Claude\morning breifing_code\scripts\set-pagefile.ps1"
#
#  왜 — 페이지 파일이 「자동 관리」라 재부팅하면 처음 크기(2GB)로 돌아간다.
#       커밋 한도 = 램 31.9GB + 페이지 파일 → 45GB 였던 것이 34GB 로 줄었다(9/29 16:17 재부팅).
#       판(시험)은 뜨기 **전에** 커밋 여유 18GB 를 보는데, 판이 떠야 Windows 가 파일을 늘리므로
#       **늘어날 기회가 없어** 계속 기다렸다.
#  무엇 — C:\pagefile.sys 를 **처음 16GB · 최대 32GB** 로 고정 (C: 여유 약 60GB)
#         → 다음 재부팅부터 커밋 한도 약 48GB (필요하면 64GB 까지)
#  ⚠️ **재부팅은 하지 않는다.** 다음에 켤 때부터 적용된다.
#     판이 도는 중에 재부팅하면 판이 날아간다 — 판이 끝난 뒤 자연스럽게 재부팅될 때 먹는다
#  되돌리기 — 관리자 PowerShell 에서:
#     Get-CimInstance Win32_ComputerSystem | Set-CimInstance -Property @{AutomaticManagedPagefile=$true}
# ══════════════════════════════════════════════════════════════

$관리자 = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $관리자) {
    Write-Host "관리자 권한 PowerShell 에서 실행하세요 (오른쪽 클릭 → 관리자 권한으로 실행)" -ForegroundColor Red
    exit 1
}

$처음MB = 16384
$최대MB = 32768

Write-Host "=== 지금 ===" -ForegroundColor Yellow
$cs = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
"자동 관리: {0}" -f $cs.AutomaticManagedPagefile
"커밋 한도: {0} GB" -f [math]::Round($os.TotalVirtualMemorySize / 1MB, 1)
Get-CimInstance Win32_PageFileUsage | ForEach-Object { "페이지 파일: {0} · 지금 {1} GB" -f $_.Name, [math]::Round($_.AllocatedBaseSize / 1024, 1) }

Write-Host ""
Write-Host "① 자동 관리 끄기..." -ForegroundColor Cyan
if ($cs.AutomaticManagedPagefile) {
    $cs | Set-CimInstance -Property @{ AutomaticManagedPagefile = $false }
}

Write-Host "② C:\pagefile.sys 를 처음 $([math]::Round($처음MB/1024))GB · 최대 $([math]::Round($최대MB/1024))GB 로..." -ForegroundColor Cyan
$pf = Get-CimInstance Win32_PageFileSetting | Where-Object { $_.Name -ieq 'C:\pagefile.sys' }
if ($pf) {
    $pf | Set-CimInstance -Property @{ InitialSize = [uint32]$처음MB; MaximumSize = [uint32]$최대MB }
} else {
    New-CimInstance -ClassName Win32_PageFileSetting -Property @{
        Name = 'C:\pagefile.sys'; InitialSize = [uint32]$처음MB; MaximumSize = [uint32]$최대MB } | Out-Null
}

Write-Host ""
Write-Host "=== 확인 ===" -ForegroundColor Yellow
"자동 관리: {0}   (False 여야 한다)" -f (Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile
Get-CimInstance Win32_PageFileSetting | ForEach-Object {
    "설정: {0} · 처음 {1} MB · 최대 {2} MB" -f $_.Name, $_.InitialSize, $_.MaximumSize
}
Write-Host ""
Write-Host "✅ 다음 재부팅부터 적용됩니다. **지금 재부팅하지 마세요** — 밤 시험이 돌고 있으면 날아갑니다." -ForegroundColor Green
