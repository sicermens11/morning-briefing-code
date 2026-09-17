---
name: ledger-answers-coverage
description: 「수집한 것 중 안 잰 게 있나」「수집할 게 더 있나」는 내가 기억으로 답하지 않는다 — scripts/material_ledger.py 를 돌려 docs/재료대장.md 맨 위를 읽는다
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-15T14:25:34.076Z
---

**「다 쟀나」에 대한 답은 대장이 낸다. 내가 아니다.** `python scripts/material_ledger.py` → `docs/재료대장.md` 맨 위 구멍 셋.

**Why (2026-09-15 · 사용자):** 「수집할 게 더 없는지, 수집한 거 중에 테스트 안 한 건 없는지 **항상 물어보는데 왜 계속 나오지?**」
하루에 네 번 나왔다 — 16년짜리 재료 셋(아침) · krx-daily 「저가」 필드 · fred 미국 금리 · RSI/MACD.
매번 내가 「다 봤다」고 했고 매번 틀렸다. 게으름이 아니라 **구조**였다:
1. 재고(docs/자료재고.md)는 손으로 적어 얼어붙고, 「시험 코드가 그 폴더·필드를 읽나」를 대조하는 코드가 없었다
2. 판마다 사건 dict 를 따로 만든다 — 새 재료가 한 판에만 들어간다 (RSI 는 combo4 에만, gate7 에는 없다)
3. 수집 → 필드 → 재료 → ①단독 → ②앞뒤/종목분할 → ③돈 → ④4관문, 여섯 단계인데 **한 표에 없었다.**
   그래서 물어볼 때마다 **다른 단계의 구멍**이 나왔다 (수집 안 함 / 필드 안 읽음 / 재료로 안 만듦 / ③으로 안 넘김)
4. `rule_align` 은 실전 다섯 곳만 본다 — 시험 판의 「지금 규칙」이 낡아도(500억·후보 40) 아무도 모른다

**How to apply:**
- 「안 잰 게 있나」「더 모을 게 있나」를 들으면 **먼저 대장을 돌리고** 그 출력으로 답한다. 기억으로 답하지 않는다
- 새 자료를 모으거나 새 재료를 넣으면 **그 턴에 대장을 다시 돌려** 표에 들어왔는지 본다
- 새 재료는 **combo4 재료들 튜플 + newmat 붙이기** 두 곳 중 하나에 반드시 등록한다 — 대장은 거기서 읽는다
- 아침 확인 목록 첫 줄 = 대장 맨 위 구멍 셋
- [[hand-written-numbers-freeze]] [[claim-full-coverage-only-after-diff]] [[checker-blind-to-unlisted-files]]
