---
name: dont-declare-impossible
description: 「그 자료는 못 구한다」고 여섯 번 말했고 여섯 번 다 틀렸다 — 최소 대여섯 곳을 두드린다
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-03T12:17:24.655Z
---

자료를 못 구한다고 단정한 게 **여섯 번, 전부 틀렸다.** 사용자가 *"또 못 구한다고
했는데, 구할 수 있는거 찾아봐"*라고 하지 않았으면 그냥 넘어갔을 것들이다.

```
「유가·금은 KRX만 2.6년」   → Yahoo에 26년 (6,500일)
「미국 금리는 KRX만」       → Yahoo에 31년 · Alpha Vantage에 기준금리 72년
「미국 지수는 3년이 한계」    → 27년
「QQQ·SOXX는 방법이 없다」  → range=max 대신 period1/period2를 주면 된다
「한국 국고채는 2.6년뿐」    → **이미 갖고 있었다** (data/etf-krx 4,103일, 국채 ETF 86개)
「FRED만 있다(하이일드)」   → HYG ÷ LQD 비율로 대신할 수 있다
```

**Why:** API 두세 곳만 두드려보고 결론지었다. 그리고 **한 서비스의 한계를 전체로
일반화**했다 — KRX는 선물·국고채가 2.6년인데 **ETF만은 2010년부터** 준다.

**How to apply:** 「없다」고 말하기 전에 **최소 대여섯 곳**을 확인한다 (Yahoo ·
Alpha Vantage · FRED · 미 재무부 · 세계은행 · 네이버 · KRX 서비스별). 한 번 실패는
결론이 아니다 — FRED는 첫 시도 TimeoutError였다가 두 번째에 열렸다. **이미 받아둔
자료부터 뒤진다.** 그리고 대용품을 생각한다(ETF 가격으로 금리 방향 역산).
확인용 probe에서 성공한 자료는 **그 자리에서 저장**한다 — probe 자체가 할당량을
쓰고, FRED는 6번 성공 뒤 IP를 막았다.
