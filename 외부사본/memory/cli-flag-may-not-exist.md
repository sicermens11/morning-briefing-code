---
name: cli-flag-may-not-exist
description: 스크립트에 넘기는 옵션(--최근 10 같은 것)이 실제로 구현돼 있는지 argparse/sys.argv 로 확인한다 — 없는 옵션은 조용히 무시되고 엉뚱한 동작이 매일 돈다
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-22T02:18:58.411Z
---

**어떤 스크립트에 옵션을 넘기기 전에, 그 스크립트가 그 옵션을 정말 읽는지 `grep "옵션이름"` 으로 확인한다. 없는 옵션은 오류가 안 나고 조용히 무시된다.**

**Why (2026-09-22 실측):**
`collect_evening.py` 는 2026-09-07 부터 `collect_krx_extra.py --최근 10` 을 매일 저녁 불렀다.
그런데 `collect_krx_extra.py` 에는 `--확인` 만 있고 **`--최근` 은 없었다.** 무시됐다.
결과: 수집기가 「폴더에 없는 날 전부」를 두드렸고, 주식선물코스닥은 서비스가 늦게 시작돼
옛날 1,385일이 영원히 빈날이라 **매일 9분 + 일반상품 7분을 헛돌았다.** 아무도 몰랐다.
이걸 08:02 브리핑 안(종가 직후)에 옮기려다 발견했다 — 그대로면 후보 뽑기가 16분 밀렸다.
`--최근 N` 을 진짜로 만들고 나니 7초.

**How to apply:**
- 호출부에 옵션을 적기 전에 피호출 스크립트에서 `sys.argv` / `add_argument` 로 그 이름을 찾는다. 없으면 만든다
- 「예상 N분」이 매번 크게 찍히는 수집 로그는 옵션이 안 먹는 신호일 수 있다 — 로그의 「받을 날」 수를 본다
- 브리핑 안에 새 단계를 넣을 땐 **혼자 한 번 돌려 시간을 잰다** (07:50~08:20 은 1분이 아깝다)
- [[checker-noise-hides-failures]] [[scheduled-task-checklist]] [[measure-screen-dont-guess]]
