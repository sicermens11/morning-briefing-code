---
name: measure-screen-dont-guess
description: 화면을 고쳤으면 브라우저로 실측한 숫자로 보고한다. 코드를 읽고 짐작하면 틀린다
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-11T01:20:39.621Z
---

화면(카드·페이지)을 고친 뒤에는 **크롬 헤드리스로 실제 좌표를 재서** 보고한다.
코드를 읽고 「들어 있으니 보일 것」이라고 말하지 않는다.

**Why:** 2026-09-11 하루에 세 번 틀렸다.
1. 「40개가 다 그려져 있다(스크롤)」 — 카드는 `overflow:hidden` 이라 잘려 있었다
2. 파이썬 `A if 조건 else B` 가 `+` 보다 우선순위가 낮아 **딱지 뒤 줄이 통째로 사라졌는데** 코드만 봐서는 안 보였다
3. 「아래 끝 1270 · 넘침 0」이라 멀쩡한 줄 알았는데, `아래` 칸이 바닥에 붙어 **가운데(`overflow:hidden`)가 242px 을 잘라먹고 있었다**

세 번 다 **사용자가 화면을 보고 찾아냈다.**

**How to apply:**
- 잴 때는 **글자 마디(text node)를 `Range.getClientRects()` 로** 잰다.
  `el.children.length` 로 잎을 고르면 `<div><b>머리</b><br>본문</div>` 의 「본문」을 못 본다
- **카드 밖만 보면 안 된다.** 조상 중 `overflow:hidden` 인 칸을 찾아
  `scrollHeight - clientHeight` 로 **거기서 잘리는지**를 본다
- `scripts/check_layout.py` 가 이 둘을 다 본다 — 퀀트 카드는 `data-label` 이 있어야 검사에 걸린다
- 관련: [[claim-full-coverage-only-after-diff]] · [[verify-data-shape-first]]
