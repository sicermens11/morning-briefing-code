---
name: briefing-port-layout
description: 코드판 브리핑은 morning breifing_code 폴더 하나로 완결된다 — Templates는 Cowork 것이니 참조 금지
metadata: 
  node_type: memory
  type: project
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-08-25T07:46:43.558Z
---

주식 브리핑 스킬 3종(morning-sector-briefing · weekly-action-review · value-chain-map-updater)이
Cowork판과 Claude Code판 두 벌로 존재한다. 사용자는 결국 코드판을 택할 생각이고, 그때까지 병행 중이다.

**코드판은 `C:\Users\mrblue\Claude\morning breifing_code\` 하나로 완결된다** (2026-08-25 분리 완료):
- `data\` — 운영 데이터 전부(daily-log·캐시·가치사슬맵·백테스트 기록). 읽기·쓰기 모두 여기
- `scripts\` — check_jargon.py · compute_ta.py · check_subject.py · run-py.ps1 · set-*.ps1
- `run-briefing.ps1` · `run-skill.ps1` — 런처. 예약작업 3종이 이 경로를 가리킴
- `run-logs\` — 실행 로그
- 스킬 본체만 `~\.claude\skills\<이름>\SKILL.md`에 따로 있다

⚠️ **`C:\Users\mrblue\Claude\Templates\`는 Cowork 폴더다. 코드판은 절대 참조하지 않는다.**

**Why:** 이식 초기에 SKILL.md에 적힌 경로를 그대로 써서 두 시스템이 같은
`briefing-daily-log.md`·`fundamentals-cache.md`에 썼고, 서로를 자기 자신의 "2차 실행"으로
오인하는 사고가 실제로 났다(08-24·08-25 각각 두 항목이 한 파일에 섞임, Cowork가 코드판 호출까지
합산해 "총 92/71회 초과"로 오기록, 코드판이 Cowork가 쓴 08-18 캐시를 재사용해 A/B가 같은 조건이
아니게 됨). 그래서 전면 분리했다.

**How to apply:** 스킬이나 런처에 파일 경로를 새로 쓸 일이 생기면 반드시 `morning breifing_code`
하위를 쓴다. `Templates`가 나오면 잘못된 것이다. 전환 시점에도 **Cowork 로그를 병합하지 말 것** —
판정 기준이 다른 두 시스템의 픽을 한 트랙레코드로 섞으면 "갭 조합별 적중률" 학습 신호가 잡음이
된다. 코드판은 08-21 기준선에서 자기 이력만 이어간다. 남은 논의는 [[briefing-pending-work]] 참고.
