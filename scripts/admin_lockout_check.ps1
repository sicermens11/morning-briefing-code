<#
admin_lockout_check.ps1 — 계정 잠김 원인 찾기 (관리자 PowerShell 에서 한 번 실행 · 읽기만 · 아무것도 안 바꿈)

10/19 08:02~08:10 사이에 또 잠겼다(SelfCheck 08:10 · FetchAntc 08:58 「계정 잠김 1909」).
잠김 규칙은 10분 안에 10번 틀리면 10분 잠김. 무엇이 틀린 비밀번호로 로그인을 시도하는지 보안 기록에서 찾는다.
결과는 data\_lockout_check.txt 에 남긴다 (Claude 가 읽는다).

실행: 시작 → PowerShell 오른쪽 클릭 → 관리자로 실행 →
  & "C:\Users\mrblue\Claude\morning breifing_code\scripts\admin_lockout_check.ps1"
#>
$out = Join-Path (Split-Path $PSScriptRoot -Parent) "data\_lockout_check.txt"
$L = New-Object System.Collections.Generic.List[string]
function W($s) { $L.Add($s); Write-Output $s }

W "== 계정 잠김 확인 · $(Get-Date -f 'yyyy-MM-dd HH:mm') =="
W "-- ① 실패 로그인 기록이 켜져 있나 (auditpol)"
try { auditpol /get /subcategory:"{0CCE9215-69AE-11D9-BED3-505054503030}","{0CCE9217-69AE-11D9-BED3-505054503030}" 2>&1 | ForEach-Object { W "   $_" } } catch { W "   auditpol 실패: $($_.Exception.Message)" }

W "-- ② 최근 3일 잠김(4740)"
try {
  Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4740; StartTime=(Get-Date).AddDays(-3)} -ErrorAction Stop |
    ForEach-Object { $x=[xml]$_.ToXml(); $d=@{}; $x.Event.EventData.Data | ForEach-Object { $d[$_.Name]=$_.'#text' }
      W ("   {0:MM-dd HH:mm:ss} 잠긴 계정={1} 부른 곳={2}" -f $_.TimeCreated, $d['TargetUserName'], $d['TargetDomainName']) }
} catch { W "   4740 없음 또는 못 읽음: $($_.Exception.Message)" }

W "-- ③ 최근 3일 실패 로그인(4625) — 무엇이 · 어디서"
try {
  $ev = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625; StartTime=(Get-Date).AddDays(-3)} -ErrorAction Stop
  W "   모두 $($ev.Count)건"
  $rows = $ev | ForEach-Object { $x=[xml]$_.ToXml(); $d=@{}; $x.Event.EventData.Data | ForEach-Object { $d[$_.Name]=$_.'#text' }
    [pscustomobject]@{ 때=$_.TimeCreated; 계정=$d['TargetUserName']; 유형=$d['LogonType']; 프로세스=$d['ProcessName']; 주소=$d['IpAddress']; 기기=$d['WorkstationName']; 사유=$d['SubStatus'] } }
  W "   [묶음] 계정 · 로그온유형 · 프로세스 · 주소 · 기기 → 건수"
  $rows | Group-Object 계정,유형,프로세스,주소,기기 | Sort-Object Count -Descending | Select-Object -First 15 |
    ForEach-Object { W ("   {0,4}건  {1}" -f $_.Count, $_.Name) }
  W "   [최근 25건]"
  $rows | Sort-Object 때 -Descending | Select-Object -First 25 |
    ForEach-Object { W ("   {0:MM-dd HH:mm:ss} 계정={1} 유형={2} 프로세스={3} 주소={4} 기기={5} 사유={6}" -f $_.때, $_.계정, $_.유형, $_.프로세스, $_.주소, $_.기기, $_.사유) }
} catch { W "   4625 없음 또는 못 읽음: $($_.Exception.Message)" }

W "-- 로그온유형: 2=자리 3=네트워크(공유폴더 등) 4=예약작업(배치) 5=서비스 7=잠금해제 10=원격 · 사유 0xC000006A=비밀번호 틀림 0xC0000234=잠김"
$L | Out-File -FilePath $out -Encoding utf8
Write-Output ""
Write-Output "저장: $out — Claude 에게 「확인했어」 라고만 말해 주세요"
