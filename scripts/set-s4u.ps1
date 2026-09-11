<#
set-s4u.ps1 — 예약 작업 3종을 "로그온 여부와 관계없이 실행"(S4U)으로 바꾼다. (2026-08-21)

왜 필요한가:
  기본 등록 상태(LogonType=Interactive)는 사용자가 로그인해 있어야만 실행된다. PC를 늘 켜두더라도
  Windows 업데이트가 새벽에 재부팅해 로그인 화면에 머물러 있으면 그날 브리핑이 조용히 건너뛰어진다.
  S4U는 로그인 화면에서도 실행되며, 비밀번호를 저장하지 않는다(Password 방식과의 차이).

⚠️ 관리자 권한 필요. 일반 권한으로 Set-ScheduledTask -Principal을 호출하면 "Access is denied"가 난다.

실행:
  Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy','Bypass','-File','<이 파일>'

결과는 아래 RESULT 파일에 기록된다(권한 상승된 창은 바로 닫히므로 화면으로 확인하기 어렵다).
#>

$result = "C:\Users\mrblue\Claude\morning breifing_code\run-logs\s4u-result.log"
$dir = Split-Path $result -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

function Log([string]$m) {
    Add-Content -Path $result -Value ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) -Encoding utf8
}

Set-Content -Path $result -Value "=== S4U 변경 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -Encoding utf8

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Log "관리자 권한: $isAdmin"
if (-not $isAdmin) { Log "치명적: 관리자 권한 없음. 중단."; exit 1 }

$user = "$env:USERDOMAIN\$env:USERNAME"
Log "대상 계정: $user"

$tasks = @('MorningSectorBriefing', 'WeeklyActionReview', 'ValueChainMapUpdater', 'EntryCheck0905')
foreach ($t in $tasks) {
    try {
        $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType S4U -RunLevel Limited
        Set-ScheduledTask -TaskName $t -Principal $principal -ErrorAction Stop | Out-Null
        $now = (Get-ScheduledTask -TaskName $t).Principal.LogonType
        Log "$t : 변경 완료 (LogonType=$now)"
    } catch {
        Log "$t : 실패 - $($_.Exception.Message)"
    }
}

# --- S4U가 실제로 "실행까지" 되는지 검증 -------------------------------------
# 등록만 성공하고 실행에서 막히는 경우가 있다("이 사용자에게 요청한 로그온 유형이 부여되지
# 않았습니다" = 배치 로그온 권한 누락). 버리는 작업 하나를 만들어 실제로 돌려본다.
$probeName = '_S4UProbe'
$probeOut  = "C:\Users\mrblue\Claude\morning breifing_code\run-logs\s4u-probe.txt"
if (Test-Path $probeOut) { Remove-Item $probeOut -Force }
try {
    $cmd = "-ExecutionPolicy Bypass -NoProfile -Command `"Set-Content -Path '$probeOut' -Value (whoami) -Encoding utf8`""
    $pa = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $cmd
    $pp = New-ScheduledTaskPrincipal -UserId $user -LogonType S4U -RunLevel Limited
    $ps = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    try { Unregister-ScheduledTask -TaskName $probeName -Confirm:$false -ErrorAction Stop } catch {}
    Register-ScheduledTask -TaskName $probeName -Action $pa -Principal $pp -Settings $ps -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $probeName

    $ok = $false
    foreach ($i in 1..20) {
        Start-Sleep -Seconds 1
        if (Test-Path $probeOut) { $ok = $true; break }
    }
    if ($ok) {
        Log "S4U 실행 검증: 성공 (실행 계정: $((Get-Content $probeOut -Encoding utf8) -join ''))"
    } else {
        $info = Get-ScheduledTaskInfo -TaskName $probeName
        Log "S4U 실행 검증: 실패 (LastTaskResult=0x$('{0:X}' -f $info.LastTaskResult))"
        Log "  → 0x4DD(1245)/0x2 계열이면 '배치 작업으로 로그온' 권한 누락일 가능성이 높다."
    }
    Unregister-ScheduledTask -TaskName $probeName -Confirm:$false -ErrorAction SilentlyContinue
    if (Test-Path $probeOut) { Remove-Item $probeOut -Force }
} catch {
    Log "S4U 실행 검증: 예외 - $($_.Exception.Message)"
}

Log "=== 끝 ==="
