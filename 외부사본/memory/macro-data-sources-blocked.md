---
name: macro-data-sources-blocked
description: 거시·일정 자료 출처 중 이 PC/구독에서 막힌 것과 되는 것 — 다시 두드리지 않도록 (2026-09-15 밤 실측)
metadata: 
  node_type: memory
  type: reference
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-15T14:34:56.063Z
---

**막힌 것 (2026-09-15 밤 실측 · 다시 시도하지 않는다)**
- FRED `fredgraph.csv` — curl 이 파일조차 못 만든다(회사망에서 차단). WebFetch 로 숫자 190줄을 받는 건 요약기 오류 위험이라 안 한다
- BLS `bls.gov` — curl 1.3KB(차단). **WebFetch 는 된다**(CPI·고용 발표일 아카이브를 그렇게 받았다)
- 한국은행 bok.or.kr — 기준금리 추이 **목록 페이지**(`singl/baseRate/list.do`)는 curl 원문 파싱 OK(35건).
  통화정책방향 결정회의 일정 · 보도자료 게시판(P0000559) · 의결사항(P0000093·B0000245) · RSS — **전부 스크립트 렌더**라 curl·WebFetch 0건
- FMP `economics`(경제 캘린더·지표) — **구독 등급 밖** (ACCESS DENIED). 이 세션에서 재시도 금지
- ⚠️ WebFetch 요약은 표를 **틀리게 옮길 수 있다** — BOK 기준금리 2018 이후를 없는 값(2023-03-16 3.75%)으로 냈다. 표는 원문 파싱만 믿는다

**되는 것**
- Fed `federalreserve.gov/monetarypolicy/fomccalendars.htm` + `fomchistoricalYYYY.htm` — WebFetch OK (FOMC 2010~26)
- DART OpenAPI list.json (pblntf_ty=I) — 하루 1~3회 · 3,203일 7,265회 · 실패 0
- Alpha Vantage(MCP) — 미국 금리·CPI·고용 **값** 은 있으나 한국 수출입은 없다

**한국 수출입·국내 CPI·금통위 일정을 제대로 받는 길 = 한국은행 ECOS API 키** (무료 · 사용자가 직접 등록해야 한다).
ECOS 하나면 수출입(월·10일 잠정) · 소비자물가 · 기준금리 결정 시계열이 다 온다. [[hand-written-numbers-freeze]]
