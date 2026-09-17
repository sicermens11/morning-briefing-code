---
name: checker-noise-hides-failures
description: 점검기가 「실패 0」까지 빨갛게 찍으면 아무도 안 읽는다 — 소음이 곧 조용한 실패다. 필드 이름은 짐작 말고 원본을 한 건 받아 본다
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-16T02:35:00.923Z
---

2026-09-16 「버그·조용히 넘어가는 것 찾자」 사냥에서 배운 둘.

**① 점검기의 소음은 조용한 실패를 숨긴다.** audit_all F절이 「실패 0」「Error 0」 줄까지 세어 40개 로그가 다 빨개져 있었고,
그 옆에서 밤 판 여섯이 Traceback 으로 죽고 08:56 판정 재게시가 실패해도 아무도 몰랐다.
점검은 「최근 며칠 · 진짜 나쁜 줄」만 세고, 복구된 것은 ✅ 로 걷어 **찾은 문제 수가 읽을 만한 수**로 남아야 한다.
42개 → 12개로 줄였더니 남은 것이 전부 아는 것이었다.

**② 필드 이름은 원본을 한 건 받아 확인한다.** DART elestock 에 `sp_stock_lmp_irds_rson` 은 없었다(3,245건 전부 None),
majorstock 「보유목적」 자리엔 `ctr_stkqy`(숫자)가 들어가 있었다. 둘 다 몇 달을 조용히 지나갔다.
`.get()` 은 없는 키를 오류 없이 None 으로 준다 — 수집기는 첫 실행 때 원본 키 목록을 찍어 대조해야 한다.

**Why:** 사용자가 「테스트 다 했으니 이제 조용히 넘어가는 것을 없애자」고 했을 때, 있는 점검기가 못 보던 종류가 여섯이었다.
**How to apply:** 새 로그·새 예약·새 수집기를 만들면 audit_all 에 그것을 보는 절을 같이 붙인다([[checker-blind-to-unlisted-files]]).
아침엔 [[ledger-answers-coverage]] 와 함께 `python scripts\audit_all.py` 를 돌려 「찾은 문제」 수부터 본다. 관련: [[suspect-data-first]] · [[verify-data-shape-first]]
