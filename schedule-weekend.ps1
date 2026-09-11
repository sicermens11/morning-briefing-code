# schedule-weekend.ps1 — 금·토·일 자동 탐색 예약 (2026-09-03 작성)
#
# 사용자 요청:
#   "금요일 퇴근 이후 금토일 종일 PC가 돌아가도록 켜놓고 갈건데
#    그때 너가 자체적으로 필요한 테스트 시뮬레이션을 했으면 좋겠어서야"
#
# ⚠️ 나(모델)는 대화 세션에서만 동작한다. 사용자가 없으면 새 시험을 만들 수 없다.
#    ⇒ 대신 **미리 짜둔 조합 격자를 자동으로 훑는다.**
#       결과는 data\_search\ 에 쌓이고, 월요일에 내가 읽고 판정한다.
#
# ⚠️⚠️ 다중검정 위험:
#    수천 개를 보면 우연히 좋은 게 반드시 나온다.
#    그래서 auto_search.py는 모든 조합에 **세 판**을 다 잰다:
#      (1) 10.4년 전체  (2) 8.8년(2025·26 제외)  (3) 걷기검증
#    셋 다 통과한 것만 후보로 남기고, **걷기검증 연평균 순**으로 정렬한다.
#    ⇒ 그래도 월요일에 **순열검정**으로 다시 걸러야 한다. 그건 내가 해야 하는 일이다.
#
# 시간 배분:
#   금 19:00  6시간 (21,600초)  — 퇴근 직후 시작
#   토 09:00  12시간 (43,200초)
#   토 22:00  10시간 (36,000초)
#   일 09:00  12시간 (43,200초)
#   일 22:00  8시간 (28,800초)
#   ⇒ 총 48시간. 조합 하나에 20~60초쯤 걸리니 대략 3,000~8,000개
#   ⚠️ 이어받기가 된다 (이미 본 조합은 건너뛴다). 중간에 멈춰도 손해가 없다

$py = 'C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe'
$base = 'C:\Users\mrblue\Claude\morning breifing_code\scripts'
$arg = '"' + $base + '\auto_search.py" --개수 99999 --시간 '

# >>> 2026-09-03 수정. 19:00은 이르다 — 사용자가 언제 퇴근할지 모른다.
#     **자정(9/5 00:05)으로 옮긴다.** 그 전까지는 같이 진행한다.
#     ⚠️ 이 예약은 **금요일 퇴근 전에 진행 상황을 보고 다시 정한다.**
#        오늘 하루만 해도 시험 방향이 여러 번 바뀌었다. 격자가 그때는 안 맞을 수 있다
$일정 = @(
    @{ 이름 = 'AutoSearch-Fri'; 때 = '2026-09-05 00:05'; 초 = 30600 },
    @{ 이름 = 'AutoSearch-Sat1'; 때 = '2026-09-05 09:00'; 초 = 43200 },
    @{ 이름 = 'AutoSearch-Sat2'; 때 = '2026-09-05 22:00'; 초 = 36000 },
    @{ 이름 = 'AutoSearch-Sun1'; 때 = '2026-09-06 09:00'; 초 = 43200 },
    @{ 이름 = 'AutoSearch-Sun2'; 때 = '2026-09-06 22:00'; 초 = 28800 }
)

foreach ($j in $일정) {
    $a = New-ScheduledTaskAction -Execute $py -Argument ($arg + $j.초)
    $t = New-ScheduledTaskTrigger -Once -At $j.때
    Register-ScheduledTask -TaskName $j.이름 -Action $a -Trigger $t `
        -Description ('자동 조합 탐색 ' + [int]($j.초 / 3600) + '시간') -Force | Out-Null
    Write-Output ('{0,-18} {1}  ({2}시간)' -f $j.이름, $j.때, [int]($j.초 / 3600))
}

Write-Output ''
Write-Output '등록된 예약 작업:'
Get-ScheduledTask -TaskName 'DartOldBackfill', 'IndustryCollect', 'CapitalCollect',
    'AutoSearch-Fri', 'AutoSearch-Sat1', 'AutoSearch-Sat2',
    'AutoSearch-Sun1', 'AutoSearch-Sun2', 'MorningSectorBriefing',
    'EveningDataCollect' -ErrorAction SilentlyContinue |
    ForEach-Object {
        $i = $_ | Get-ScheduledTaskInfo
        '{0,-24} {1}' -f $_.TaskName, $i.NextRunTime
    }
