# admin_lockout_fix.ps1 — **관리자 권한으로 한 번만** 실행한다 (2026-10-16)
#
# 왜: 매일 작업이 계정 잠김(오류 1909)으로 10/13·10/14·10/15 09:05 에 못 돌았다.
#     「10분 안에 10번 틀리면 잠금」 인데, 누가 틀리는지 기록이 꺼져 있어 못 찾았다(9/29 도 같음).
# 하는 일 (사용자 10/16 「1번은 너 권고대로 해」):
#   ① 실패한 로그인을 기록한다 → 다음에 잠기면 보안 기록 4625 에 어느 기기(주소)가 틀렸는지 남는다
#   ② 누가 로그인해 있는 동안은 Windows 업데이트가 컴퓨터를 저절로 다시 시작하지 않게 한다
#      (10/15 01:34 처럼 밤에 재시작되면 「로그인해 있을 때 실행」 작업이 멈춘다)
# 하지 않는 일: 잠금 정책은 그대로 둔다(끄면 비밀번호 찍어 보기를 못 막는다)
#
# 실행: 시작 → 「PowerShell」 오른쪽 클릭 → 관리자 권한으로 실행 → 아래 한 줄
#   powershell -ExecutionPolicy Bypass -File "C:\Users\mrblue\Claude\morning breifing_code\scripts\admin_lockout_fix.ps1"

$ErrorActionPreference = 'Stop'
$me = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $me.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Output "관리자 권한이 아닙니다. 'PowerShell' 을 오른쪽 클릭 → '관리자 권한으로 실행' 으로 다시 열어 주세요."
    exit 1
}

# ① 실패한 로그인 기록 켜기 (하위 범주 GUID — 한글 Windows 에서도 이름 없이 된다)
#    {0CCE9215-...} = 로그온 · {0CCE9217-...} = 계정 잠금
auditpol /set /subcategory:"{0CCE9215-69AE-11D9-BED3-505054503030}" /failure:enable | Out-Null
auditpol /set /subcategory:"{0CCE9217-69AE-11D9-BED3-505054503030}" /failure:enable | Out-Null
Write-Output "① 실패한 로그인 기록: 켬"
auditpol /get /subcategory:"{0CCE9215-69AE-11D9-BED3-505054503030}"

# ② 로그인해 있는 동안 업데이트 자동 재시작 막기
$k = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU'
if (-not (Test-Path $k)) { New-Item -Path $k -Force | Out-Null }
New-ItemProperty -Path $k -Name NoAutoRebootWithLoggedOnUsers -PropertyType DWord -Value 1 -Force | Out-Null
Write-Output "② 로그인해 있을 때 업데이트 자동 재시작: 막음"

# 지금 계정이 잠겨 있는지
# ⚠️ 10/16 관리자 창에서 이 줄이 null 오류를 냈다(①②는 이미 끝난 뒤 · 무해) → 못 찾아도 멈추지 않게
$a = net user $env:USERNAME | Select-String -Pattern 'Account active|활성' | Select-Object -First 1
Write-Output ("지금 계정 상태: " + $(if ($a) { $a.ToString().Trim() } else { "(못 읽음 · Claude 가 따로 확인)" }))
Write-Output ""
Write-Output "끝. 다음에 계정이 잠기면 Claude 가 보안 기록 4625 로 어느 기기가 틀렸는지 찾습니다."
