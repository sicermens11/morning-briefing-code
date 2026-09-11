# 주식 브리핑 스킬 3종 — Claude Code 이식판

Cowork에서 돌던 스킬 3개를 이 PC의 Claude Code로 옮긴 것. 2026-08-21 작업.

**판정 규칙·점수표·서술 원칙은 전부 원본 그대로다.** 바뀐 것은 실행 환경뿐(리눅스 샌드박스 → Windows).

| 스킬 | 주기 | 하는 일 | 작업 이름 |
|---|---|---|---|
| `morning-sector-briefing` | 평일 08:00 | 섹터 브리핑 → Gmail 초안 + 카카오 | `MorningSectorBriefing` |
| `weekly-action-review` | 화 10:30 | 전주 픽 적중률 리뷰 → Gmail | `WeeklyActionReview` |
| `value-chain-map-updater` | 4·9월 첫 월요일 09:00 | 가치사슬맵 갱신 → 카카오 알림 | `ValueChainMapUpdater` |

세 스킬은 서로 물려 있다. 브리핑이 매일 `value-chain-map.md`를 읽어 종목 후보 풀로 쓰고,
브리핑이 남긴 `briefing-daily-log.md`를 주간 리뷰가 읽어 적중률을 매기며,
가치사슬맵 갱신이 그 후보 풀 자체를 반기마다 손본다.
→ **한 스킬의 출력 형식을 바꾸면 다른 스킬이 조용히 깨진다.** 특히 브리핑 STEP 8의
   일일 로그 필드를 바꿀 때는 `weekly-action-review` STEP 2를 반드시 함께 고칠 것.

---

## 어디에 뭐가 있나

**2026-08-25에 Cowork와 완전히 분리했다.** 이 폴더 하나가 코드판의 전부이고,
`~\Claude\Templates\`(Cowork 폴더)는 더 이상 참조하지 않는다.

```
morning breifing_code\
├── run-briefing.ps1        브리핑 전용 런처(테스트 모드·제목 suffix 때문에 따로 둠)
├── run-skill.ps1           나머지 두 스킬 공용 런처
├── data\                   ★ 운영 데이터 (읽기·쓰기 전부 여기)
│   ├── briefing-daily-log.md          매일 STEP8이 append
│   ├── fundamentals-cache.md          F2·VAL·RISK 캐시(10거래일 재사용)
│   ├── backtest-track-record.md       백테스트 적중률
│   ├── weekly-review-history.md       주간 리뷰 결과
│   ├── value-chain-map.md             13섹터 가치사슬맵
│   ├── krx-holidays-2026.md           국내 휴장일
│   ├── briefing-template.html         HTML 템플릿
│   ├── seasonal-investment-calendar.md  참고자료(스킬은 읽지 않음)
│   └── SKILL-backups\                 value-chain-map 갱신 전 스냅샷
├── scripts\                검산·계산 스크립트
│   ├── check_jargon.py     용어·출처링크·내부코드명 검산
│   ├── compute_ta.py       기술지표 계산
│   ├── check_subject.py    Gmail 제목 형식 하드체크
│   ├── run-py.ps1          파이썬 실행 래퍼(인터프리터 자동 탐색)
│   └── set-*.ps1           예약작업 설정 변경(관리자 권한 필요)
├── run-logs\               실행 1건당 1파일, 자동 삭제(브리핑 60일·나머지 180일)
├── README.md / AGENDA.md   문서
└── SKILL.md / DECISIONS.md Cowork 원본 참고 사본(운영에 쓰이지 않음)
```

스킬 본체는 `~\.claude\skills\<스킬이름>\SKILL.md`에 있다. **규칙은 그 파일을 고친다.**

### ⚠️ 왜 분리했나 (2026-08-25)

이식할 때 SKILL.md에 적힌 경로(`C:\Users\mrblue\Claude\Templates`)를 그대로 썼는데,
**그 경로가 Cowork가 지금도 쓰고 있는 폴더였다.** 결과적으로 두 시스템이 같은
`briefing-daily-log.md`·`fundamentals-cache.md`에 쓰면서 서로를 자기 자신의 재실행으로
오인했다 — Cowork 로그에 이렇게 남아 있다:

> ## 2026-08-24 (월) ⚠️ **2차 실행** (컨텍스트 압축 재개)
> **1차 자동실행(성광벤드/두산에너빌리티 픽)이 이미 완료·로그 기록 후 2차로 재실행된 것으로 추정.**
> MCP횟수: … 1차 실행 45회 포함 **총 92/71회 초과 — 2개 실행분 합산**

실제로는 "1차"가 코드판 실행이었다. 코드판도 반대로 Cowork 항목을 "08-24 2차 실행분"으로
기록했다. 착각이 양방향이었다.

실질 피해 셋:
1. **`weekly-action-review` 채점 오염** — 한 파일에 두 시스템 픽이 섞여 어느 쪽 성과인지 구분 불가
2. **캐시 교차 오염** — 코드판이 `캐시 08-18 재사용`(Cowork가 쓴 값)으로 계산 → A/B가 같은 조건이 아니게 됨
3. **예산 집계 오염** — 위의 "92/71회 초과" 오기록

→ 데이터·스크립트·런처·로그를 전부 이 폴더로 옮기고, Templates는 손대지 않았다.
   나중에 Cowork를 정리할 때 **Templates를 통째로 지워도 아무 영향이 없다.**

### ⚠️ 전환할 때 Cowork 이력을 병합하지 말 것

코드판 로그는 08-21 기준선에서 자기 이력만 이어간다(08-24·08-25 코드판 항목은 이전 완료).
Cowork가 그 사이 쌓은 픽은 **일부러 가져오지 않는다** — 판정 기준이 다른 두 시스템의 픽을
한 트랙레코드로 섞으면 "갭 조합별 적중률" 같은 학습 신호가 잡음이 된다.
Cowork 쪽 성과를 비교하고 싶으면 Gmail 초안이 양쪽 다 남아 있으니 그걸로 본다.

---

## 현재 운영 상태 (2026-08-21~)

**`MorningSectorBriefing`·`EntryCheck0905`·`EntryCheck1220` 셋이 켜져 있다.**
Cowork 병행은 **2026-08-25에 끝났다**(Cowork를 수동 실행으로 전환).
**⚠️ 2026-08-27 정정 — 5개 전부 켜져 있다.** README가 "2개는 꺼져 있다"고 잘못 적고 있었다:

| 작업 | 다음 실행 |
|---|---|
| `MorningSectorBriefing` | 평일 08:00 |
| `EntryCheck0905` | 평일 09:05 |
| `EntryCheck1220` | 평일 12:20 (2026-08-26 신설) |
| **`WeeklyActionReview`** | **2026-09-01(화) 10:30** ← 다음 주에 실제로 돈다 |
| **`ValueChainMapUpdater`** | **2026-09-07(월) 09:00** (반기 갱신) |

### ⚠️ `[코드]` 마커 — 폐지됨 (2026-08-25), 붙이면 실패한다

병행 시절 Gmail 제목·카카오 첫 줄에 `[코드]`를 붙여 두 판을 구분했다. **지금은 금지다.**

📌 **사흘 연속 되살아났던 사고**(08-25·08-26·08-27). 원인은 마커를 요구하는 자리가
**네 곳**이었는데 08-26에 **세 곳만** 막았기 때문이다:

| 자리 | 08-26 처리 | |
|---|---|---|
| `SKILL.md` "되살리려면 이렇게" 안내 | ✅ 제거 | |
| `check_subject.py` `SUBJECT_RE` | ✅ `SUBJECT_BANNED_MARKER`로 차단 | |
| `check_jargon.py` 내부코드 패턴 | ✅ `internal_leaks`에 추가 | |
| **`run-briefing.ps1`의 프롬프트** | ❌ **놓침** | ← **실제로 지시하던 곳** |

08-27 실행에서 검산 스크립트가 마커를 **잡아냈는데도**, 프롬프트가 "필수"라고 말하고 있어
모델은 **"사용자 지시가 우선"이라며 마커를 유지하고 차단 규칙을 되돌리라고 권고**했다.
모델이 틀린 게 아니다 — 지시가 그렇게 돼 있었다.
**2026-08-27에 `run-briefing.ps1` 56번째 줄을 고쳐 네 곳을 모두 정리했다.**

⚠️ **교훈**: 규칙을 없앨 때는 그 규칙이 **"선언된 곳"** 만이 아니라
**"모델에게 전달되는 경로"**(런처 프롬프트 포함)를 전부 훑어야 한다.
검사만 강화하면, 검사를 이기는 지시가 남아 있는 한 매일 실패로만 남는다.

## 켜고 끄는 법

```powershell
Enable-ScheduledTask  -TaskName MorningSectorBriefing, WeeklyActionReview, ValueChainMapUpdater
Disable-ScheduledTask -TaskName MorningSectorBriefing     # 개별로 끄기
Start-ScheduledTask   -TaskName MorningSectorBriefing     # 지금 한 번 돌려보기
Get-ScheduledTask MorningSectorBriefing, WeeklyActionReview, ValueChainMapUpdater |
    Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime, LastTaskResult
```

수동 실행(스케줄러 없이):
```powershell
$T = "C:\Users\mrblue\Claude\morning breifing_code"
powershell -ExecutionPolicy Bypass -File "$T\run-briefing.ps1" -Mode test    # 브리핑 테스트
powershell -ExecutionPolicy Bypass -File "$T\run-skill.ps1" -Skill weekly-action-review
powershell -ExecutionPolicy Bypass -File "$T\run-skill.ps1" -Skill value-chain-map-updater
```
브리핑의 `-Mode test`는 제목에 `[수동실행 HH:MM]` suffix를 붙이고 일일 로그를 남기지 않는다.

**두 런처 모두 `-DryRun`을 지원한다.** claude를 부르지 않고 전달될 프롬프트만 찍는다 —
스크립트를 고친 뒤 한글이 안 깨졌는지 확인하는 용도다(아래 5번 참고).

---

## 돌아가는 배경 — 서버는 없다, 이 PC가 서버다

```
08:00  Windows 작업 스케줄러 (이 PC)
         └─ claude.exe 실행
              ├─→ Anthropic API          (판단·글쓰기)
              ├─→ playmcp.kakao.com      (네이버·한국주식·DART·카카오)
              ├─→ mcp.exa.ai             (해외 뉴스)
              ├─→ financialmodelingprep  (미국 시세·실적)
              └─→ gmailmcp.googleapis    (초안 저장)
```

데이터 소스는 전부 원격 서비스라 직접 띄우거나 관리할 서버가 없다. 이 PC가 하는 일은 두 가지 —
**정해진 시각에 프로그램을 켜주는 것**, 그리고 **일일 로그·캐시·가치사슬맵 파일을 들고 있는 것**.

**PC가 켜져 있어야 한다.** Cowork도 마찬가지였으므로 이 점은 이식으로 달라진 게 아니다.
이 PC는 데스크톱이고 절전 설정이 "사용 안 함"(`STANDBYIDLE` AC 인덱스 `0x00000000`)이라
잠들지 않는다 — 조건은 좋은 편이다.

세 작업 모두 **S4U("로그온 여부와 관계없이 실행")** 로 등록돼 있다. 비밀번호를 저장하지 않으면서
로그인 화면에서도 실행되는 방식이라, Windows 업데이트가 새벽에 재부팅해도 그날 브리핑이
건너뛰어지지 않는다. 2026-08-21에 실제 실행까지 검증했다(등록만 되고 실행에서 막히는
"배치 로그온 권한 누락" 사례가 있어 버리는 작업으로 확인).

⚠️ S4U 설정을 다시 건드리려면 **관리자 권한**이 필요하다(`Set-ScheduledTask -Principal`은
일반 권한으로는 "Access is denied"). 이럴 때 쓰는 스크립트가
`scripts\set-s4u.ps1`이고, 권한 상승으로 실행하면 된다:
```powershell
Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy','Bypass','-File','C:\Users\mrblue\Claude\morning breifing_code\scripts\set-s4u.ps1'
```
결과는 `run-logs\s4u-result.log`에 남는다(권한 상승된 창은 바로 닫혀서 화면으로는 못 본다).

그래도 PC가 꺼져 있으면 그날은 건너뛴다. `StartWhenAvailable`이 켜져 있어 PC를 켜면 늦게라도
한 번 따라 실행되지만, 개장 전 브리핑이 10시에 오면 가치는 반감된다.

---

## 환경 때문에 바뀐 것 (규칙 변경 아님)

1. **STEP 0 신설 — 도구 스키마 선조회**
   이 환경의 MCP 도구는 전부 deferred 상태라 이름만 알고 파라미터는 모르는 채로 시작한다.
   `ToolSearch`로 스키마를 먼저 불러오지 않으면 커넥터가 멀쩡히 붙어 있어도 "도구 없음"으로 실패한다
   (실측 확인: `ToolSearch` 없이 돌리면 `TOOL_MISSING`, 넣으면 정상 조회).
   → 수집용 29개는 STEP 0에서, 발송용 4개(Gmail·카카오)는 **STEP 6 직전에** 따로 불러온다.
   발송용을 일부러 뒤로 뺀 이유는, 미리 불러두면 실제 사용 시점까지 거리가 멀어져
   기억 기반 호출로 되돌아가는 것이 `create_draft` 파싱오류(DECISIONS.md 134차)의 패턴이었기 때문.

2. **도구 이름 매핑표 (STEP 0-3)**
   본문 STEP 1~8은 원본의 짧은 이름(`koreaStock-stock_get_quote` 등)을 그대로 두고,
   호출 시점에 매핑표로 치환한다. 본문을 전부 긴 이름으로 바꾸면 규칙 문장이 읽기 어려워지고
   이식 중 규칙을 흘릴 위험이 커져서 이 방식을 택했다.
   부수 효과: 도구 이름에 박혀 있던 **커넥터 UUID가 사라졌다**(`mcp__e14afac1-...` → `mcp__claude_ai_Gmail__`).
   재연결해도 이름이 안 바뀌므로, 원본 실행 규칙 6번의 "connector ID는 재연결 시 바뀔 수 있음" 걱정이 없어졌다.

3. **bash → PowerShell** (이 PC엔 bash·grep·`/tmp`가 없다)
   - Gmail 업그레이드 하드카운터: `/tmp` + `touch` → `%TEMP%\morning-briefing` + `New-Item`
   - 제목 형식 하드체크: `grep -P` → `check_subject.py` (**판정 정규식은 원본과 글자 단위로 동일**)
   - 검산 스크립트: heredoc stdin → 파일 경유

4. **긴 문자열은 파일로 넘긴다**
   완성 HTML·카카오 본문·Gmail 제목은 한글과 이모지가 섞여 있어 PowerShell 명령행으로 넘기면
   콘솔 코드페이지 때문에 조용히 깨진다. "제목이 규칙을 어겼다"가 아니라 "검증기가 제목을
   잘못 읽었다"로 실패하는 게 최악이라, UTF-8 파일로 쓰고 경로만 넘기도록 바꿨다.
   두 파이썬 스크립트에 `--html-file` / `--text-file` / `--file` 입력을 추가했고
   (기존 stdin 방식은 유지 — Cowork 쪽 호출에 영향 없음), BOM도 벗겨내도록 했다.

5. **⚠️ `.ps1` 파일은 반드시 UTF-8 BOM 포함으로 저장할 것**
   Windows PowerShell 5.1은 BOM 없는 UTF-8 스크립트를 ANSI로 읽는다. 그러면 스크립트 안의
   한글이 **실행 시점에 이미** 깨지고, 깨진 프롬프트가 그대로 claude에게 전달된다.
   첫 테스트 실행에서 실제로 이걸 겪었다 — 로그가 `morning-sector-briefing ?쒖옉`으로 찍혀서
   드러났지, 안 그랬으면 "왜 결과가 이상하지"로 한참 헤맸을 문제다.
   에디터로 고칠 때 인코딩이 풀리기 쉬우니, 고친 뒤엔 `-DryRun`으로 한글을 눈으로 확인할 것:
   ```powershell
   powershell -ExecutionPolicy Bypass -File "...\run-briefing.ps1" -Mode test -DryRun
   ```
   BOM 다시 붙이기:
   ```powershell
   $f = "...\run-briefing.ps1"
   $t = [IO.File]::ReadAllText($f, [Text.Encoding]::UTF8)
   [IO.File]::WriteAllText($f, $t, (New-Object Text.UTF8Encoding($true)))
   ```

6. **파이썬이 이 PC에 없어서 설치했다** (3.13, 사용자 영역)
   PATH에 `python.exe`가 있긴 한데 Microsoft Store 스텁이라 실행하면 종료코드 9009만 남긴다.
   겉보기엔 "파이썬이 있다"로 보여서 진단이 오래 걸리는 함정이라, `run-py.ps1`이 이 스텁을
   명시적으로 걸러내고 실제 인터프리터를 찾는다.

7. **`--allowedTools`에 `ToolSearch`가 반드시 들어가야 한다**
   두 런처 모두에 들어 있다. 빼면 커넥터가 멀쩡히 연결돼 있어도 전부 "도구 없음"으로 실패한다.
   와일드카드(`mcp__claude_ai_PlayMCP__*`)는 정상 동작하는 것을 실측 확인했다.

---

## 규칙이 바뀐 것 (딱 하나)

**MCP 호출 상한: "70회 절대 초과 금지" → "목표 70회 / 하드 상한 95회"**

원본의 70회는 Cowork 태스크의 단계 수 제약에서 나온 수치다. 초과하면 STEP 6(Gmail 발송)에
닿기 전에 실행이 잘릴 위험이 있었다. Claude Code 로컬 실행에는 그 제약이 없고 비용도
호출수가 아니라 토큰 기준이라, 같은 숫자를 하드 상한으로 유지하면 **멀쩡한 신호를 이유 없이
버리는 쪽으로만 작동한다** — 생략 순서 1~5순위(MCP-6 재시도, 국내금리·예탁금·경제지표,
2군, 조건부-ANCHOR, MCP-GLOBAL)가 사실상 매일 발동하는 구조였다.

실제 소요량은 STEP 8 로그에 계속 기록되니, 몇 주치 쌓이면 상한을 다시 조정할 것.

---

## 이식하다 확인한 것

**`seasonal-investment-calendar.md`는 원래 스킬이 읽지 않는 파일이다.**
이식 중에 이 파일이 Templates에 없는 걸 보고 "끊어진 참조"로 오판했다가, DECISIONS.md
60차(2026-07-20)·88차에서 정정했다 — 이 파일은 "어떤 SKILL.md도 읽지 않는 순수 브라우징용
참고자료"로 의도적으로 만든 것이고, MCP-SEASON의 "근거:" 표기는 **배경 문서 포인터**이지
Read 지시가 아니다. MCP-SEASON은 시기별 트리거가 맞을 때 뉴스검색 1회를 하는 항목이다.
→ 스킬에 "이 항목 때문에 Read를 호출하지 말 것"이라고 명시해 뒀다. 파일 자체는
   `data\`에 복사해 뒀지만(사람이 보는 용도), 스킬 동작에는 관여하지 않는다.

---

## 규칙을 고치고 싶을 때

`~\.claude\skills\morning-sector-briefing\SKILL.md`를 고치고, 배경을 이 폴더의 `DECISIONS.md`에 남긴다
(원본이 138차까지 그렇게 관리돼 왔다).

⚠️ Cowork 쪽 SKILL.md와 이 파일은 **별개이고, 이미 크게 갈라졌다.**
**병행은 2026-08-25에 끝났으므로 Cowork 쪽은 더 이상 고치지 않는다.**
(2026-08-26~27에 코드판에만 들어간 것: 1군/2군 폐지, 후보 상한 6, 4분류 점수,
가치사슬맵을 색인으로 되돌림, 재무 최신분기 병기, 시장국면 한 줄 — Cowork판엔 전부 없다.)
⚠️ `C:\Users\mrblue\Claude\Templates\`(Cowork 폴더)는 **건드리지 않는다.**



