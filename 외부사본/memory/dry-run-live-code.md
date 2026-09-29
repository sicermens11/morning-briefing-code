---
name: dry-run-live-code
description: 실전 코드(record_pick 등)를 고치면 기록 파일을 임시 사본으로 바꿔 끼워 끝까지 돌린다 — 문법 검사로는 안 잡힌다
metadata:
  node_type: memory
  type: feedback
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-29T11:30:25.290Z
---

**실전에서 도는 코드를 고치면, 기록 파일을 임시 사본으로 바꿔 끼워 그 경로를 끝까지 돌려 본다.**
`ast.parse` 통과 · 단위 시험 통과로는 **안 잡히는 버그**가 있다.

**Why:** 2026-09-29 밤 전체 점검. 「섹터 자리 2」를 시뮬과 같게 고친 뒤 순수 함수는 8만 번 대조해
통과했다. 그런데 08:55 경로(`record_pick.동시호가기록`)를 **임시 사본으로 끝까지 돌리자**
`NameError: _섹터맵` 이 났다 — 08:05 함수의 지역 변수를 08:55 함수에서 쓰고 있었다.
**그날 아침 10:09 에 넣은 원래 코드도 같았다.** 문턱 넘은 게 6개를 넘는 첫날 08:55 기록이
통째로 멈췄을 것이다. 그날 산 게 0개라 드러나지 않았을 뿐이다.
처음 돌렸을 때는 예상가를 잘못 지어 **문턱 넘은 게 0개** — 고친 부분이 **아예 안 돌았는데**
「같다 ✅」가 찍혔다. 그 가지가 실제로 도는 입력을 만들어야 시험이 된다.

**How to apply:**
- `record_pick` 는 `RP.LOG = 임시경로` 로 바꿔 끼우고 `RP.동시호가기록("코드=값,…")` · `RP.main()`
  을 부른다. **진짜 기록 해시를 전후로 찍어** 안 바뀐 걸 확인한다 (파일을 쓰는 곳은 LOG 셋뿐)
- **고친 가지가 실제로 도는 입력**을 만든다 (예: 문턱 넘는 게 8개보다 많게 · 섹터 걸린 종목 넣기).
  「산 것 0」이면 시험이 안 된 것이다
- ⚠️ `bad_news_check.py` 는 **import 금지** — 맨 위부터 돌고 끝에 `raise SystemExit` 한다.
  값이 필요하면 파일을 글로 읽어 `ast` 로 꺼낸다 (`quant_cards._파는말()` 이 그렇게 한다)
- 관련: [[assert-only-after-checking]] · [[checker-can-catch-and-still-ship]] ·
  [[measure-screen-dont-guess]] · [[verify-data-shape-first]]
