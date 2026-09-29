---
name: layout-never-blocks-publishing
description: 조판이 어긋났다고 게시를 막지 않는다 — 안 올리면 그날 전부가 전달이 안 된다
metadata:
  node_type: memory
  type: feedback
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-29T07:44:21.689Z
---

**조판 문제(잘림·넘침·간격·밖으로)로는 게시를 막지 않는다.** 🔴 로 크게 찍고 **올린다.**

사용자(2026-09-29): 「넘치면 안되지만, **넘쳤다고 게시 금지 되는건 전혀 정보 전달을
못 하게 되는거잖아?**」

| | 잃는 것 |
|---|---|
| 넘침·잘림 | 그 카드의 **일부** |
| 게시 금지 | **그날 전부** |

**Why:** 2026-09-29 아침에 「검사기가 잡고도 올렸다」([[checker-can-catch-and-still-ship]])를
고치면서 **막는 쪽으로 너무 갔다.** 그날 저녁 게시가 막혔는데 막은 카드가
**어제 것**이었고, 오늘 카드는 멀쩡했다. 22px 짜리 9/1 카드 하나가 브리핑 전체를 멈췄다.
「잡고도 올린다」의 답은 **막는 것**이 아니라 **크게 찍는 것**이었다.

**막는 자리는 「코드가 뒤로 간 것」에만 남긴다:**
· 문법 오류 — 단추가 안 눌려 **넘길 수가 없다** (화면은 멀쩡해 보여 더 위험하다)
· 좌우 잠금·flex-wrap·word-wrap 빠짐 · 좁은 화면 넘침 — 내용이 아니라 코드 문제다

**How to apply:**
· 관문을 넣기 전에 **「막으면 무엇을 잃나」와 「안 막으면 무엇을 잃나」를 견준다**
· 「알린다」가 약해 보이면 **경고를 더 크게** 만든다 — 막는 것으로 바꾸지 않는다
· 관련: [[new-gate-can-deadlock-on-old-data]] · [[checker-can-catch-and-still-ship]] ·
  [[layout-never-cuts-content]] · [[checker-noise-hides-failures]]
