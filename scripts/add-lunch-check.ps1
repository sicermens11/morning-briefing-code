#requires -RunAsAdministrator
<#
  add-lunch-check.ps1 — 평일 12:20 점심 진입체크 예약작업 생성 (2026-08-26 신설)

  ⚠️ 관리자 권한이 필요하다. S4U(로그온 여부와 관계없이 실행) 작업은 일반 권한으로 등록되지 않는다.
     실행: 시작 → "PowerShell" 우클릭 → "관리자 권한으로 실행" → 이 파일 경로를 붙여넣고 Enter

  ⚠️ **이 파일은 반드시 BOM 있는 UTF-8로 저장한다.** PowerShell 5.1은 BOM이 없으면
     .ps1을 ANSI(cp949)로 읽어 한글 문자열이 깨진 채 실행된다. 2026-08-26 최초 실행에서
     -Description에 깨진 글자가 그대로 등록됐다. 화면 출력만의 문제가 아니다.
  왜 12:20인가:
    사용자가 회사에 있어 실제로 볼 수 있는 시간은 **출근 전(~09:30)과 점심(12:30~13:30)** 두 번뿐이다.
    09:05은 "재료가 시초가에 이미 반영됐나"를 답한다 — 그 시각엔 추세·수급이 아직 노이즈다.
    12:20은 **오전 흐름이 확정된 뒤**라 다른 질문에 답한다: "오전에 조건이 충족됐나, 흐름이 살아있나".

  ⚠️ entry-check 스킬과 check_entry.py는 **이미 1220 슬롯을 지원한다.** 없던 것은 예약작업뿐이다.
#>
$ErrorActionPreference = 'Stop'
$src = Get-ScheduledTask -TaskName 'EntryCheck0905'   # 09:05 작업을 그대로 복제한다

$action = New-ScheduledTaskAction -Execute $src.Actions[0].Execute `
    -Argument ($src.Actions[0].Arguments -replace '0905', '1220')

$trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At '12:20'

# ⚠️ LogonType S4U — 로그온하지 않아도 실행된다(비밀번호 저장 없이).
$principal = New-ScheduledTaskPrincipal -UserId $src.Principal.UserId `
    -LogonType S4U -RunLevel $src.Principal.RunLevel

# ⚠️ ExecutionTimeLimit 20분 — 진입체크는 실측 32초다. 20분이면 넉넉하고,
#    행(hang)이 나도 다음 실행을 막지 않는다.
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

Register-ScheduledTask -TaskName 'EntryCheck1220' -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description '평일 12:20 점심 진입체크 — 오전 흐름 반영 (2026-08-26 신설)' -Force | Out-Null

Get-ScheduledTask | Where-Object TaskName -like 'EntryCheck*' | ForEach-Object {
    $i = $_ | Get-ScheduledTaskInfo
    '{0,-18} {1,-8} 다음 {2}' -f $_.TaskName, $_.State, $i.NextRunTime
}
Write-Output ''
Write-Output '생성 완료. 확인할 것: EntryCheck1220이 Ready이고 다음 실행이 평일 12:20인지.'
