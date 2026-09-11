# ==============================================================
#  주말 시험 (2026-09-11 20:35 에 다시 짬)
#
#  ⚠️⚠️ **한 번에 하나만 돌린다.** gate7_lab 은 램을 9GB 쓴다
#  ⚠️ LAB_OUT 은 **필수**다 (안 주면 193차 때처럼 남의 결과를 덮어쓴다)
#  ⚠️ 이미 있는 이름이면 gate7_lab 이 스스로 멈춘다 — 두 번 돌아도 안전하다
#
#  ⭐ 한 판 = 절 26개 전부 · **35분** (259차 실측: 19:53~20:28)
#  ⭐ 이번엔 **기준선을 바꿔가며** 여섯 판을 돌린다.
#     253차에서 잣대 하나 바꾸니 3.19억이 13.35억이 됐다 — 바탕이 결론을 바꾼다
#
#  ⭐ 처음 도는 절 다섯: 260 규모별중앙갭 · 261 후보수 · 262 갭문턱
#                      263 OR넷째갈래 · 264 4관문C·D
#     그리고 257차(증자)는 오늘 고쳤다 — 「0건」은 자료가 아니라 내 탓이었다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\weekend_labs_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

# 판 하나를 돌린다. 이름이 이미 있으면 gate7_lab 이 스스로 멈춘다
# 수집 시각(00:00~01:30)을 비켜 간다. **수집이 시험보다 먼저**다
#   00:05 AutoSearch · DartOldBackfill / 00:10 CapitalResume · OvernightDataCollect
#   램 9GB 를 같이 쓰면 한쪽이 죽는다. 죽는 게 수집이면 월요일 브리핑이 빈다
function 수집비키기 {
    while ($true) {
        $지금 = Get-Date
        $분 = $지금.Hour * 60 + $지금.Minute
        # 판 하나가 45분이다. 23:15 이후에 시작하면 00:00 을 넘는다
        if (($분 -ge 1395) -or ($분 -lt 90)) {
            적기 "   수집 시각이다 - 01:30 까지 기다린다 (지금 $($지금.ToString('HH:mm')))"
            Start-Sleep -Seconds 300
        } else {
            break
        }
    }
}

function 판($이름, $설명, $환경) {
    수집비키기
    적기 "[$이름] $설명 - 시작"
    foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
    $env:LAB_OUT = "2026-09-12_$이름.txt"
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append
    foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    적기 "[$이름] 끝"
}

# -- 0 . 앞 시험이 돌고 있으면 기다린다 (램 9GB) --------------------
적기 "[0] 앞 시험 확인"
$분 = 0
while ((Get-Process python -ErrorAction SilentlyContinue) -and ($분 -lt 180)) {
    Start-Sleep -Seconds 60
    $분 = $분 + 1
}
적기 "[0] $분 분 기다림 - 시작한다"

# ==============================================================
#  판 여섯 — 기준선만 다르고 **절 26개는 같다**
# ==============================================================

# 1) 지금 기준선 (견줌의 바탕) — 새 절 다섯이 처음 도는 판
판 "A_지금기준선" "갭잣대 후보+실전표본30 · 상대갭 -3.5 · 후보 40" @{}

# 2) ⭐⭐⭐ ㉯ 기준선 — **실전을 바꿀 유일한 후보**
#    259차 A절: 36.5억 · 낙폭 -5.4% · 돈÷낙 16.21 (지금 13.35억 · -5.7% · 12.49)
#    이 바탕에서 **다른 절들이 어떻게 보이는지**가 핵심이다
판 "B_실전표본만" "갭잣대 = 실전표본30 혼자" @{ BASE_GAP = "표본만+실전표본" }

# 3) ⭐⭐⭐ 규모별 중앙갭 기준선 (260차)
판 "C_규모별중앙갭" "갭잣대 = 규모별" @{ BASE_GAP = "규모별" }

# 4) ⭐⭐⭐ 갭 문턱을 푼 판 (262차 · 181차 「갭이 후보의 98%를 버린다」)
판 "D_갭문턱_2.0" "상대갭 -3.5 -> -2.0" @{ BASE_RELGAP = "-2.0" }

# 5) ⭐⭐⭐ 안 자르는 판 (261차 · 172차 기회 60% 차이)
판 "E_안자름" "후보 40 -> 안 자름" @{ BASE_PICKS = "999" }

# 6) ⭐⭐ 크기 무제한 — 260차 A절은 여기서만 뜻이 산다
#    ⚠️ 251차 규모별 문턱은 **오늘 기각**됐다(낙폭 -50.5%). 이 판은 260차용이다
판 "F_크기무제한" "대형주까지 사건에 넣는다" @{ SIZE_HI = "999999" }

# ==============================================================
#  판 G — **매도 기준선**을 A판 결과가 정한다
#
#  ⭐ 사용자: 「결과에 따라 테스트가 필요하면 허락받지 말고 그냥 테스트해」
#     그래서 사람이 결과를 볼 때까지 기다리지 않는다. A판 표를 코드가 읽고 잇는다
#
#  판정은 TEST-ORDER.md 3절 그대로다 — **끝 자산**이 더 많고 **돈÷낙폭**이
#  안 나빠진 것. 둘 다 이긴 게 없으면 끝 자산이 제일 큰 것을 **살펴보기**로
#  돌린다 (낙폭이 나빠진 걸 앞뒤 분할이 걸러내는지 본다)
# ==============================================================
적기 "[G] 매도 기준선 고르는 중"
$A판 = "data\_labs\2026-09-12_A_지금기준선.txt"
if (Test-Path $A판) {
    $매도 = & $py "scripts\pick_sell.py" $A판 2>&1 | Tee-Object $log -Append |
            Where-Object { $_ -notmatch '^#' } | Select-Object -Last 1
    $매도 = "$매도".Trim()
    if ($매도) {
        판 "G_매도기준선" "매도 기준선 = $매도" @{ BASE_SELL = $매도 }
    } else {
        적기 "[G] 바꿀 매도 설정이 없다 - 건너뛴다"
    }
} else {
    적기 "[G] A판 결과가 없다 - 건너뛴다"
}

# ==============================================================
#  뒷정리 (시험이 아니다)
# ==============================================================
적기 "[H] 빈도 재생성"
& $py "scripts\how_often.py" 2>&1 | Select-Object -Last 4 | Tee-Object $log -Append

적기 "[I] 규칙 대조"
& $py "scripts\rule_align.py" 2>&1 | Select-Object -Last 6 | Tee-Object $log -Append

적기 "[J] 시험 대조 (계획에 있는데 절이 없는 것)"
& $py "scripts\check_tests.py" 2>&1 | Select-Object -Last 12 | Tee-Object $log -Append

적기 "모두 끝"
